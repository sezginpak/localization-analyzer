"""Tests for LocalizationFileManager."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from localization_analyzer.core.file_manager import LocalizationFileManager
from localization_analyzer.frameworks.swift import SwiftAdapter


class TestLocalizationFileManager:
    """Test cases for LocalizationFileManager."""

    def create_test_localization_dir(self, tmpdir):
        """Create test localization directory structure."""
        resources_dir = Path(tmpdir) / 'Resources'

        # English
        en_lproj = resources_dir / 'en.lproj'
        en_lproj.mkdir(parents=True)
        (en_lproj / 'Localizable.strings').write_text('''
"save" = "Save";
"cancel" = "Cancel";
"delete" = "Delete";
''')

        # Turkish
        tr_lproj = resources_dir / 'tr.lproj'
        tr_lproj.mkdir(parents=True)
        (tr_lproj / 'Localizable.strings').write_text('''
"save" = "Kaydet";
"cancel" = "İptal";
''')

        return resources_dir

    def test_init(self):
        """FileManager should initialize correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            assert fm.adapter == adapter
            assert fm.localization_dir == resources_dir

    def test_discover_languages(self):
        """Should discover available languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            assert 'en' in fm.languages
            assert 'tr' in fm.languages
            assert len(fm.languages) >= 2

    def test_discover_languages_nonexistent_dir(self, capfd):
        """Should handle non-existent directory gracefully."""
        adapter = SwiftAdapter()
        fm = LocalizationFileManager(adapter, Path('/nonexistent/path'))

        captured = capfd.readouterr()
        assert "not found" in captured.out

    def test_load_all_keys(self):
        """Should load all keys from all languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            assert 'save' in fm.keys
            assert 'cancel' in fm.keys
            assert 'delete' in fm.keys
            assert fm.keys['save']['en'] == 'Save'
            assert fm.keys['save']['tr'] == 'Kaydet'

    def test_key_exists(self):
        """Should check if key exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            assert fm.key_exists('save') is True
            assert fm.key_exists('nonexistent') is False

    def test_get_key_translations(self):
        """Should return all translations for a key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            translations = fm.get_key_translations('save')
            assert translations['en'] == 'Save'
            assert translations['tr'] == 'Kaydet'

    def test_get_key_translations_nonexistent(self):
        """Should return empty dict for nonexistent key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            translations = fm.get_key_translations('nonexistent')
            assert translations == {}

    def test_keys_by_language(self):
        """Should return keys grouped by language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            by_lang = fm.keys_by_language

            assert 'en' in by_lang
            assert 'tr' in by_lang
            assert by_lang['en']['save'] == 'Save'
            assert by_lang['tr']['save'] == 'Kaydet'

    def test_find_missing_translations(self):
        """Should find keys missing in some languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            missing = fm.find_missing_translations()

            # 'delete' is only in English, missing in Turkish
            assert 'delete' in missing
            assert 'tr' in missing['delete']

    def test_find_untranslated_keys(self):
        """Should find keys with same text as source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'

            # Create files with untranslated key
            en_lproj = resources_dir / 'en.lproj'
            en_lproj.mkdir(parents=True)
            (en_lproj / 'Localizable.strings').write_text('''
"ok" = "OK";
"hello" = "Hello";
''')

            tr_lproj = resources_dir / 'tr.lproj'
            tr_lproj.mkdir(parents=True)
            (tr_lproj / 'Localizable.strings').write_text('''
"ok" = "OK";
"hello" = "Merhaba";
''')

            adapter = SwiftAdapter()
            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            untranslated = fm.find_untranslated_keys(source_lang='en')

            # 'ok' has same value in both languages
            assert 'ok' in untranslated
            assert 'tr' in untranslated['ok']
            # 'hello' is translated
            assert 'hello' not in untranslated

    def test_get_language_stats(self):
        """Should return statistics per language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_localization_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            stats = fm.get_language_stats()

            assert 'en' in stats
            assert 'tr' in stats
            assert stats['en']['completion_percent'] == 100.0
            # Turkish is missing 'delete'
            assert stats['tr']['missing_keys'] >= 1


class TestAddKey:
    """Test cases for add_key method."""

    def create_test_dir(self, tmpdir):
        """Create test directory with empty strings files."""
        resources_dir = Path(tmpdir) / 'Resources'

        en_lproj = resources_dir / 'en.lproj'
        en_lproj.mkdir(parents=True)
        (en_lproj / 'Localizable.strings').write_text('')

        tr_lproj = resources_dir / 'tr.lproj'
        tr_lproj.mkdir(parents=True)
        (tr_lproj / 'Localizable.strings').write_text('')

        return resources_dir

    def test_add_key_dry_run(self, capfd):
        """Dry run should not write files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            result = fm.add_key(
                'new.key',
                {'en': 'New Value', 'tr': 'Yeni Değer'},
                dry_run=True
            )

            assert result is True
            captured = capfd.readouterr()
            assert "DRY RUN" in captured.out

            # Key should not be in memory
            assert 'new.key' not in fm.keys

    def test_add_key_already_exists(self, capfd):
        """Should warn if key already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = self.create_test_dir(tmpdir)
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)
            fm.keys = {'existing.key': {'en': 'Existing'}}

            result = fm.add_key(
                'existing.key',
                {'en': 'New Value'},
                dry_run=False,
                overwrite=False
            )

            assert result is False
            captured = capfd.readouterr()
            assert "already exists" in captured.out


class TestFindModuleFile:
    """Test cases for _find_module_file method."""

    def test_find_exact_match(self):
        """Should find file matching module name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            files = [
                Path('/test/Common.strings'),
                Path('/test/AI.strings'),
                Path('/test/Settings.strings'),
            ]

            result = fm._find_module_file(files, 'AI')
            assert result == Path('/test/AI.strings')

    def test_find_no_match_returns_first(self):
        """Should return first file if no match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            files = [
                Path('/test/Common.strings'),
                Path('/test/AI.strings'),
            ]

            result = fm._find_module_file(files, 'NonExistent')
            assert result == Path('/test/Common.strings')

    def test_find_no_module_returns_first(self):
        """Should return first file if no module specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            files = [
                Path('/test/Common.strings'),
                Path('/test/AI.strings'),
            ]

            result = fm._find_module_file(files, None)
            assert result == Path('/test/Common.strings')

    def test_find_empty_list(self):
        """Should return None for empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            adapter = SwiftAdapter()

            fm = LocalizationFileManager(adapter, resources_dir)

            result = fm._find_module_file([], 'Any')
            assert result is None


class TestValidateAllFiles:
    """Test cases for validate_all_files method."""

    def test_validate_valid_files(self):
        """Should return no errors for valid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'

            en_lproj = resources_dir / 'en.lproj'
            en_lproj.mkdir(parents=True)
            (en_lproj / 'Localizable.strings').write_text('''
"key" = "value";
''')

            adapter = SwiftAdapter()
            fm = LocalizationFileManager(adapter, resources_dir)

            errors = fm.validate_all_files()

            # Should have no errors for valid file
            assert 'en' not in errors or len(errors.get('en', [])) == 0


class TestSyncKeysAcrossLanguages:
    """Test cases for sync_keys_across_languages method."""

    def test_sync_dry_run(self, capfd):
        """Dry run should not modify files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'

            # English with keys
            en_lproj = resources_dir / 'en.lproj'
            en_lproj.mkdir(parents=True)
            (en_lproj / 'Localizable.strings').write_text('''
"key1" = "Value 1";
"key2" = "Value 2";
''')

            # Turkish with missing key
            tr_lproj = resources_dir / 'tr.lproj'
            tr_lproj.mkdir(parents=True)
            (tr_lproj / 'Localizable.strings').write_text('''
"key1" = "Değer 1";
''')

            adapter = SwiftAdapter()
            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            result = fm.sync_keys_across_languages('en', dry_run=True)

            captured = capfd.readouterr()
            assert "DRY RUN" in captured.out

    def test_sync_nonexistent_source(self, capfd):
        """Should error if source language doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            resources_dir.mkdir(parents=True)

            adapter = SwiftAdapter()
            fm = LocalizationFileManager(adapter, resources_dir)

            result = fm.sync_keys_across_languages('nonexistent')

            assert result == {}
            captured = capfd.readouterr()
            assert "not found" in captured.out


class TestModularStringsSupport:
    """Test cases for modular .strings file support."""

    def test_multiple_strings_files_per_language(self):
        """Should support multiple .strings files per language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'

            en_lproj = resources_dir / 'en.lproj'
            en_lproj.mkdir(parents=True)

            # Multiple module files
            (en_lproj / 'Common.strings').write_text('"common.key" = "Common";')
            (en_lproj / 'AI.strings').write_text('"ai.key" = "AI";')
            (en_lproj / 'Settings.strings').write_text('"settings.key" = "Settings";')

            adapter = SwiftAdapter()
            fm = LocalizationFileManager(adapter, resources_dir)
            fm.load_all_keys()

            # Should have all keys
            assert 'common.key' in fm.keys
            assert 'ai.key' in fm.keys
            assert 'settings.key' in fm.keys

            # Should track modules
            assert fm.key_modules.get('common.key') == 'Common'
            assert fm.key_modules.get('ai.key') == 'AI'
            assert fm.key_modules.get('settings.key') == 'Settings'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
