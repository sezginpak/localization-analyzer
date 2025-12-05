"""Tests for the diff module."""

import pytest
import json
from pathlib import Path
import tempfile

from localization_analyzer.features.diff import (
    LocalizationDiff,
    DiffResult,
    DiffEntry,
    DiffType
)


class TestDiffEntry:
    """Test cases for DiffEntry."""

    def test_create_removed(self):
        """Test creating a removed entry."""
        entry = DiffEntry(
            key='test.key',
            diff_type=DiffType.REMOVED,
            source_value='Hello',
            target_value=None
        )

        assert entry.key == 'test.key'
        assert entry.diff_type == DiffType.REMOVED
        assert entry.source_value == 'Hello'
        assert entry.target_value is None

    def test_create_added(self):
        """Test creating an added entry."""
        entry = DiffEntry(
            key='new.key',
            diff_type=DiffType.ADDED,
            source_value=None,
            target_value='Merhaba'
        )

        assert entry.diff_type == DiffType.ADDED
        assert entry.target_value == 'Merhaba'


class TestDiffResult:
    """Test cases for DiffResult."""

    def test_empty_result(self):
        """Test empty result."""
        result = DiffResult(source_lang='en', target_lang='tr')

        assert result.total_differences == 0
        assert not result.has_differences
        assert result.added == []
        assert result.removed == []

    def test_with_differences(self):
        """Test result with differences."""
        result = DiffResult(source_lang='en', target_lang='tr')
        result.added.append(DiffEntry(key='k1', diff_type=DiffType.ADDED))
        result.removed.append(DiffEntry(key='k2', diff_type=DiffType.REMOVED))
        result.changed.append(DiffEntry(key='k3', diff_type=DiffType.CHANGED))

        assert result.total_differences == 3
        assert result.has_differences


class TestLocalizationDiff:
    """Test cases for LocalizationDiff."""

    def test_compare_identical(self):
        """Test comparing identical languages."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello', 'key2': 'World'}
        target = {'key1': 'Hello', 'key2': 'World'}

        result = differ.compare(source, target)

        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert len(result.changed) == 0
        assert len(result.same) == 2  # Both are same

    def test_compare_missing_in_target(self):
        """Test detecting missing keys in target."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello', 'key2': 'World'}
        target = {'key1': 'Merhaba'}  # Missing key2

        result = differ.compare(source, target, 'en', 'tr')

        assert len(result.removed) == 1
        assert result.removed[0].key == 'key2'
        assert result.removed[0].source_value == 'World'

    def test_compare_extra_in_target(self):
        """Test detecting extra keys in target."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello'}
        target = {'key1': 'Merhaba', 'key2': 'Dünya'}  # Extra key2

        result = differ.compare(source, target, 'en', 'tr')

        assert len(result.added) == 1
        assert result.added[0].key == 'key2'
        assert result.added[0].target_value == 'Dünya'

    def test_compare_changed_values(self):
        """Test detecting changed (translated) values."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello', 'key2': 'World'}
        target = {'key1': 'Merhaba', 'key2': 'Dünya'}

        result = differ.compare(source, target, 'en', 'tr')

        assert len(result.changed) == 2
        assert len(result.same) == 0

        key1_entry = next(e for e in result.changed if e.key == 'key1')
        assert key1_entry.source_value == 'Hello'
        assert key1_entry.target_value == 'Merhaba'

    def test_compare_same_values(self):
        """Test detecting same (untranslated) values."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello', 'key2': 'OK'}
        target = {'key1': 'Merhaba', 'key2': 'OK'}  # key2 same as source

        result = differ.compare(source, target, 'en', 'tr')

        assert len(result.changed) == 1  # key1
        assert len(result.same) == 1  # key2
        assert result.same[0].key == 'key2'

    def test_compare_complex(self):
        """Test complex comparison with all types."""
        differ = LocalizationDiff()

        source = {
            'translated': 'Hello',
            'untranslated': 'OK',
            'missing': 'World'
        }
        target = {
            'translated': 'Merhaba',
            'untranslated': 'OK',
            'extra': 'Ekstra'
        }

        result = differ.compare(source, target, 'en', 'tr')

        assert len(result.changed) == 1  # translated
        assert len(result.same) == 1  # untranslated
        assert len(result.removed) == 1  # missing
        assert len(result.added) == 1  # extra

    def test_results_sorted(self):
        """Test results are sorted by key."""
        differ = LocalizationDiff()

        source = {'z_key': 'Z', 'a_key': 'A', 'm_key': 'M'}
        target = {}

        result = differ.compare(source, target)

        keys = [e.key for e in result.removed]
        assert keys == ['a_key', 'm_key', 'z_key']


class TestDiffExport:
    """Test cases for diff export functionality."""

    def test_export_json(self):
        """Test JSON export."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello'}
        target = {}

        result = differ.compare(source, target, 'en', 'tr')

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'diff.json'
            differ.export_diff(result, output_path, format='json')

            assert output_path.exists()

            with open(output_path, 'r') as f:
                data = json.load(f)

            assert data['source_lang'] == 'en'
            assert data['target_lang'] == 'tr'
            assert data['summary']['missing'] == 1

    def test_export_markdown(self):
        """Test Markdown export."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello', 'key2': 'World'}
        target = {'key1': 'Merhaba'}

        result = differ.compare(source, target, 'en', 'tr')

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'diff.md'
            differ.export_diff(result, output_path, format='md')

            assert output_path.exists()

            content = output_path.read_text()

            assert '# Localization Diff' in content
            assert 'Missing in tr' in content
            assert 'key2' in content

    def test_export_txt(self):
        """Test text export."""
        differ = LocalizationDiff()

        source = {'key1': 'Hello'}
        target = {'key1': 'Merhaba', 'key2': 'Extra'}

        result = differ.compare(source, target, 'en', 'tr')

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'diff.txt'
            differ.export_diff(result, output_path, format='txt')

            assert output_path.exists()

            content = output_path.read_text()
            assert 'Localization Diff' in content


class TestTruncate:
    """Test cases for text truncation."""

    def test_short_text(self):
        """Test short text not truncated."""
        differ = LocalizationDiff()
        result = differ._truncate("Hello", max_len=50)
        assert result == "Hello"

    def test_long_text(self):
        """Test long text truncated."""
        differ = LocalizationDiff()
        long_text = "A" * 100
        result = differ._truncate(long_text, max_len=50)

        assert len(result) == 50
        assert result.endswith("...")

    def test_empty_text(self):
        """Test empty text."""
        differ = LocalizationDiff()
        assert differ._truncate("") == ""
        assert differ._truncate(None) == ""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
