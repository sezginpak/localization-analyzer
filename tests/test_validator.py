"""Tests for the validator module."""

import pytest
from pathlib import Path
import tempfile

from localization_analyzer.features.validator import (
    LocalizationValidator,
    ValidationResult,
    ValidationIssue
)


class TestValidationResult:
    """Test cases for ValidationResult."""

    def test_default_valid(self):
        """Test default state is valid."""
        result = ValidationResult()
        assert result.is_valid
        assert result.total_issues == 0

    def test_add_error_makes_invalid(self):
        """Test adding error makes result invalid."""
        result = ValidationResult()
        result.add_issue(ValidationIssue(
            severity='error',
            code='E001',
            message='Test error',
            file='test.strings'
        ))
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_add_warning_stays_valid(self):
        """Test adding warning keeps result valid."""
        result = ValidationResult()
        result.add_issue(ValidationIssue(
            severity='warning',
            code='W001',
            message='Test warning',
            file='test.strings'
        ))
        assert result.is_valid
        assert len(result.warnings) == 1

    def test_total_issues(self):
        """Test total issues count."""
        result = ValidationResult()
        result.add_issue(ValidationIssue(severity='error', code='E001', message='', file=''))
        result.add_issue(ValidationIssue(severity='warning', code='W001', message='', file=''))
        result.add_issue(ValidationIssue(severity='info', code='I001', message='', file=''))

        assert result.total_issues == 3


class TestLocalizationValidator:
    """Test cases for LocalizationValidator."""

    def test_init(self):
        """Test initialization."""
        validator = LocalizationValidator()
        assert validator.source_lang == 'en'

        validator2 = LocalizationValidator(source_lang='tr')
        assert validator2.source_lang == 'tr'

    def test_validate_valid_file(self):
        """Test validating a valid .strings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('''
/* Comment */
"key1" = "value1";
"key2" = "value2";
''')

            validator = LocalizationValidator()
            result = validator.validate_file(file_path)

            assert result.is_valid
            assert len(result.errors) == 0

    def test_validate_missing_semicolon(self):
        """Test detecting missing semicolon."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('"key" = "value"')

            validator = LocalizationValidator()
            result = validator.validate_file(file_path)

            assert any(e.code == 'E003' for e in result.errors)

    def test_validate_duplicate_key(self):
        """Test detecting duplicate keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('''
"key" = "value1";
"key" = "value2";
''')

            validator = LocalizationValidator()
            result = validator.validate_file(file_path)

            assert any(e.code == 'E005' for e in result.errors)

    def test_validate_empty_value(self):
        """Test detecting empty values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('"key" = "";')

            validator = LocalizationValidator()
            result = validator.validate_file(file_path)

            assert any(w.code == 'W003' for w in result.warnings)

    def test_validate_todo_comment(self):
        """Test detecting TODO comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.strings'
            file_path.write_text('''
/* TODO: translate this */
"key" = "value";
''')

            validator = LocalizationValidator()
            result = validator.validate_file(file_path)

            assert any(i.code == 'I002' for i in result.info)

    def test_validate_nonexistent_file(self):
        """Test validating non-existent file."""
        validator = LocalizationValidator()
        result = validator.validate_file(Path('/nonexistent/file.strings'))

        assert not result.is_valid
        assert len(result.errors) == 1

    def test_count_placeholders(self):
        """Test placeholder counting."""
        validator = LocalizationValidator()

        counts = validator._count_placeholders("Hello %@, you have %d items")
        assert counts['%@'] == 1
        assert counts['%d'] == 1

        counts2 = validator._count_placeholders(r"Hello \(name)")
        assert counts2['interpolation'] == 1

    def test_consistency_missing_key(self):
        """Test detecting missing keys across languages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en_file = Path(tmpdir) / 'en.strings'
            tr_file = Path(tmpdir) / 'tr.strings'

            en_file.write_text('"key1" = "value1";\n"key2" = "value2";')
            tr_file.write_text('"key1" = "değer1";')

            validator = LocalizationValidator(source_lang='en')

            source_keys = {'key1': 'value1', 'key2': 'value2'}
            files = {'en': en_file, 'tr': tr_file}

            results = validator.validate_consistency(files, source_keys)

            # Turkish should have missing key warning
            assert any(w.code == 'W001' for w in results['tr'].warnings)

    def test_consistency_placeholder_mismatch(self):
        """Test detecting placeholder count mismatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en_file = Path(tmpdir) / 'en.strings'
            tr_file = Path(tmpdir) / 'tr.strings'

            en_file.write_text('"greeting" = "Hello %@";')
            tr_file.write_text('"greeting" = "Merhaba";')  # Missing %@

            validator = LocalizationValidator(source_lang='en')

            source_keys = {'greeting': 'Hello %@'}
            files = {'en': en_file, 'tr': tr_file}

            results = validator.validate_consistency(files, source_keys)

            # Should detect placeholder mismatch
            assert any(w.code == 'W002' for w in results['tr'].warnings)


class TestValidatorIntegration:
    """Integration tests for validator."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            en_dir = Path(tmpdir) / 'en.lproj'
            tr_dir = Path(tmpdir) / 'tr.lproj'
            en_dir.mkdir()
            tr_dir.mkdir()

            en_file = en_dir / 'Localizable.strings'
            tr_file = tr_dir / 'Localizable.strings'

            en_file.write_text('''
/* English strings */
"hello" = "Hello";
"goodbye" = "Goodbye";
"items_count" = "You have %d items";
''')

            tr_file.write_text('''
/* Turkish strings */
"hello" = "Merhaba";
"items_count" = "You have %d items";
''')

            validator = LocalizationValidator(source_lang='en')

            # Validate each file
            en_result = validator.validate_file(en_file)
            tr_result = validator.validate_file(tr_file)

            assert en_result.is_valid
            assert tr_result.is_valid

            # Check consistency
            source_keys = {
                'hello': 'Hello',
                'goodbye': 'Goodbye',
                'items_count': 'You have %d items'
            }

            results = validator.validate_consistency(
                {'en': en_file, 'tr': tr_file},
                source_keys
            )

            # Turkish should have missing 'goodbye' warning
            tr_warnings = [w for w in results['tr'].warnings if w.code == 'W001']
            assert len(tr_warnings) == 1
            assert tr_warnings[0].key == 'goodbye'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
