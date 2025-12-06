"""Main localization analyzer."""

import re
from pathlib import Path
from typing import List, Set, Dict, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from ..frameworks.base import BaseAdapter, HardcodedString, LocalizedUsage
from ..utils.colors import Colors
from ..utils.validators import is_excluded_string
from .file_manager import LocalizationFileManager
from .health_calculator import HealthCalculator, HealthScore

# Dinamik key pattern'lerini tespit etmek için regex
DYNAMIC_KEY_PATTERNS = [
    r'\\\(',          # Swift string interpolation: \(variable)
    r'\$\{',          # JavaScript/Kotlin template: ${variable}
    r'\$\(',          # Shell-style: $(variable)
    r'\{[0-9]+\}',    # Positional placeholders: {0}, {1}
    r'\{\w+\}',       # Named placeholders: {name}, {id}
    r'%[@dsfg]',      # Format specifiers: %@, %d, %s, %f, %g
]


@dataclass
class AnalysisResult:
    """Result of localization analysis."""
    health: HealthScore
    hardcoded_strings: List[HardcodedString] = field(default_factory=list)
    localized_usages: List[LocalizedUsage] = field(default_factory=list)
    used_keys: Set[str] = field(default_factory=set)
    dead_keys: Set[str] = field(default_factory=set)
    missing_keys: Dict[str, List[str]] = field(default_factory=dict)  # key -> [files using it]
    dynamic_keys: Dict[str, List[str]] = field(default_factory=dict)  # Dinamik key'ler (bilgi amaçlı)
    missing_dynamic_keys: Dict[str, Dict] = field(default_factory=dict)  # Enum-based eksik key'ler
    duplicates: Dict[str, List[HardcodedString]] = field(default_factory=dict)
    component_stats: Dict[str, Dict] = field(default_factory=dict)
    file_stats: Dict[str, Dict] = field(default_factory=dict)
    folder_stats: Dict[str, Dict] = field(default_factory=dict)


class LocalizationAnalyzer:
    """
    Main localization analyzer for any framework.

    Features:
    - Framework-agnostic design
    - Multi-language support
    - Dead key detection
    - Missing key detection
    - Duplicate string detection
    - Health score calculation
    - Multi-threaded analysis
    """

    def __init__(
        self,
        project_dir: Path,
        adapter: BaseAdapter,
        localization_dir: Optional[Path] = None,
        use_threads: bool = True,
    ):
        """
        Initialize analyzer.

        Args:
            project_dir: Project root directory
            adapter: Framework adapter (e.g., SwiftAdapter)
            localization_dir: Directory containing localization files
            use_threads: Enable multi-threaded analysis
        """
        self.project_dir = Path(project_dir)
        self.adapter = adapter
        self.use_threads = use_threads

        # File manager
        if localization_dir is None:
            localization_dir = self.project_dir
        self.file_manager = LocalizationFileManager(adapter, localization_dir)

        # Analysis data
        self.source_files: List[Path] = []
        self.hardcoded_strings: List[HardcodedString] = []
        self.localized_usages: List[LocalizedUsage] = []
        self.used_keys: Set[str] = set()
        self.dead_keys: Set[str] = set()
        self.missing_keys: Dict[str, List[str]] = defaultdict(list)
        self.dynamic_keys: Dict[str, List[str]] = defaultdict(list)  # Dinamik key'ler
        self.duplicates: Dict[str, List[HardcodedString]] = defaultdict(list)

        # Statistics
        self.component_stats = defaultdict(lambda: {'total': 0, 'localized': 0, 'hardcoded': 0})
        self.file_stats = defaultdict(lambda: {'total': 0, 'localized': 0, 'hardcoded': 0})
        self.folder_stats = defaultdict(lambda: {'total': 0, 'localized': 0, 'hardcoded': 0})

        # Thread-safety için lock (multi-threaded analiz sırasında shared state koruma)
        self._lock = Lock()

    def analyze(self, verbose: bool = True) -> AnalysisResult:
        """
        Run complete analysis.

        Args:
            verbose: Print progress messages

        Returns:
            AnalysisResult object
        """
        if verbose:
            print("=" * 70)
            print(f"{Colors.bold('🚀 Localization Analyzer')}")
            print("=" * 70)

        # Load localization keys
        self.file_manager.load_all_keys()

        # Find source files
        self._find_source_files(verbose)

        # Analyze files
        self._analyze_all_files(verbose)

        # Analyze dynamic key patterns for missing enum-based keys
        # (Bu önce yapılmalı ki dinamik key'ler dead key hesabından çıkarılabilsin)
        missing_dynamic_keys, all_dynamic_keys = self._analyze_dynamic_key_patterns(verbose)

        # Find dead keys (dinamik key'leri hariç tut)
        self._find_dead_keys(verbose, all_dynamic_keys)

        # Analyze duplicates
        self._analyze_duplicates(verbose)

        # Calculate health score
        health = HealthCalculator.calculate(
            localized_count=len(self.localized_usages),
            hardcoded_count=len(self.hardcoded_strings),
            missing_keys=list(self.missing_keys.keys()),
            dead_keys=list(self.dead_keys),
            duplicates=self.duplicates,
        )

        if verbose:
            self._print_summary(health)

        return AnalysisResult(
            health=health,
            hardcoded_strings=self.hardcoded_strings,
            localized_usages=self.localized_usages,
            used_keys=self.used_keys,
            dead_keys=self.dead_keys,
            missing_keys=dict(self.missing_keys),
            dynamic_keys=dict(self.dynamic_keys),
            missing_dynamic_keys=missing_dynamic_keys,
            duplicates=dict(self.duplicates),
            component_stats=dict(self.component_stats),
            file_stats=dict(self.file_stats),
            folder_stats=dict(self.folder_stats),
        )

    def _is_dynamic_key(self, key: str) -> bool:
        r"""
        Key'in dinamik (runtime'da oluşturulan) olup olmadığını kontrol et.

        Dinamik key'ler interpolation içerir ve gerçek missing key değildir.
        Örnek: "activity.\(id)" -> dinamik, "activity.work" -> statik
        """
        for pattern in DYNAMIC_KEY_PATTERNS:
            if re.search(pattern, key):
                return True
        return False

    def _has_base_pattern_keys(self, key: str) -> bool:
        r"""
        Dinamik bir key için base pattern'e sahip statik key'lerin var olup olmadığını kontrol et.

        Örnek: "activity.\(id)" için "activity.work", "activity.friends" gibi
        key'ler varsa, bu dinamik key eksik değildir.

        Ayrıca ortada interpolation olan pattern'leri de destekler:
        Örnek: "style.\(rawValue).description" için "style.friendly.description" gibi
        key'ler varsa, bu dinamik key eksik değildir.
        """
        # Key'den interpolation pattern'lerini çıkar
        interpolation_patterns = [
            r'\\\([^)]*\)',      # Swift: \(...)
            r'\$\{[^}]*\}',      # JS/Kotlin: ${...}
            r'\$\([^)]*\)',      # Shell: $(...)
            r'\{[^}]*\}',        # Generic: {...}
        ]

        # Interpolation'ları placeholder ile değiştir
        normalized_key = key
        for pattern in interpolation_patterns:
            normalized_key = re.sub(pattern, '*', normalized_key)

        # Eğer key değişmediyse interpolation yok
        if normalized_key == key:
            return False

        # Pattern parçalarını ayır (örn: "style.*.description" -> ["style", "*", "description"])
        parts = normalized_key.split('.')

        # Eğer sadece tek parça varsa (örn: "activity.*" -> "activity." prefix'i)
        if len(parts) == 2 and parts[1] == '*':
            prefix = parts[0] + '.'
            for existing_key in self.file_manager.keys:
                if existing_key.startswith(prefix) and existing_key != key:
                    return True
            return False

        # Birden fazla parça varsa (örn: "style.*.description")
        # Regex oluştur: "style.*.description" -> "^style\.[^.]+\.description$"
        regex_parts = []
        for part in parts:
            if part == '*':
                regex_parts.append('[^.]+')  # Bir segment (nokta içermeyen)
            else:
                regex_parts.append(re.escape(part))

        regex_pattern = '^' + r'\.'.join(regex_parts) + '$'

        try:
            compiled_pattern = re.compile(regex_pattern)
            for existing_key in self.file_manager.keys:
                if compiled_pattern.match(existing_key) and existing_key != key:
                    return True
        except re.error:
            # Invalid regex pattern derived from key - treat as no match
            pass

        return False

    def _find_source_files(self, verbose: bool = True):
        """Find all source files to analyze."""
        if verbose:
            print(f"\n🔍 Finding source files...")

        extensions = self.adapter.get_file_extensions()

        for ext in extensions:
            for file_path in self.project_dir.rglob(f'*{ext}'):
                if self.adapter.should_exclude_file(file_path):
                    continue
                self.source_files.append(file_path)

        if verbose:
            print(f"   {Colors.success('✓')} Found {len(self.source_files)} files")

    def _analyze_all_files(self, verbose: bool = True):
        """Analyze all source files."""
        if verbose:
            print(f"\n📊 Analyzing {len(self.source_files)} files...")

        if self.use_threads and len(self.source_files) > 20:
            # Multi-threaded
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(self._analyze_file, f) for f in self.source_files]
                for i, future in enumerate(as_completed(futures), 1):
                    if verbose and i % 50 == 0:
                        print(f"   {i}/{len(self.source_files)} processed...")
        else:
            # Single-threaded
            for i, file_path in enumerate(self.source_files, 1):
                if verbose and i % 50 == 0:
                    print(f"   {i}/{len(self.source_files)} processed...")
                self._analyze_file(file_path)

        if verbose:
            print(f"   {Colors.success('✓')} Analysis complete")

    def _analyze_file(self, file_path: Path):
        """Analyze a single file (thread-safe)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError, UnicodeDecodeError) as e:
            # Silently skip files that can't be read (binary files, permission issues)
            return

        relative_path = file_path.relative_to(self.project_dir)
        folder = str(relative_path.parent)

        # Thread-local sonuçları topla
        local_used_keys: Set[str] = set()
        local_localized_usages: List[LocalizedUsage] = []
        local_dynamic_keys: Dict[str, List[str]] = defaultdict(list)
        local_missing_keys: Dict[str, List[str]] = defaultdict(list)
        local_component_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'localized': 0, 'hardcoded': 0})
        local_file_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'localized': 0, 'hardcoded': 0})
        local_folder_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'localized': 0, 'hardcoded': 0})
        local_hardcoded_strings: List[HardcodedString] = []
        local_duplicates: Dict[str, List[HardcodedString]] = defaultdict(list)

        # Find localized usages
        for pattern in self.adapter.localized_patterns:
            for match in re.finditer(pattern.pattern, content):
                key = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                local_used_keys.add(key)
                local_localized_usages.append(LocalizedUsage(
                    file=str(relative_path),
                    line=line_num,
                    key=key,
                    component=pattern.component_type,
                ))

                local_component_stats[pattern.component_type]['localized'] += 1
                local_file_stats[str(relative_path)]['localized'] += 1
                local_folder_stats[folder]['localized'] += 1

                # Check if key exists (skip dynamic keys with valid base patterns)
                if not self.file_manager.key_exists(key):
                    # Dinamik key mi kontrol et
                    if self._is_dynamic_key(key):
                        # Dinamik key'i ayrı kategoride takip et (bilgi amaçlı)
                        local_dynamic_keys[key].append(str(relative_path))
                        # Base pattern'e sahip key'ler var mı?
                        if self._has_base_pattern_keys(key):
                            # Dinamik key, base pattern mevcut - eksik değil
                            continue
                    # Gerçekten eksik key
                    local_missing_keys[key].append(str(relative_path))

        # Find hardcoded strings
        for pattern in self.adapter.hardcoded_patterns:
            for match in re.finditer(pattern.pattern, content):
                text = match.group(1)

                # Check if string should be excluded from localization
                if hasattr(self.adapter, 'should_exclude_string') and self.adapter.should_exclude_string(text):
                    continue

                line_num = content[:match.start()].count('\n') + 1

                # Skip if wrapped in localization
                context_start = max(0, match.start() - 50)
                context = content[context_start:match.end()]
                if 'String(localized:' in context or 'NSLocalizedString' in context:
                    continue

                priority = self.adapter.calculate_priority(
                    pattern.component_type,
                    pattern.category,
                    text
                )
                suggested_key = self.adapter.suggest_key_name(text, pattern.component_type)

                hardcoded = HardcodedString(
                    file=str(relative_path),
                    line=line_num,
                    text=text,
                    component=pattern.component_type,
                    category=pattern.category,
                    priority=priority,
                    suggested_key=suggested_key,
                )

                local_hardcoded_strings.append(hardcoded)
                local_duplicates[text].append(hardcoded)

                local_component_stats[pattern.component_type]['hardcoded'] += 1
                local_file_stats[str(relative_path)]['hardcoded'] += 1
                local_folder_stats[folder]['hardcoded'] += 1

        # Thread-safe: Lock ile shared state'e yaz
        with self._lock:
            self.used_keys.update(local_used_keys)
            self.localized_usages.extend(local_localized_usages)
            self.hardcoded_strings.extend(local_hardcoded_strings)

            for key, files in local_dynamic_keys.items():
                self.dynamic_keys[key].extend(files)

            for key, files in local_missing_keys.items():
                self.missing_keys[key].extend(files)

            for text, locations in local_duplicates.items():
                self.duplicates[text].extend(locations)

            for comp, stats in local_component_stats.items():
                self.component_stats[comp]['localized'] += stats['localized']
                self.component_stats[comp]['hardcoded'] += stats['hardcoded']

            for f, stats in local_file_stats.items():
                self.file_stats[f]['localized'] += stats['localized']
                self.file_stats[f]['hardcoded'] += stats['hardcoded']

            for folder_name, stats in local_folder_stats.items():
                self.folder_stats[folder_name]['localized'] += stats['localized']
                self.folder_stats[folder_name]['hardcoded'] += stats['hardcoded']

    def _find_dead_keys(
        self, verbose: bool = True, dynamically_used_keys: set = None
    ):
        """Find keys that exist but are not used.

        Args:
            verbose: Detaylı çıktı göster
            dynamically_used_keys: Dinamik olarak kullanılan key'ler - dead sayılmaz
        """
        if verbose:
            print(f"\n🔎 Finding dead keys...")

        all_keys = set(self.file_manager.keys.keys())

        # Dinamik key'ler yoksa boş set kullan
        if dynamically_used_keys is None:
            dynamically_used_keys = set()

        # Dead keys = Tüm key'ler - Kullanılanlar - Dinamik kullanılanlar
        self.dead_keys = all_keys - self.used_keys - dynamically_used_keys

        if verbose:
            if dynamically_used_keys:
                print(f"   {Colors.info('ℹ')} {len(dynamically_used_keys)} keys excluded "
                      f"(used dynamically)")
            print(f"   {Colors.success('✓')} Found {len(self.dead_keys)} dead keys")

    def _analyze_duplicates(self, verbose: bool = True):
        """Find duplicate hardcoded strings."""
        if verbose:
            print(f"\n🔍 Analyzing duplicates...")

        self.duplicates = {
            text: locations
            for text, locations in self.duplicates.items()
            if len(locations) >= 2
        }

        if verbose:
            print(f"   {Colors.success('✓')} Found {len(self.duplicates)} duplicate strings")

    def _analyze_dynamic_key_patterns(
        self, verbose: bool = True
    ) -> tuple[Dict[str, Dict], set]:
        r"""
        Dinamik key pattern'lerini analiz et ve enum-based eksik key'leri bul.

        Bu metod:
        1. Swift enum tanımlarını keşfeder
        2. "prefix.\(variable)".localized pattern'lerini bulur
        3. Her pattern için enum case'lerine göre beklenen key'leri hesaplar
        4. .strings dosyasında eksik olan key'leri raporlar

        Returns:
            tuple: (
                Dict: {pattern -> {enum, expected_keys, existing_keys, missing_keys}},
                set: Tüm dinamik olarak kullanılan key'ler (dead key hesabı için)
            )
        """
        if verbose:
            print(f"\n🔄 Analyzing dynamic key patterns...")

        try:
            from ..features.dynamic_key_analyzer import DynamicKeyAnalyzer

            # Mevcut key'leri al
            existing_keys = set(self.file_manager.keys.keys())

            # DynamicKeyAnalyzer oluştur
            analyzer = DynamicKeyAnalyzer(self.project_dir, existing_keys)

            # Analiz çalıştır
            results = analyzer.analyze()

            # Sonuçları dict formatına çevir
            missing_dynamic = {}
            all_dynamic_keys = set()  # Tüm dinamik key'ler (dead key hesabından çıkarılacak)
            total_missing = 0

            for result in results:
                # Tüm expected_keys dinamik kullanım gösterir
                all_dynamic_keys.update(result.expected_keys)

                if result.missing_keys:
                    pattern_key = result.pattern.pattern
                    missing_dynamic[pattern_key] = {
                        'file': result.pattern.file_path,
                        'line': result.pattern.line_number,
                        'enum': result.enum_name,
                        'prefix': result.pattern.prefix,
                        'suffix': result.pattern.suffix,
                        'expected_keys': result.expected_keys,
                        'existing_keys': result.existing_keys,
                        'missing_keys': result.missing_keys,
                    }
                    total_missing += len(result.missing_keys)

            if verbose:
                if missing_dynamic:
                    print(f"   {Colors.warning('⚠')} Found {total_missing} missing dynamic keys "
                          f"in {len(missing_dynamic)} patterns")
                else:
                    print(f"   {Colors.success('✓')} No missing dynamic keys found")
                if all_dynamic_keys:
                    print(f"   {Colors.info('ℹ')} {len(all_dynamic_keys)} keys used dynamically")

            return missing_dynamic, all_dynamic_keys

        except Exception as e:
            if verbose:
                print(f"   {Colors.error('✗')} Dynamic key analysis failed: {e}")
            return {}, set()

    def _print_summary(self, health: HealthScore):
        """Print analysis summary."""
        print(f"\n{'=' * 70}")
        print(f"{Colors.bold('📊 ANALYSIS SUMMARY')}")
        print(f"{'=' * 70}")

        grade_color = HealthCalculator.get_grade_color(health.grade)
        print(f"🏥 Health Score: {grade_color}{health.score}/100 ({health.grade}){Colors.ENDC}")
        print(f"📈 Localization Rate: {health.localization_rate}%")
        print(f"✅ Localized: {health.localized_count} strings")
        print(f"⚠️  Hardcoded: {health.hardcoded_count} strings")
        print(f"🔴 Missing Keys: {health.missing_keys_count}")
        print(f"🟡 Dead Keys: {health.dead_keys_count}")
        print(f"📦 Duplicates: {health.duplicate_count}")

        # Recommendations
        recommendations = HealthCalculator.get_recommendations(health)
        if recommendations:
            print(f"\n{Colors.bold('💡 RECOMMENDATIONS:')}")
            for rec in recommendations:
                print(f"   {rec}")

        print(f"{'=' * 70}")
