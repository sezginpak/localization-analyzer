"""Tests for the sync module."""

import pytest
import json
from pathlib import Path
import tempfile

from localization_analyzer.features.sync import (
    LocalizationSync,
    SyncResult,
    SyncSummary
)


class TestSyncResult:
    """Test cases for SyncResult."""

    def test_default_values(self):
        """Test default values."""
        result = SyncResult(language='tr')

        assert result.language == 'tr'
        assert result.added_keys == []
        assert result.translated_keys == []
        assert result.failed_keys == []
        assert result.skipped_keys == []

    def test_total_processed(self):
        """Test total processed count."""
        result = SyncResult(language='tr')
        result.added_keys = ['key1', 'key2', 'key3']

        assert result.total_processed == 3

    def test_success_count(self):
        """Test success count."""
        result = SyncResult(language='tr')
        result.translated_keys = ['key1', 'key2']

        assert result.success_count == 2

    def test_failure_count(self):
        """Test failure count."""
        result = SyncResult(language='tr')
        result.failed_keys = ['key1']

        assert result.failure_count == 1


class TestSyncSummary:
    """Test cases for SyncSummary."""

    def test_default_values(self):
        """Test default values."""
        summary = SyncSummary(source_lang='en')

        assert summary.source_lang == 'en'
        assert summary.results == []
        assert summary.backup_paths == {}
        assert summary.dry_run is False

    def test_total_languages(self):
        """Test total languages count."""
        summary = SyncSummary(source_lang='en')
        summary.results = [
            SyncResult(language='tr'),
            SyncResult(language='de')
        ]

        assert summary.total_languages == 2

    def test_total_keys_added(self):
        """Test total keys added count."""
        summary = SyncSummary(source_lang='en')

        result1 = SyncResult(language='tr')
        result1.added_keys = ['key1', 'key2']

        result2 = SyncResult(language='de')
        result2.added_keys = ['key1', 'key2', 'key3']

        summary.results = [result1, result2]

        assert summary.total_keys_added == 5

    def test_has_changes_true(self):
        """Test has changes detection."""
        summary = SyncSummary(source_lang='en')
        result = SyncResult(language='tr')
        result.added_keys = ['key1']
        summary.results = [result]

        assert summary.has_changes is True

    def test_has_changes_false(self):
        """Test no changes detection."""
        summary = SyncSummary(source_lang='en')
        summary.results = [SyncResult(language='tr')]

        assert summary.has_changes is False


class TestLocalizationSync:
    """Test cases for LocalizationSync."""

    def test_init_default(self):
        """Test default initialization."""
        syncer = LocalizationSync()

        assert syncer.source_lang == 'en'
        assert syncer.auto_translate is True
        assert syncer.backup is True

    def test_init_custom(self):
        """Test custom initialization."""
        syncer = LocalizationSync(
            source_lang='de',
            auto_translate=False,
            backup=False
        )

        assert syncer.source_lang == 'de'
        assert syncer.auto_translate is False
        assert syncer.backup is False

    def test_sync_language_no_missing(self):
        """Test syncing language with no missing keys."""
        syncer = LocalizationSync(auto_translate=False)

        source_keys = {'key1': 'Hello', 'key2': 'World'}
        current_keys = {'key1': 'Merhaba', 'key2': 'Dünya'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.strings', delete=False) as f:
            f.write('"key1" = "Merhaba";\n')
            f.write('"key2" = "Dünya";\n')
            file_path = Path(f.name)

        try:
            result = syncer.sync_language(
                lang='tr',
                source_keys=source_keys,
                current_keys=current_keys,
                file_path=file_path,
                dry_run=True
            )

            assert len(result.added_keys) == 0
            assert result.total_processed == 0
        finally:
            file_path.unlink()

    def test_sync_language_with_missing(self):
        """Test syncing language with missing keys."""
        syncer = LocalizationSync(auto_translate=False)

        source_keys = {'key1': 'Hello', 'key2': 'World', 'key3': 'Test'}
        current_keys = {'key1': 'Merhaba'}  # Missing key2 and key3

        with tempfile.NamedTemporaryFile(mode='w', suffix='.strings', delete=False) as f:
            f.write('"key1" = "Merhaba";\n')
            file_path = Path(f.name)

        try:
            result = syncer.sync_language(
                lang='tr',
                source_keys=source_keys,
                current_keys=current_keys,
                file_path=file_path,
                dry_run=True
            )

            assert len(result.added_keys) == 2
            assert 'key2' in result.added_keys
            assert 'key3' in result.added_keys
            assert result.total_processed == 2
        finally:
            file_path.unlink()

    def test_sync_language_dry_run(self):
        """Test dry run doesn't modify files."""
        syncer = LocalizationSync(auto_translate=False)

        source_keys = {'key1': 'Hello', 'key2': 'World'}
        current_keys = {'key1': 'Merhaba'}

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'tr.strings'
            file_path.write_text('"key1" = "Merhaba";\n')
            original_content = file_path.read_text()

            result = syncer.sync_language(
                lang='tr',
                source_keys=source_keys,
                current_keys=current_keys,
                file_path=file_path,
                dry_run=True
            )

            # File should not be modified
            assert file_path.read_text() == original_content
            assert len(result.added_keys) == 1

    def test_sync_all_multiple_languages(self):
        """Test syncing multiple languages."""
        syncer = LocalizationSync(auto_translate=False)

        source_keys = {'key1': 'Hello', 'key2': 'World'}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create target files
            tr_file = Path(tmpdir) / 'tr.strings'
            de_file = Path(tmpdir) / 'de.strings'

            tr_file.write_text('"key1" = "Merhaba";\n')
            de_file.write_text('')  # Empty - missing both keys

            target_files = {
                'tr': tr_file,
                'de': de_file
            }

            target_keys = {
                'tr': {'key1': 'Merhaba'},
                'de': {}
            }

            summary = syncer.sync_all(
                source_keys=source_keys,
                target_files=target_files,
                target_keys=target_keys,
                dry_run=True
            )

            assert summary.total_languages == 2

            # Check tr result
            tr_result = next(r for r in summary.results if r.language == 'tr')
            assert len(tr_result.added_keys) == 1
            assert 'key2' in tr_result.added_keys

            # Check de result
            de_result = next(r for r in summary.results if r.language == 'de')
            assert len(de_result.added_keys) == 2


class TestSyncExport:
    """Test cases for sync export functionality."""

    def test_export_json(self):
        """Test JSON export."""
        syncer = LocalizationSync()

        summary = SyncSummary(source_lang='en', dry_run=True)
        result = SyncResult(language='tr')
        result.added_keys = ['key1', 'key2']
        result.translated_keys = ['key1']
        result.failed_keys = ['key2']
        summary.results = [result]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'sync_report.json'
            syncer.export_report(summary, output_path, format='json')

            assert output_path.exists()

            with open(output_path, 'r') as f:
                data = json.load(f)

            assert data['source_lang'] == 'en'
            assert data['dry_run'] is True
            assert data['summary']['total_languages'] == 1
            assert data['summary']['total_keys_added'] == 2

    def test_export_markdown(self):
        """Test Markdown export."""
        syncer = LocalizationSync()

        summary = SyncSummary(source_lang='en')
        result = SyncResult(language='tr')
        result.added_keys = ['key1', 'key2']
        result.translated_keys = ['key1', 'key2']
        summary.results = [result]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'sync_report.md'
            syncer.export_report(summary, output_path, format='md')

            assert output_path.exists()

            content = output_path.read_text()
            assert '# Localization Sync Report' in content
            assert 'Source Language' in content
            assert 'tr' in content


class TestBackup:
    """Test cases for backup functionality."""

    def test_create_backup(self):
        """Test backup creation."""
        syncer = LocalizationSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('"key1" = "value1";\n')

            backup_path = syncer._create_backup(file_path)

            assert backup_path is not None
            assert backup_path.exists()
            assert 'backup' in backup_path.name
            assert backup_path.read_text() == file_path.read_text()

    def test_create_backup_nonexistent(self):
        """Test backup with nonexistent file."""
        syncer = LocalizationSync()

        backup_path = syncer._create_backup(Path('/nonexistent/file.strings'))

        assert backup_path is None


class TestAppendToFile:
    """Test cases for file append functionality."""

    def test_append_entries(self):
        """Test appending entries to file."""
        syncer = LocalizationSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('"existing" = "value";\n')

            entries = {'new_key': 'new_value', 'another': 'another value'}
            syncer._append_to_file(file_path, entries)

            content = file_path.read_text()

            assert '"existing" = "value";' in content
            assert '"new_key" = "new_value";' in content
            assert '"another" = "another value";' in content
            assert 'Auto-synced entries' in content

    def test_append_with_quotes(self):
        """Test appending entries with quotes in value."""
        syncer = LocalizationSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('')

            entries = {'key': 'Say "Hello"'}
            syncer._append_to_file(file_path, entries)

            content = file_path.read_text()

            # Quotes should be escaped
            assert '\\"Hello\\"' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
