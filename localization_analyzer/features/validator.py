"""Localization file validator."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ..utils.colors import Colors


@dataclass
class ValidationIssue:
    """Doğrulama sorunu."""
    severity: str  # error, warning, info
    code: str  # E001, W001, I001
    message: str
    file: str
    line: Optional[int] = None
    key: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Doğrulama sonucu."""
    is_valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings) + len(self.info)

    def add_issue(self, issue: ValidationIssue):
        """Sorun ekle."""
        if issue.severity == 'error':
            self.errors.append(issue)
            self.is_valid = False
        elif issue.severity == 'warning':
            self.warnings.append(issue)
        else:
            self.info.append(issue)


class LocalizationValidator:
    """
    Localization dosyası doğrulayıcısı.

    Kontroller:
    - Syntax doğruluğu (geçersiz karakterler, eksik tırnak)
    - Key tutarlılığı (tüm dillerde aynı key'ler)
    - Placeholder tutarlılığı (%@, %d sayısı aynı mı)
    - Boş değerler
    - Duplicate key'ler
    - Escape karakterleri
    """

    # Hata kodları
    ERROR_CODES = {
        'E001': 'Invalid syntax',
        'E002': 'Unclosed quote',
        'E003': 'Missing semicolon',
        'E004': 'Invalid escape sequence',
        'E005': 'Duplicate key',
        'W001': 'Missing key in language',
        'W002': 'Placeholder count mismatch',
        'W003': 'Empty value',
        'W004': 'Untranslated (same as source)',
        'I001': 'Extra key not in source',
        'I002': 'TODO comment found',
    }

    def __init__(self, source_lang: str = 'en'):
        """
        Validator'ı başlat.

        Args:
            source_lang: Kaynak dil (karşılaştırma için)
        """
        self.source_lang = source_lang
        self.results: Dict[str, ValidationResult] = {}

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Tek bir .strings dosyasını doğrula.

        Args:
            file_path: .strings dosya yolu

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not file_path.exists():
            result.add_issue(ValidationIssue(
                severity='error',
                code='E000',
                message=f'File not found: {file_path}',
                file=str(file_path)
            ))
            return result

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='E000',
                message=f'Cannot read file: {e}',
                file=str(file_path)
            ))
            return result

        file_str = str(file_path)
        seen_keys = set()

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('/*') or stripped.startswith('//') or stripped.startswith('*'):
                # Check for TODO comments
                if 'TODO' in stripped.upper():
                    result.add_issue(ValidationIssue(
                        severity='info',
                        code='I002',
                        message='TODO comment found',
                        file=file_str,
                        line=line_num
                    ))
                continue

            # Skip closing comment
            if stripped == '*/':
                continue

            # Parse key-value line
            match = re.match(r'^"([^"]+)"\s*=\s*"(.*)";?\s*$', stripped)

            if not match and '=' in stripped and '"' in stripped:
                # Syntax error - malformed line
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='E001',
                    message='Invalid syntax',
                    file=file_str,
                    line=line_num,
                    suggestion='Format should be: "key" = "value";'
                ))
                continue

            if not match:
                continue

            key, value = match.groups()

            # Check for duplicate keys
            if key in seen_keys:
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='E005',
                    message=f'Duplicate key: {key}',
                    file=file_str,
                    line=line_num,
                    key=key
                ))
            seen_keys.add(key)

            # Check for empty value
            if not value.strip():
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='W003',
                    message='Empty value',
                    file=file_str,
                    line=line_num,
                    key=key
                ))

            # Check for missing semicolon
            if not stripped.endswith(';'):
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='E003',
                    message='Missing semicolon',
                    file=file_str,
                    line=line_num,
                    key=key
                ))

            # Check for invalid escape sequences
            invalid_escapes = re.findall(r'\\[^nrt"\\]', value)
            if invalid_escapes:
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='E004',
                    message=f'Invalid escape sequence: {invalid_escapes[0]}',
                    file=file_str,
                    line=line_num,
                    key=key,
                    suggestion='Valid escapes: \\n, \\r, \\t, \\", \\\\'
                ))

        return result

    def validate_consistency(
        self,
        files: Dict[str, Path],
        source_keys: Dict[str, str]
    ) -> Dict[str, ValidationResult]:
        """
        Diller arası tutarlılığı kontrol et.

        Args:
            files: {lang_code: file_path} sözlüğü
            source_keys: {key: value} kaynak dil key'leri

        Returns:
            {lang_code: ValidationResult} sözlüğü
        """
        results = {}

        for lang_code, file_path in files.items():
            result = ValidationResult()
            file_str = str(file_path)

            # Parse this file's keys
            lang_keys = self._parse_keys(file_path)

            # Check for missing keys
            for key in source_keys:
                if key not in lang_keys:
                    result.add_issue(ValidationIssue(
                        severity='warning',
                        code='W001',
                        message=f'Missing key from {self.source_lang}',
                        file=file_str,
                        key=key
                    ))

            # Check for extra keys
            for key in lang_keys:
                if key not in source_keys:
                    result.add_issue(ValidationIssue(
                        severity='info',
                        code='I001',
                        message=f'Extra key not in {self.source_lang}',
                        file=file_str,
                        key=key
                    ))

            # Check placeholder consistency
            for key, source_value in source_keys.items():
                if key in lang_keys:
                    target_value = lang_keys[key]

                    # Count placeholders
                    source_placeholders = self._count_placeholders(source_value)
                    target_placeholders = self._count_placeholders(target_value)

                    if source_placeholders != target_placeholders:
                        result.add_issue(ValidationIssue(
                            severity='warning',
                            code='W002',
                            message=f'Placeholder count mismatch: {source_placeholders} vs {target_placeholders}',
                            file=file_str,
                            key=key,
                            suggestion=f'Source has {source_placeholders} placeholders'
                        ))

                    # Check for untranslated (same as source)
                    if lang_code != self.source_lang and target_value == source_value:
                        # Only warn for non-technical strings
                        if len(source_value) > 3 and not source_value.startswith('%'):
                            result.add_issue(ValidationIssue(
                                severity='warning',
                                code='W004',
                                message='Untranslated (same as source)',
                                file=file_str,
                                key=key
                            ))

            results[lang_code] = result

        return results

    def _parse_keys(self, file_path: Path) -> Dict[str, str]:
        """Dosyadan key-value çiftlerini parse et."""
        keys = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            pattern = r'"([^"]+)"\s*=\s*"((?:[^"\\]|\\.)*)";'
            matches = re.finditer(pattern, content)

            for match in matches:
                key, value = match.groups()
                keys[key] = value

        except (IOError, OSError, UnicodeDecodeError) as e:
            # File read errors - return empty dict
            print(f"  Warning: Could not parse {file_path.name}: {e}")

        return keys

    def _count_placeholders(self, text: str) -> Dict[str, int]:
        """Placeholder sayılarını say."""
        counts = {
            '%@': len(re.findall(r'%@', text)),
            '%d': len(re.findall(r'%l?l?d', text)),
            '%f': len(re.findall(r'%\.?\d*f', text)),
            '%s': len(re.findall(r'%s', text)),
            'interpolation': len(re.findall(r'\\\([^)]+\)', text)),
        }
        return counts

    def print_results(self, results: Dict[str, ValidationResult]):
        """Sonuçları yazdır."""
        total_errors = 0
        total_warnings = 0
        total_info = 0

        for lang, result in results.items():
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            total_info += len(result.info)

            if result.total_issues == 0:
                print(f"  {Colors.success('✓')} {lang}: No issues")
                continue

            print(f"\n  {Colors.bold(lang)}:")

            for issue in result.errors:
                print(f"    {Colors.error('✗')} [{issue.code}] {issue.message}")
                if issue.key:
                    print(f"      Key: {issue.key}")
                if issue.line:
                    print(f"      Line: {issue.line}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")

            for issue in result.warnings:
                print(f"    {Colors.warning('⚠')} [{issue.code}] {issue.message}")
                if issue.key:
                    print(f"      Key: {issue.key}")

            for issue in result.info[:5]:  # Limit info messages
                print(f"    {Colors.info('ℹ')} [{issue.code}] {issue.message}")
                if issue.key:
                    print(f"      Key: {issue.key}")

            if len(result.info) > 5:
                print(f"    ... and {len(result.info) - 5} more info messages")

        # Summary
        print(f"\n{'=' * 50}")
        print(f"  Errors: {total_errors}")
        print(f"  Warnings: {total_warnings}")
        print(f"  Info: {total_info}")

        if total_errors > 0:
            print(f"\n  {Colors.error('❌ Validation FAILED')}")
            return False
        elif total_warnings > 0:
            print(f"\n  {Colors.warning('⚠️  Validation passed with warnings')}")
            return True
        else:
            print(f"\n  {Colors.success('✅ Validation PASSED')}")
            return True
