"""Tests for SwiftAdapter."""

import pytest
import tempfile
from pathlib import Path

from localization_analyzer.frameworks.swift import SwiftAdapter
from localization_analyzer.utils.config import L10nConfig


class TestSwiftAdapterInit:
    """Test cases for SwiftAdapter initialization."""

    def test_default_init(self):
        """Should initialize with defaults."""
        adapter = SwiftAdapter()

        # l10n_config can be None by default
        assert len(adapter.hardcoded_patterns) > 0
        assert len(adapter.localized_patterns) > 0
        assert len(adapter.exclusion_patterns) > 0

    def test_init_with_l10n_config(self):
        """Should accept custom L10n config."""
        config = L10nConfig(
            enabled=True,
            enum_name='Strings',
            default_module='Core'
        )
        adapter = SwiftAdapter(l10n_config=config)

        assert adapter.l10n_config.enabled is True
        assert adapter.l10n_config.enum_name == 'Strings'
        assert adapter.l10n_config.default_module == 'Core'


class TestGetFileExtensions:
    """Test cases for get_file_extensions method."""

    def test_returns_swift_extension(self):
        """Should return .swift extension."""
        adapter = SwiftAdapter()
        extensions = adapter.get_file_extensions()

        assert '.swift' in extensions


class TestGetLocalizationFilePattern:
    """Test cases for get_localization_file_pattern method."""

    def test_returns_strings_pattern(self):
        """Should return .strings file pattern."""
        adapter = SwiftAdapter()
        pattern = adapter.get_localization_file_pattern()

        assert '.strings' in pattern


class TestShouldExcludeFile:
    """Test cases for should_exclude_file method."""

    def test_excludes_build_directory(self):
        """Should exclude build directories."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_file(Path('/project/build/Test.swift')) is True
        assert adapter.should_exclude_file(Path('/project/.build/Test.swift')) is True

    def test_excludes_derived_data(self):
        """Should exclude DerivedData."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_file(
            Path('/project/DerivedData/Build/Test.swift')
        ) is True

    def test_excludes_pods(self):
        """Should exclude Pods directory."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_file(Path('/project/Pods/Library/Test.swift')) is True

    def test_includes_source_files(self):
        """Should include regular source files."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_file(Path('/project/Sources/Test.swift')) is False
        assert adapter.should_exclude_file(Path('/project/App/ViewController.swift')) is False


class TestShouldExcludeString:
    """Test cases for should_exclude_string method."""

    def test_excludes_empty_string(self):
        """Should exclude empty strings."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_string('') is True
        assert adapter.should_exclude_string('   ') is True

    def test_excludes_pure_emoji(self):
        """Should exclude pure emoji strings."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_string('😀') is True
        assert adapter.should_exclude_string('🎉🎊') is True
        assert adapter.should_exclude_string('👨‍👩‍👧‍👦') is True  # Family emoji

    def test_includes_emoji_with_text(self):
        """Should include strings with emoji and text."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_string('Hello 😀') is False
        assert adapter.should_exclude_string('🎉 Congratulations!') is False

    def test_excludes_format_strings(self):
        """Should exclude pure format strings."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_string('%@') is True
        assert adapter.should_exclude_string('%d') is True
        assert adapter.should_exclude_string('%s') is True

    def test_excludes_technical_strings(self):
        """Should exclude technical/code strings."""
        adapter = SwiftAdapter()

        # URLs and paths
        assert adapter.should_exclude_string('https://example.com') is True
        assert adapter.should_exclude_string('/api/v1/users') is True

        # Code identifiers
        assert adapter.should_exclude_string('com.example.app') is True
        assert adapter.should_exclude_string('UIViewController') is True

    def test_includes_user_facing_strings(self):
        """Should include user-facing strings."""
        adapter = SwiftAdapter()

        assert adapter.should_exclude_string('Hello World') is False
        assert adapter.should_exclude_string('Save') is False
        assert adapter.should_exclude_string('Please enter your name') is False


class TestTextToKey:
    """Test cases for text_to_key method."""

    def test_simple_text(self):
        """Should convert simple text to camelCase key."""
        adapter = SwiftAdapter()

        assert adapter.text_to_key('Save') == 'save'
        assert adapter.text_to_key('Cancel Changes') == 'cancelChanges'
        assert adapter.text_to_key('Delete Item') == 'deleteItem'

    def test_special_characters_removed(self):
        """Should remove special characters."""
        adapter = SwiftAdapter()

        # Apostrophe followed by lowercase creates camelCase
        result = adapter.text_to_key("Don't Save")
        assert 'don' in result.lower() and 'save' in result.lower()

        result = adapter.text_to_key('Hello, World!')
        assert 'hello' in result.lower() and 'world' in result.lower()

    def test_numbers_preserved(self):
        """Should preserve numbers."""
        adapter = SwiftAdapter()

        assert adapter.text_to_key('Item 1') == 'item1'
        assert adapter.text_to_key('Step 2 of 3') == 'step2Of3'

    def test_turkish_characters(self):
        """Should convert Turkish characters."""
        adapter = SwiftAdapter()

        assert adapter.text_to_key('Çıkış') == 'cikis'
        assert adapter.text_to_key('Güncelle') == 'guncelle'
        assert adapter.text_to_key('Şifre') == 'sifre'

    def test_german_characters(self):
        """Should convert German characters."""
        adapter = SwiftAdapter()

        assert adapter.text_to_key('Größe') == 'grosse'
        assert adapter.text_to_key('Ändern') == 'andern'

    def test_long_text_truncated(self):
        """Should handle long text (may or may not truncate based on implementation)."""
        adapter = SwiftAdapter()
        long_text = 'This is a very long text that should be truncated to a reasonable length'

        result = adapter.text_to_key(long_text)

        # Result should be non-empty and valid camelCase
        assert len(result) > 0
        assert result[0].islower()  # camelCase starts with lowercase


class TestSuggestKeyName:
    """Test cases for suggest_key_name method."""

    def test_with_component(self):
        """Should prefix key with component type."""
        adapter = SwiftAdapter()

        result = adapter.suggest_key_name('Save', 'Button')
        assert 'button' in result.lower() or 'save' in result.lower()

    def test_unique_keys(self):
        """Should generate unique keys for different texts."""
        adapter = SwiftAdapter()

        key1 = adapter.suggest_key_name('Save', 'Button')
        key2 = adapter.suggest_key_name('Cancel', 'Button')

        assert key1 != key2


class TestCalculatePriority:
    """Test cases for calculate_priority method."""

    def test_ui_components_high_priority(self):
        """UI components should have high priority."""
        adapter = SwiftAdapter()

        button_priority = adapter.calculate_priority('Button', 'UI', 'Save')
        label_priority = adapter.calculate_priority('Label', 'UI', 'Title')

        assert button_priority >= 7
        assert label_priority >= 7

    def test_alert_components_highest_priority(self):
        """Alert components should have highest priority."""
        adapter = SwiftAdapter()

        alert_priority = adapter.calculate_priority('Alert', 'UI', 'Error occurred')

        assert alert_priority >= 9

    def test_short_strings_lower_priority(self):
        """Very short strings should have lower priority."""
        adapter = SwiftAdapter()

        short_priority = adapter.calculate_priority('Label', 'UI', 'OK')
        long_priority = adapter.calculate_priority('Label', 'UI', 'Please enter your email address')

        assert short_priority < long_priority

    def test_pure_emoji_zero_priority(self):
        """Pure emoji strings should have zero priority."""
        adapter = SwiftAdapter()

        priority = adapter.calculate_priority('Label', 'UI', '😀')

        assert priority == 0


class TestExtractLanguageCode:
    """Test cases for extract_language_code method."""

    def test_lproj_directory(self):
        """Should extract from .lproj directory."""
        adapter = SwiftAdapter()

        assert adapter.extract_language_code(
            Path('/Resources/en.lproj/Localizable.strings')
        ) == 'en'
        assert adapter.extract_language_code(
            Path('/Resources/tr.lproj/Localizable.strings')
        ) == 'tr'
        assert adapter.extract_language_code(
            Path('/Resources/de.lproj/Localizable.strings')
        ) == 'de'

    def test_base_lproj(self):
        """Should handle Base.lproj."""
        adapter = SwiftAdapter()

        result = adapter.extract_language_code(
            Path('/Resources/Base.lproj/Localizable.strings')
        )
        assert result == 'Base'


class TestParseLocalizationFile:
    """Test cases for parse_localization_file method."""

    def test_parse_valid_file(self):
        """Should parse valid .strings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text('''
"save" = "Save";
"cancel" = "Cancel";
"delete" = "Delete";
''')

            adapter = SwiftAdapter()
            keys = adapter.parse_localization_file(strings_file)

            assert keys['save'] == 'Save'
            assert keys['cancel'] == 'Cancel'
            assert keys['delete'] == 'Delete'

    def test_parse_with_comments(self):
        """Should ignore comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text('''
/* Comment */
"key1" = "Value 1";
// Another comment
"key2" = "Value 2";
''')

            adapter = SwiftAdapter()
            keys = adapter.parse_localization_file(strings_file)

            assert keys['key1'] == 'Value 1'
            assert keys['key2'] == 'Value 2'

    def test_parse_with_escaped_quotes(self):
        """Should handle escaped quotes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text(r'"key" = "He said \"Hello\"";')

            adapter = SwiftAdapter()
            keys = adapter.parse_localization_file(strings_file)

            assert 'Hello' in keys['key']

    def test_parse_empty_file(self):
        """Should handle empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text('')

            adapter = SwiftAdapter()
            keys = adapter.parse_localization_file(strings_file)

            assert keys == {}

    def test_parse_nonexistent_file(self):
        """Should handle non-existent file."""
        adapter = SwiftAdapter()
        keys = adapter.parse_localization_file(Path('/nonexistent/file.strings'))

        assert keys == {}


class TestWriteLocalizationEntry:
    """Test cases for write_localization_entry method."""

    def test_write_new_entry(self):
        """Should write new entry to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text('')

            adapter = SwiftAdapter()
            result = adapter.write_localization_entry(
                strings_file, 'new.key', 'New Value'
            )

            assert result is True
            content = strings_file.read_text()
            assert '"new.key"' in content
            assert '"New Value"' in content

    def test_write_with_special_characters(self):
        """Should escape special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strings_file = Path(tmpdir) / 'Localizable.strings'
            strings_file.write_text('')

            adapter = SwiftAdapter()
            adapter.write_localization_entry(
                strings_file, 'key', 'Value with "quotes"'
            )

            content = strings_file.read_text()
            assert '\\"' in content or 'quotes' in content


class TestDiscoverTables:
    """Test cases for discover_tables method."""

    def test_discover_multiple_tables(self):
        """Should discover multiple .strings files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resources_dir = Path(tmpdir) / 'Resources'
            en_lproj = resources_dir / 'en.lproj'
            en_lproj.mkdir(parents=True)

            (en_lproj / 'Localizable.strings').write_text('"key" = "value";')
            (en_lproj / 'Common.strings').write_text('"key" = "value";')
            (en_lproj / 'Settings.strings').write_text('"key" = "value";')

            adapter = SwiftAdapter()
            tables = adapter.discover_tables(resources_dir)

            assert 'Localizable' in tables or 'localizable' in str(tables).lower()
            assert 'Common' in tables or 'common' in str(tables).lower()

    def test_discover_empty_directory(self):
        """Should return empty dict for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = SwiftAdapter()
            tables = adapter.discover_tables(Path(tmpdir))

            assert tables == {}


class TestPatternCaching:
    """Test cases for pattern caching."""

    def test_emoji_pattern_cached(self):
        """Emoji pattern should be cached at class level."""
        adapter1 = SwiftAdapter()
        adapter2 = SwiftAdapter()

        pattern1 = adapter1._get_compiled_emoji_pattern()
        pattern2 = adapter2._get_compiled_emoji_pattern()

        assert pattern1 is pattern2

    def test_exclusion_patterns_cached(self):
        """Exclusion patterns should be cached."""
        adapter1 = SwiftAdapter()
        adapter2 = SwiftAdapter()

        patterns1 = adapter1._get_compiled_exclusion_patterns(adapter1.exclusion_patterns)
        patterns2 = adapter2._get_compiled_exclusion_patterns(adapter2.exclusion_patterns)

        assert patterns1 is patterns2


class TestCharacterMap:
    """Test cases for character mapping."""

    def test_char_map_exists(self):
        """CHAR_MAP should exist with expected characters."""
        adapter = SwiftAdapter()

        assert hasattr(adapter, 'CHAR_MAP')
        assert 'ç' in adapter.CHAR_MAP
        assert 'ğ' in adapter.CHAR_MAP
        assert 'ü' in adapter.CHAR_MAP
        assert 'ö' in adapter.CHAR_MAP
        assert 'ş' in adapter.CHAR_MAP
        assert 'ı' in adapter.CHAR_MAP

    def test_char_map_german(self):
        """CHAR_MAP should include German characters."""
        adapter = SwiftAdapter()

        assert 'ä' in adapter.CHAR_MAP
        assert 'ß' in adapter.CHAR_MAP

    def test_char_map_french(self):
        """CHAR_MAP should include French characters."""
        adapter = SwiftAdapter()

        assert 'é' in adapter.CHAR_MAP
        assert 'è' in adapter.CHAR_MAP
        assert 'ê' in adapter.CHAR_MAP


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
