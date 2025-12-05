"""Tests for report generators (console and JSON)."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Set, Dict

from localization_analyzer.reports.console_reporter import ConsoleReporter
from localization_analyzer.reports.json_reporter import JSONReporter
from localization_analyzer.core.health_calculator import HealthScore
from localization_analyzer.frameworks.base import HardcodedString


@dataclass
class MockAnalysisResult:
    """Mock analysis result for testing."""
    health: HealthScore
    hardcoded_strings: List[HardcodedString] = field(default_factory=list)
    localized_usages: list = field(default_factory=list)
    used_keys: Set[str] = field(default_factory=set)
    dead_keys: Set[str] = field(default_factory=set)
    missing_keys: Dict[str, List[str]] = field(default_factory=dict)
    dynamic_keys: Dict[str, List[str]] = field(default_factory=dict)
    duplicates: Dict[str, List[HardcodedString]] = field(default_factory=dict)
    component_stats: Dict[str, Dict] = field(default_factory=dict)
    file_stats: Dict[str, Dict] = field(default_factory=dict)
    folder_stats: Dict[str, Dict] = field(default_factory=dict)


class TestConsoleReporter:
    """Test cases for ConsoleReporter."""

    def create_mock_health(self):
        """Create a mock health score."""
        return HealthScore(
            score=85,
            grade='B',
            localized_count=100,
            hardcoded_count=15,
            total_strings=115,
            localization_rate=87.0,
            missing_keys_count=5,
            dead_keys_count=3,
            duplicate_count=2
        )

    def create_mock_file_manager(self):
        """Create a mock file manager."""
        mock = MagicMock()
        mock.get_language_stats.return_value = {
            'en': {'total_keys': 100, 'missing_keys': 0, 'completion_percent': 100.0},
            'tr': {'total_keys': 95, 'missing_keys': 5, 'completion_percent': 95.0},
        }
        mock.languages = {
            'en': [Path('/test/en.lproj/Localizable.strings')],
            'tr': [Path('/test/tr.lproj/Localizable.strings')],
        }
        mock.key_modules = {'test.key': 'Common'}
        return mock

    def test_print_full_report_no_details(self, capfd):
        """Full report without details should print basic info."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()

        ConsoleReporter.print_full_report(result, file_manager, show_details=False)

        captured = capfd.readouterr()
        assert "LOCALIZATION ANALYSIS REPORT" in captured.out
        assert "HEALTH SCORE" in captured.out
        assert "85/100" in captured.out
        assert "LANGUAGES" in captured.out

    def test_print_full_report_with_details(self, capfd):
        """Full report with details should print all sections."""
        health = self.create_mock_health()
        hardcoded = HardcodedString(
            file='test.swift',
            line=10,
            text='Test string',
            component='Label',
            category='UI',
            priority=8,
            suggested_key='testString'
        )
        result = MockAnalysisResult(
            health=health,
            hardcoded_strings=[hardcoded],
            missing_keys={'missing.key': ['file1.swift']},
            dead_keys={'dead.key'},
            duplicates={'Duplicate': [hardcoded, hardcoded]}
        )
        file_manager = self.create_mock_file_manager()

        ConsoleReporter.print_full_report(result, file_manager, show_details=True)

        captured = capfd.readouterr()
        assert "TOP HARDCODED STRINGS" in captured.out
        assert "MISSING KEYS" in captured.out
        assert "DEAD KEYS" in captured.out

    def test_print_header(self, capfd):
        """Header should print title."""
        ConsoleReporter._print_header()
        captured = capfd.readouterr()
        assert "LOCALIZATION ANALYSIS REPORT" in captured.out
        assert "=" in captured.out

    def test_print_health_score(self, capfd):
        """Health score section should print all metrics."""
        health = self.create_mock_health()
        ConsoleReporter._print_health_score(health)
        captured = capfd.readouterr()

        assert "HEALTH SCORE" in captured.out
        assert "85/100" in captured.out
        assert "Localized Strings: 100" in captured.out
        assert "Hardcoded Strings: 15" in captured.out
        assert "Missing Keys: 5" in captured.out
        assert "Dead Keys: 3" in captured.out

    def test_print_language_stats(self, capfd):
        """Language stats should print table."""
        file_manager = self.create_mock_file_manager()
        ConsoleReporter._print_language_stats(file_manager)
        captured = capfd.readouterr()

        assert "LANGUAGES" in captured.out
        assert "Language" in captured.out
        assert "Keys" in captured.out
        assert "Missing" in captured.out
        assert "Completion" in captured.out

    def test_print_language_stats_empty(self, capfd):
        """Empty language stats should show message."""
        mock = MagicMock()
        mock.get_language_stats.return_value = {}
        ConsoleReporter._print_language_stats(mock)
        captured = capfd.readouterr()
        assert "No languages found" in captured.out

    def test_print_hardcoded_strings(self, capfd):
        """Hardcoded strings section should print items."""
        strings = [
            HardcodedString(
                file='test.swift',
                line=10,
                text='Test string',
                component='Label',
                category='UI',
                priority=9,
                suggested_key='testString'
            )
        ]
        ConsoleReporter._print_hardcoded_strings(strings)
        captured = capfd.readouterr()

        assert "TOP HARDCODED STRINGS" in captured.out
        assert "test.swift:10" in captured.out
        assert "testString" in captured.out

    def test_print_hardcoded_strings_empty(self, capfd):
        """Empty hardcoded strings should print nothing."""
        ConsoleReporter._print_hardcoded_strings([])
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_print_missing_keys(self, capfd):
        """Missing keys section should print keys."""
        missing = {'test.key': ['file1.swift', 'file2.swift']}
        mock_fm = MagicMock()
        mock_fm.key_modules = {'test.key': 'Common'}

        ConsoleReporter._print_missing_keys(missing, mock_fm)
        captured = capfd.readouterr()

        assert "MISSING KEYS" in captured.out
        assert "test.key" in captured.out

    def test_print_missing_keys_empty(self, capfd):
        """Empty missing keys should print nothing."""
        ConsoleReporter._print_missing_keys({}, MagicMock())
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_print_dynamic_keys(self, capfd):
        """Dynamic keys section should print keys."""
        dynamic = {'activity.\\(id)': ['file1.swift']}
        ConsoleReporter._print_dynamic_keys(dynamic)
        captured = capfd.readouterr()

        assert "DYNAMIC KEYS" in captured.out
        assert "runtime-generated" in captured.out

    def test_print_dynamic_keys_empty(self, capfd):
        """Empty dynamic keys should print nothing."""
        ConsoleReporter._print_dynamic_keys({})
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_print_dead_keys(self, capfd):
        """Dead keys section should print keys."""
        dead = {'dead.key1', 'dead.key2'}
        mock_fm = MagicMock()
        mock_fm.key_modules = {'dead.key1': 'Common'}

        ConsoleReporter._print_dead_keys(dead, mock_fm)
        captured = capfd.readouterr()

        assert "DEAD KEYS" in captured.out
        assert "dead.key" in captured.out

    def test_print_dead_keys_empty(self, capfd):
        """Empty dead keys should print nothing."""
        ConsoleReporter._print_dead_keys(set(), MagicMock())
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_print_duplicates(self, capfd):
        """Duplicates section should print items."""
        hardcoded = HardcodedString(
            file='test.swift', line=10, text='Duplicate',
            component='Label', category='UI', priority=5,
            suggested_key='duplicate'
        )
        duplicates = {'Duplicate text': [hardcoded, hardcoded]}

        ConsoleReporter._print_duplicates(duplicates)
        captured = capfd.readouterr()

        assert "DUPLICATE STRINGS" in captured.out
        assert "2 occurrences" in captured.out

    def test_print_duplicates_empty(self, capfd):
        """Empty duplicates should print nothing."""
        ConsoleReporter._print_duplicates({})
        captured = capfd.readouterr()
        assert captured.out == ""

    def test_create_progress_bar_high(self):
        """High percentage should be green."""
        bar = ConsoleReporter._create_progress_bar(95.0)
        assert "95.0%" in bar
        assert "█" in bar

    def test_create_progress_bar_medium(self):
        """Medium percentage should be cyan."""
        bar = ConsoleReporter._create_progress_bar(75.0)
        assert "75.0%" in bar

    def test_create_progress_bar_low(self):
        """Low percentage should be yellow."""
        bar = ConsoleReporter._create_progress_bar(50.0)
        assert "50.0%" in bar


class TestJSONReporter:
    """Test cases for JSONReporter."""

    def create_mock_health(self):
        """Create a mock health score."""
        return HealthScore(
            score=85,
            grade='B',
            localized_count=100,
            hardcoded_count=15,
            total_strings=115,
            localization_rate=87.0,
            missing_keys_count=5,
            dead_keys_count=3,
            duplicate_count=2
        )

    def create_mock_file_manager(self):
        """Create a mock file manager."""
        mock = MagicMock()
        mock.get_language_stats.return_value = {
            'en': {'total_keys': 100, 'missing_keys': 0, 'completion_percent': 100.0}
        }
        mock.key_modules = {}
        mock.find_missing_translations.return_value = {}
        mock.find_untranslated_keys.return_value = {}
        return mock

    def create_mock_adapter(self):
        """Create a mock adapter."""
        mock = MagicMock()
        mock.__class__.__name__ = 'SwiftAdapter'
        return mock

    def test_generate_creates_file(self):
        """Generate should create JSON file."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            returned_path = JSONReporter.generate(
                result, file_manager, adapter, output_path
            )

            assert output_path.exists()
            assert returned_path == output_path

            with open(output_path) as f:
                data = json.load(f)

            assert 'metadata' in data
            assert 'health_score' in data
            assert data['health_score']['score'] == 85

    def test_generate_with_hardcoded_strings(self):
        """Generate should include hardcoded strings."""
        health = self.create_mock_health()
        hardcoded = HardcodedString(
            file='test.swift', line=10, text='Test',
            component='Label', category='UI', priority=8,
            suggested_key='test'
        )
        result = MockAnalysisResult(
            health=health,
            hardcoded_strings=[hardcoded]
        )
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert len(data['hardcoded_strings']) == 1
            assert data['hardcoded_strings'][0]['file'] == 'test.swift'
            assert data['hardcoded_strings'][0]['line'] == 10

    def test_generate_with_missing_keys(self):
        """Generate should include missing keys."""
        health = self.create_mock_health()
        result = MockAnalysisResult(
            health=health,
            missing_keys={'missing.key': ['file1.swift']}
        )
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert 'missing.key' in data['missing_keys']
            assert 'file1.swift' in data['missing_keys']['missing.key']['files']

    def test_generate_with_dead_keys(self):
        """Generate should include dead keys."""
        health = self.create_mock_health()
        result = MockAnalysisResult(
            health=health,
            dead_keys={'dead.key1', 'dead.key2'}
        )
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert len(data['dead_keys']) == 2

    def test_generate_with_duplicates(self):
        """Generate should include duplicates."""
        health = self.create_mock_health()
        hardcoded = HardcodedString(
            file='test.swift', line=10, text='Dup',
            component='Label', category='UI', priority=5,
            suggested_key='dup'
        )
        result = MockAnalysisResult(
            health=health,
            duplicates={'Duplicate': [hardcoded, hardcoded]}
        )
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert 'Duplicate' in data['duplicates']
            assert len(data['duplicates']['Duplicate']) == 2

    def test_generate_creates_directory(self):
        """Generate should create parent directories."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'subdir' / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_generate_pretty_print(self):
        """Generate with pretty=True should indent JSON."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(
                result, file_manager, adapter, output_path, pretty=True
            )

            content = output_path.read_text()
            assert '\n' in content  # Pretty print has newlines
            assert '  ' in content  # Has indentation

    def test_generate_compact(self):
        """Generate with pretty=False should be compact."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(
                result, file_manager, adapter, output_path, pretty=False
            )

            content = output_path.read_text()
            # Compact JSON is typically a single line (no indentation)
            assert '  "' not in content

    def test_generate_default_path(self, capfd):
        """Generate without path should use default."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        # Change to temp directory to avoid creating file in project
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                returned_path = JSONReporter.generate(
                    result, file_manager, adapter, output_path=None
                )
                assert returned_path.name == 'localization_report.json'
                assert returned_path.exists()
            finally:
                os.chdir(old_cwd)

    def test_load_report(self):
        """Load should read JSON report."""
        test_data = {'test': 'value', 'number': 42}

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / 'report.json'
            with open(report_path, 'w') as f:
                json.dump(test_data, f)

            loaded = JSONReporter.load(report_path)
            assert loaded == test_data

    def test_metadata_includes_timestamp(self):
        """Metadata should include generation timestamp."""
        health = self.create_mock_health()
        result = MockAnalysisResult(health=health)
        file_manager = self.create_mock_file_manager()
        adapter = self.create_mock_adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.json'
            JSONReporter.generate(result, file_manager, adapter, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert 'generated_at' in data['metadata']
            assert 'version' in data['metadata']
            assert data['metadata']['framework'] == 'swift'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
