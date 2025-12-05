"""Tests for the stats module."""

import pytest
import json
from pathlib import Path
import tempfile

from localization_analyzer.features.stats import (
    StatsCalculator,
    ProjectStats,
    LanguageStats,
    TableStats
)


class TestProjectStats:
    """Test cases for ProjectStats."""

    def test_default_values(self):
        """Test default values."""
        stats = ProjectStats()
        assert stats.total_languages == 0
        assert stats.total_keys == 0
        assert stats.overall_completion == 0.0
        assert stats.languages == []

    def test_to_dict(self):
        """Test dictionary conversion."""
        stats = ProjectStats(
            project_name="Test",
            total_languages=2,
            total_keys=10,
            overall_completion=85.5
        )

        d = stats.to_dict()

        assert d['project_name'] == "Test"
        assert d['summary']['total_languages'] == 2
        assert d['summary']['total_keys'] == 10
        assert d['summary']['overall_completion'] == 85.5

    def test_to_json(self):
        """Test JSON conversion."""
        stats = ProjectStats(
            project_name="Test",
            total_keys=5
        )

        json_str = stats.to_json()
        parsed = json.loads(json_str)

        assert parsed['project_name'] == "Test"
        assert parsed['summary']['total_keys'] == 5


class TestLanguageStats:
    """Test cases for LanguageStats."""

    def test_default_values(self):
        """Test default values."""
        lang = LanguageStats(code='en', name='English')

        assert lang.code == 'en'
        assert lang.name == 'English'
        assert lang.total_keys == 0
        assert lang.completion_percent == 0.0

    def test_with_values(self):
        """Test with custom values."""
        lang = LanguageStats(
            code='tr',
            name='Turkish',
            total_keys=100,
            translated_keys=80,
            missing_keys=20,
            completion_percent=80.0
        )

        assert lang.code == 'tr'
        assert lang.translated_keys == 80
        assert lang.missing_keys == 20


class TestStatsCalculator:
    """Test cases for StatsCalculator."""

    def test_init(self):
        """Test initialization."""
        calc = StatsCalculator()
        assert calc.source_lang == 'en'

        calc2 = StatsCalculator(source_lang='tr')
        assert calc2.source_lang == 'tr'

    def test_calculate_empty(self):
        """Test calculation with empty data."""
        calc = StatsCalculator()
        stats = calc.calculate({})

        assert stats.total_languages == 0
        assert stats.total_keys == 0

    def test_calculate_single_language(self):
        """Test calculation with single language."""
        calc = StatsCalculator(source_lang='en')

        keys_by_language = {
            'en': {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        }

        stats = calc.calculate(keys_by_language)

        assert stats.total_languages == 1
        assert stats.total_keys == 3
        assert stats.overall_completion == 100.0  # No other languages

    def test_calculate_multiple_languages_complete(self):
        """Test calculation with multiple complete languages."""
        calc = StatsCalculator(source_lang='en')

        keys_by_language = {
            'en': {'key1': 'Hello', 'key2': 'World'},
            'tr': {'key1': 'Merhaba', 'key2': 'Dünya'}
        }

        stats = calc.calculate(keys_by_language)

        assert stats.total_languages == 2
        assert stats.total_keys == 2
        assert stats.overall_completion == 100.0

        # Turkish should be 100% complete
        tr_lang = next(l for l in stats.languages if l.code == 'tr')
        assert tr_lang.completion_percent == 100.0
        assert tr_lang.missing_keys == 0

    def test_calculate_multiple_languages_incomplete(self):
        """Test calculation with incomplete translations."""
        calc = StatsCalculator(source_lang='en')

        keys_by_language = {
            'en': {'key1': 'Hello', 'key2': 'World', 'key3': 'Test'},
            'tr': {'key1': 'Merhaba'}  # Only 1 of 3 keys
        }

        stats = calc.calculate(keys_by_language)

        # Turkish should be ~33% complete
        tr_lang = next(l for l in stats.languages if l.code == 'tr')
        assert tr_lang.completion_percent == pytest.approx(33.33, rel=0.1)
        assert tr_lang.missing_keys == 2

        # Should have missing translations
        assert 'tr' in stats.missing_translations
        assert 'key2' in stats.missing_translations['tr']
        assert 'key3' in stats.missing_translations['tr']

    def test_calculate_overall_completion(self):
        """Test overall completion calculation."""
        calc = StatsCalculator(source_lang='en')

        keys_by_language = {
            'en': {'k1': 'v1', 'k2': 'v2', 'k3': 'v3', 'k4': 'v4'},
            'tr': {'k1': 'v1', 'k2': 'v2'},  # 50%
            'de': {'k1': 'v1', 'k2': 'v2', 'k3': 'v3', 'k4': 'v4'}  # 100%
        }

        stats = calc.calculate(keys_by_language)

        # Overall should be (50 + 100) / 2 = 75%
        assert stats.overall_completion == pytest.approx(75.0, rel=0.1)

    def test_language_names(self):
        """Test language name lookup."""
        calc = StatsCalculator()

        keys_by_language = {
            'en': {'key': 'value'},
            'tr': {'key': 'değer'},
            'de': {'key': 'wert'}
        }

        stats = calc.calculate(keys_by_language)

        lang_names = {l.code: l.name for l in stats.languages}

        assert lang_names['en'] == 'English'
        assert lang_names['tr'] == 'Turkish'
        assert lang_names['de'] == 'German'

    def test_languages_sorted_by_completion(self):
        """Test languages are sorted by completion."""
        calc = StatsCalculator(source_lang='en')

        keys_by_language = {
            'en': {'k1': 'v1', 'k2': 'v2'},
            'tr': {'k1': 'v1'},  # 50%
            'de': {'k1': 'v1', 'k2': 'v2'}  # 100%
        }

        stats = calc.calculate(keys_by_language)

        # First should be highest completion
        assert stats.languages[0].code in ['en', 'de']  # Both 100%
        assert stats.languages[-1].code == 'tr'  # 50%


class TestStatsExport:
    """Test cases for stats export functionality."""

    def test_export_json(self):
        """Test JSON export."""
        calc = StatsCalculator()

        keys_by_language = {
            'en': {'key1': 'Hello'},
            'tr': {'key1': 'Merhaba'}
        }

        stats = calc.calculate(keys_by_language, project_name="TestProject")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'stats.json'
            calc.export_json(stats, output_path)

            assert output_path.exists()

            with open(output_path, 'r') as f:
                data = json.load(f)

            assert data['project_name'] == 'TestProject'
            assert data['summary']['total_languages'] == 2

    def test_export_markdown(self):
        """Test Markdown export."""
        calc = StatsCalculator()

        keys_by_language = {
            'en': {'key1': 'Hello', 'key2': 'World'},
            'tr': {'key1': 'Merhaba'}
        }

        stats = calc.calculate(keys_by_language)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'stats.md'
            calc.export_markdown(stats, output_path)

            assert output_path.exists()

            content = output_path.read_text()

            assert '# Localization Statistics' in content
            assert 'Total Languages' in content
            assert 'Turkish' in content


class TestCompletionBar:
    """Test cases for completion bar visualization."""

    def test_completion_bar_full(self):
        """Test 100% completion bar."""
        calc = StatsCalculator()
        bar = calc._completion_bar(100.0)

        assert '100.0%' in bar
        assert '█' in bar

    def test_completion_bar_empty(self):
        """Test 0% completion bar."""
        calc = StatsCalculator()
        bar = calc._completion_bar(0.0)

        assert '0.0%' in bar
        assert '░' in bar

    def test_completion_bar_partial(self):
        """Test partial completion bar."""
        calc = StatsCalculator()
        bar = calc._completion_bar(50.0)

        assert '50.0%' in bar


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
