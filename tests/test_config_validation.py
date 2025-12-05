"""Tests for configuration validation."""

import pytest
from pathlib import Path
import tempfile
import yaml

from localization_analyzer.utils.config import (
    Config,
    ConfigValidationError,
    ConfigValidationWarning,
    ProjectConfig,
    PathsConfig,
    LanguagesConfig,
    L10nConfig,
    AutoFixConfig,
    ReportsConfig,
)


class TestConfigValidation:
    """Test cases for Config.validate() method."""

    def test_valid_default_config(self):
        """Default config should pass validation."""
        config = Config()
        errors, warnings = config.validate()
        assert len(errors) == 0

    def test_invalid_framework(self):
        """Invalid framework should cause error."""
        config = Config()
        config.project.framework = "invalid_framework"
        errors, warnings = config.validate()
        assert len(errors) == 1
        assert "Invalid framework" in errors[0]

    def test_valid_frameworks(self):
        """All valid frameworks should pass."""
        for framework in ['swift', 'react', 'flutter', 'android']:
            config = Config()
            config.project.framework = framework
            errors, warnings = config.validate()
            assert len(errors) == 0, f"Framework '{framework}' should be valid"

    def test_invalid_primary_language(self):
        """Invalid primary language code should cause error."""
        config = Config()
        config.languages.primary = "invalid"
        errors, warnings = config.validate()
        assert len(errors) == 1
        assert "Invalid primary language code" in errors[0]

    def test_valid_language_codes(self):
        """Valid language codes should pass."""
        valid_codes = ['en', 'tr', 'de', 'fr', 'en-US', 'pt-BR', 'zh-Hans']
        for code in valid_codes:
            config = Config()
            config.languages.primary = code
            config.languages.supported = [code]
            errors, warnings = config.validate()
            # Filter out only language-related errors
            lang_errors = [e for e in errors if "language" in e.lower()]
            assert len(lang_errors) == 0, f"Language code '{code}' should be valid"

    def test_invalid_supported_language(self):
        """Invalid supported language code should cause error."""
        config = Config()
        config.languages.supported = ['en', 'invalid_lang']
        errors, warnings = config.validate()
        assert any("Invalid supported language code" in e for e in errors)

    def test_primary_not_in_supported_warning(self):
        """Primary language not in supported should produce warning."""
        config = Config()
        config.languages.primary = 'tr'
        config.languages.supported = ['en', 'de']
        errors, warnings = config.validate()
        assert any("not in supported languages" in str(w) for w in warnings)

    def test_auto_fix_min_priority_range(self):
        """min_priority should be between 1 and 10."""
        # Too low
        config = Config()
        config.auto_fix.min_priority = 0
        errors, warnings = config.validate()
        assert any("min_priority must be between" in e for e in errors)

        # Too high
        config = Config()
        config.auto_fix.min_priority = 11
        errors, warnings = config.validate()
        assert any("min_priority must be between" in e for e in errors)

        # Valid values
        for priority in [1, 5, 10]:
            config = Config()
            config.auto_fix.min_priority = priority
            errors, warnings = config.validate()
            priority_errors = [e for e in errors if "min_priority" in e]
            assert len(priority_errors) == 0

    def test_invalid_report_format_warning(self):
        """Invalid report format should produce warning."""
        config = Config()
        config.reports.formats = ['json', 'unknown_format']
        errors, warnings = config.validate()
        assert any("Unknown report format" in str(w) for w in warnings)

    def test_valid_report_formats(self):
        """Valid report formats should pass."""
        config = Config()
        config.reports.formats = ['json', 'console', 'html', 'markdown']
        errors, warnings = config.validate()
        format_warnings = [w for w in warnings if "report format" in str(w)]
        assert len(format_warnings) == 0

    def test_l10n_empty_enum_name(self):
        """L10n enabled with empty enum_name should cause error."""
        config = Config()
        config.l10n.enabled = True
        config.l10n.enum_name = ""
        errors, warnings = config.validate()
        assert any("enum_name cannot be empty" in e for e in errors)

    def test_l10n_empty_default_module(self):
        """L10n enabled with empty default_module should cause error."""
        config = Config()
        config.l10n.enabled = True
        config.l10n.default_module = ""
        errors, warnings = config.validate()
        assert any("default_module cannot be empty" in e for e in errors)

    def test_l10n_disabled_ignores_validation(self):
        """L10n disabled should not validate enum_name/default_module."""
        config = Config()
        config.l10n.enabled = False
        config.l10n.enum_name = ""
        config.l10n.default_module = ""
        errors, warnings = config.validate()
        l10n_errors = [e for e in errors if "l10n" in e.lower()]
        assert len(l10n_errors) == 0

    def test_raise_on_error(self):
        """validate(raise_on_error=True) should raise exception."""
        config = Config()
        config.project.framework = "invalid"

        with pytest.raises(ConfigValidationError) as excinfo:
            config.validate(raise_on_error=True)

        assert len(excinfo.value.errors) > 0

    def test_source_path_warning(self):
        """Non-existent source path should produce warning."""
        config = Config()
        config.paths.source = "/non/existent/path/12345"
        errors, warnings = config.validate()
        assert any("Source path does not exist" in str(w) for w in warnings)


class TestLanguageCodeValidation:
    """Test cases for _is_valid_lang_code static method."""

    def test_iso_639_1_codes(self):
        """ISO 639-1 two-letter codes should be valid."""
        valid_codes = ['en', 'tr', 'de', 'fr', 'es', 'pt', 'it', 'ja', 'ko', 'zh']
        for code in valid_codes:
            assert Config._is_valid_lang_code(code) is True

    def test_locale_variants(self):
        """Locale variants like en-US should be valid."""
        valid_codes = ['en-US', 'en-GB', 'pt-BR', 'zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant']
        for code in valid_codes:
            assert Config._is_valid_lang_code(code) is True, f"'{code}' should be valid"

    def test_invalid_codes(self):
        """Invalid codes should return False."""
        invalid_codes = ['', 'e', 'eng', 'english', '12', 'en_US', 'en-', '-US']
        for code in invalid_codes:
            assert Config._is_valid_lang_code(code) is False, f"'{code}' should be invalid"

    def test_none_and_non_string(self):
        """None and non-string values should return False."""
        assert Config._is_valid_lang_code(None) is False
        assert Config._is_valid_lang_code(123) is False
        assert Config._is_valid_lang_code(['en']) is False


class TestConfigValidationWarning:
    """Test cases for ConfigValidationWarning class."""

    def test_warning_message(self):
        """Warning should store and display message."""
        warning = ConfigValidationWarning("Test warning message")
        assert warning.message == "Test warning message"
        assert str(warning) == "Test warning message"


class TestConfigValidationError:
    """Test cases for ConfigValidationError class."""

    def test_error_with_single_error(self):
        """Error should handle single error."""
        error = ConfigValidationError(["Single error"])
        assert len(error.errors) == 1
        assert "Single error" in str(error)

    def test_error_with_multiple_errors(self):
        """Error should handle multiple errors."""
        errors = ["Error 1", "Error 2", "Error 3"]
        error = ConfigValidationError(errors)
        assert len(error.errors) == 3
        assert "Error 1" in str(error)
        assert "Error 2" in str(error)


class TestConfigFromFile:
    """Test cases for loading and validating config from file."""

    def test_load_valid_config(self):
        """Valid config file should load without errors."""
        config_data = {
            'project': {
                'name': 'Test Project',
                'framework': 'swift'
            },
            'languages': {
                'primary': 'en',
                'supported': ['en', 'tr', 'de']
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            errors, warnings = config.validate()
            assert len(errors) == 0
            assert config.project.name == 'Test Project'
            assert config.languages.primary == 'en'
        finally:
            temp_path.unlink()

    def test_load_invalid_config(self):
        """Invalid config file should produce validation errors."""
        config_data = {
            'project': {
                'framework': 'invalid_framework'
            },
            'languages': {
                'primary': 'invalid_lang'
            },
            'auto_fix': {
                'min_priority': 15
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            errors, warnings = config.validate()
            assert len(errors) >= 2  # At least framework and language errors
        finally:
            temp_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
