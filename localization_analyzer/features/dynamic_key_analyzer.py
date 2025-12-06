r"""
Dynamic Key Analyzer - Enum-based localization key validation.

Bu modül dinamik key pattern'lerini analiz eder ve eksik key'leri tespit eder.

Örnek:
    "activity.\(id)".localized -> ActivityType enum'undaki tüm case'ler için
    "activity.work", "activity.friends" gibi key'ler olmalı.

Desteklenen pattern'ler:
    - Swift: "\(variable)", "\(self.property)", "\(rawValue)"
    - Kotlin: "${variable}", "${enum.name}"
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class DynamicKeyPattern:
    """Dinamik key pattern bilgisi."""
    pattern: str  # Örn: "activity.\(id)"
    prefix: str  # Örn: "activity."
    suffix: str  # Örn: "" veya ".description"
    variable_name: str  # Örn: "id", "rawValue"
    file_path: str  # Hangi dosyada kullanılıyor
    line_number: int


@dataclass
class EnumDefinition:
    """Swift/Kotlin enum tanımı."""
    name: str  # Örn: "ActivityType"
    cases: List[str]  # Örn: ["work", "friends", "family"]
    raw_values: Dict[str, str]  # case -> raw value mapping
    file_path: str


@dataclass
class DynamicKeyAnalysisResult:
    """Dinamik key analiz sonucu."""
    pattern: DynamicKeyPattern
    enum_name: Optional[str]  # Eşleşen enum adı
    expected_keys: List[str]  # Beklenen key'ler
    existing_keys: List[str]  # Mevcut key'ler
    missing_keys: List[str]  # Eksik key'ler


class DynamicKeyAnalyzer:
    """
    Dinamik key pattern'lerini analiz eder ve eksik key'leri tespit eder.

    Çalışma mantığı:
    1. Kaynak kodda dinamik key pattern'lerini bul
    2. Pattern'deki değişken adından enum tipini tahmin et
    3. Enum tanımını bul ve case'leri çıkar
    4. Her case için beklenen key'i oluştur
    5. .strings dosyasında var mı kontrol et
    """

    # Swift interpolation pattern'leri
    SWIFT_INTERPOLATION_PATTERNS = [
        # "\(variable)" - basit değişken
        r'"([^"]*)\\\((\w+)\)([^"]*)"\.localized',
        # "\(self.property)" - self property
        r'"([^"]*)\\\(self\.(\w+)\)([^"]*)"\.localized',
        # "\(variable.rawValue)" - enum raw value
        r'"([^"]*)\\\((\w+)\.rawValue\)([^"]*)"\.localized',
        # "\(Type.property)" - static property
        r'"([^"]*)\\\((\w+)\.(\w+)\)([^"]*)"\.localized',
        # .localized(from:) variant
        r'"([^"]*)\\\((\w+)\)([^"]*)"\.localized\(from:',
        r'"([^"]*)\\\(self\.(\w+)\)([^"]*)"\.localized\(from:',
        r'"([^"]*)\\\((\w+)\.rawValue\)([^"]*)"\.localized\(from:',
    ]

    # Enum case pattern (Swift)
    SWIFT_ENUM_PATTERN = r'enum\s+(\w+)\s*(?::\s*\w+)?\s*\{([^}]+)\}'
    SWIFT_CASE_PATTERN = r'case\s+(\w+)(?:\s*=\s*"([^"]+)")?'

    def __init__(self, source_dir: Path, existing_keys: Set[str]):
        """
        Args:
            source_dir: Kaynak kod dizini
            existing_keys: .strings dosyalarındaki mevcut key'ler
        """
        self.source_dir = source_dir
        self.existing_keys = existing_keys
        self.enums: Dict[str, EnumDefinition] = {}
        self.dynamic_patterns: List[DynamicKeyPattern] = []
        self.results: List[DynamicKeyAnalysisResult] = []

    def analyze(self) -> List[DynamicKeyAnalysisResult]:
        """
        Tam analiz çalıştır.

        Returns:
            Eksik key'leri içeren analiz sonuçları
        """
        # 1. Enum tanımlarını bul
        self._discover_enums()

        # 2. Dinamik key pattern'lerini bul
        self._discover_dynamic_patterns()

        # 3. Her pattern için eksik key'leri tespit et
        self._analyze_patterns()

        return self.results

    def _discover_enums(self):
        """Tüm Swift enum tanımlarını bul."""
        for swift_file in self.source_dir.rglob('*.swift'):
            # Exclude build directories
            if any(excluded in str(swift_file) for excluded in
                   ['build/', '.build/', 'DerivedData/', 'Pods/', '.git/']):
                continue

            try:
                content = swift_file.read_text(encoding='utf-8')
                self._extract_enums_from_content(content, str(swift_file))
            except Exception:
                continue

    def _extract_enums_from_content(self, content: str, file_path: str):
        """Dosya içeriğinden enum tanımlarını çıkar."""
        # Basit enum pattern - çok satırlı
        enum_pattern = re.compile(
            r'enum\s+(\w+)\s*(?::\s*[\w,\s]+)?\s*\{',
            re.MULTILINE
        )

        for match in enum_pattern.finditer(content):
            enum_name = match.group(1)
            start_pos = match.end()

            # Enum body'sini bul (brace matching)
            brace_count = 1
            end_pos = start_pos
            for i, char in enumerate(content[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break

            enum_body = content[start_pos:end_pos]

            # Case'leri çıkar
            cases = []
            raw_values = {}

            case_pattern = re.compile(r'case\s+(\w+)(?:\s*=\s*"([^"]+)")?')
            for case_match in case_pattern.finditer(enum_body):
                case_name = case_match.group(1)
                raw_value = case_match.group(2)  # Optional

                cases.append(case_name)
                if raw_value:
                    raw_values[case_name] = raw_value
                else:
                    # Raw value yoksa case adını kullan (camelCase -> lowercase)
                    raw_values[case_name] = self._camel_to_snake(case_name)

            if cases:
                self.enums[enum_name] = EnumDefinition(
                    name=enum_name,
                    cases=cases,
                    raw_values=raw_values,
                    file_path=file_path
                )

    def _camel_to_snake(self, name: str) -> str:
        """CamelCase'i snake_case'e çevir."""
        # Basit dönüşüm: büyük harflerden önce _ ekle
        result = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        return result

    def _discover_dynamic_patterns(self):
        """Dinamik key pattern'lerini bul."""
        for swift_file in self.source_dir.rglob('*.swift'):
            if any(excluded in str(swift_file) for excluded in
                   ['build/', '.build/', 'DerivedData/', 'Pods/', '.git/']):
                continue

            try:
                content = swift_file.read_text(encoding='utf-8')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    self._extract_dynamic_patterns_from_line(
                        line, str(swift_file), line_num
                    )
            except Exception:
                continue

    def _extract_dynamic_patterns_from_line(
        self, line: str, file_path: str, line_number: int
    ):
        """Satırdan dinamik pattern'leri çıkar."""
        # Pattern: "prefix.\(var)suffix".localized veya .localized(from:)
        # Örnek: "activity.\(id)".localized

        # Genel pattern - string interpolation içeren .localized kullanımları
        pattern = re.compile(
            r'"([^"\\]*(?:\\.[^"\\]*)*)"\.localized(?:\(from:\s*\.[a-zA-Z]+\))?'
        )

        for match in pattern.finditer(line):
            key_template = match.group(1)

            # İnterpolation içeriyor mu?
            interp_match = re.search(r'\\\(([^)]+)\)', key_template)
            if not interp_match:
                continue

            variable_expr = interp_match.group(1)  # Örn: "id", "self.type", "type.rawValue"

            # Değişken adını çıkar
            if '.' in variable_expr:
                parts = variable_expr.split('.')
                if parts[-1] == 'rawValue':
                    variable_name = parts[-2] if len(parts) > 1 else parts[0]
                else:
                    variable_name = parts[-1]
            else:
                variable_name = variable_expr

            # Prefix ve suffix'i çıkar
            prefix = key_template[:interp_match.start()]
            suffix = key_template[interp_match.end():]

            # Escape karakterlerini temizle
            prefix = prefix.replace('\\', '')
            suffix = suffix.replace('\\', '')

            self.dynamic_patterns.append(DynamicKeyPattern(
                pattern=key_template,
                prefix=prefix,
                suffix=suffix,
                variable_name=variable_name,
                file_path=file_path,
                line_number=line_number
            ))

    def _analyze_patterns(self):
        """Her pattern için key'leri analiz et.

        Not: Tüm sonuçlar eklenir (missing olsun olmasın) çünkü
        dead key tespiti için expected_keys bilgisi gereklidir.
        """
        for pattern in self.dynamic_patterns:
            result = self._analyze_single_pattern(pattern)
            if result:
                self.results.append(result)

    def _analyze_single_pattern(
        self, pattern: DynamicKeyPattern
    ) -> Optional[DynamicKeyAnalysisResult]:
        """Tek bir pattern'i analiz et."""
        # Değişken adından olası enum'ları bul
        possible_enums = self._find_possible_enums(pattern)

        if not possible_enums:
            # Enum bulunamadı, mevcut key'lerden tahmin et
            return self._analyze_from_existing_keys(pattern)

        # En uygun enum'u seç (en fazla eşleşen)
        best_enum = None
        best_match_count = 0

        for enum in possible_enums:
            expected_keys = self._generate_expected_keys(pattern, enum)
            existing = [k for k in expected_keys if k in self.existing_keys]
            if len(existing) > best_match_count:
                best_match_count = len(existing)
                best_enum = enum

        if not best_enum:
            best_enum = possible_enums[0]

        expected_keys = self._generate_expected_keys(pattern, best_enum)
        existing_keys = [k for k in expected_keys if k in self.existing_keys]
        missing_keys = [k for k in expected_keys if k not in self.existing_keys]

        return DynamicKeyAnalysisResult(
            pattern=pattern,
            enum_name=best_enum.name,
            expected_keys=expected_keys,
            existing_keys=existing_keys,
            missing_keys=missing_keys
        )

    def _find_possible_enums(self, pattern: DynamicKeyPattern) -> List[EnumDefinition]:
        """Pattern'e uygun olabilecek enum'ları bul."""
        possible = []
        var_name = pattern.variable_name.lower()

        for enum_name, enum_def in self.enums.items():
            enum_lower = enum_name.lower()

            # Değişken adı enum adını içeriyor mu?
            # Örn: activityType -> ActivityType, type -> Type
            if var_name in enum_lower or enum_lower.endswith(var_name):
                possible.append(enum_def)

            # Prefix enum adını içeriyor mu?
            # Örn: "activity." prefix'i için ActivityType
            prefix_lower = pattern.prefix.rstrip('.').lower()
            if prefix_lower in enum_lower or enum_lower.startswith(prefix_lower):
                if enum_def not in possible:
                    possible.append(enum_def)

        return possible

    def _generate_expected_keys(
        self, pattern: DynamicKeyPattern, enum: EnumDefinition
    ) -> List[str]:
        """Enum case'lerine göre beklenen key'leri oluştur."""
        expected = []

        for case_name in enum.cases:
            # Raw value varsa onu kullan, yoksa case adını
            value = enum.raw_values.get(case_name, case_name.lower())
            key = f"{pattern.prefix}{value}{pattern.suffix}"
            expected.append(key)

        return expected

    def _analyze_from_existing_keys(
        self, pattern: DynamicKeyPattern
    ) -> Optional[DynamicKeyAnalysisResult]:
        """
        Enum bulunamadığında mevcut key'lerden analiz yap.

        Mevcut key'lerdeki pattern'e bakarak eksikleri tahmin et.
        """
        # Prefix ile başlayan ve suffix ile biten key'leri bul
        matching_keys = []

        for key in self.existing_keys:
            if pattern.prefix and pattern.suffix:
                if key.startswith(pattern.prefix) and key.endswith(pattern.suffix):
                    matching_keys.append(key)
            elif pattern.prefix:
                if key.startswith(pattern.prefix) and '.' not in key[len(pattern.prefix):]:
                    matching_keys.append(key)

        # Eşleşen key yoksa analiz yapamayız
        if not matching_keys:
            return None

        # Bu durumda eksik key yok (mevcut key'ler zaten var)
        return DynamicKeyAnalysisResult(
            pattern=pattern,
            enum_name=None,
            expected_keys=matching_keys,
            existing_keys=matching_keys,
            missing_keys=[]
        )

    def get_summary(self) -> Dict:
        """Özet rapor döndür."""
        total_patterns = len(self.dynamic_patterns)
        patterns_with_missing = len(self.results)
        total_missing = sum(len(r.missing_keys) for r in self.results)

        return {
            'total_dynamic_patterns': total_patterns,
            'patterns_with_missing_keys': patterns_with_missing,
            'total_missing_keys': total_missing,
            'enums_discovered': len(self.enums),
            'details': [
                {
                    'pattern': r.pattern.pattern,
                    'file': r.pattern.file_path,
                    'line': r.pattern.line_number,
                    'enum': r.enum_name,
                    'missing_keys': r.missing_keys,
                    'existing_keys': r.existing_keys,
                }
                for r in self.results
            ]
        }
