"""Localization statistics module."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

from ..utils.colors import Colors


@dataclass
class TableStats:
    """Tablo istatistikleri."""
    name: str
    total_keys: int = 0
    languages: Dict[str, int] = field(default_factory=dict)  # lang -> key count
    missing_by_lang: Dict[str, int] = field(default_factory=dict)  # lang -> missing count
    completion_by_lang: Dict[str, float] = field(default_factory=dict)  # lang -> percent


@dataclass
class LanguageStats:
    """Dil istatistikleri."""
    code: str
    name: str
    total_keys: int = 0
    translated_keys: int = 0
    missing_keys: int = 0
    completion_percent: float = 0.0
    tables: Dict[str, int] = field(default_factory=dict)  # table -> key count


@dataclass
class ProjectStats:
    """Proje istatistikleri."""
    project_name: str = ""
    generated_at: str = ""
    source_language: str = "en"
    total_languages: int = 0
    total_tables: int = 0
    total_keys: int = 0
    overall_completion: float = 0.0
    languages: List[LanguageStats] = field(default_factory=list)
    tables: List[TableStats] = field(default_factory=list)
    missing_translations: Dict[str, List[str]] = field(default_factory=dict)  # lang -> [missing keys]

    def to_dict(self) -> Dict[str, Any]:
        """Sözlüğe dönüştür."""
        return {
            'project_name': self.project_name,
            'generated_at': self.generated_at,
            'source_language': self.source_language,
            'summary': {
                'total_languages': self.total_languages,
                'total_tables': self.total_tables,
                'total_keys': self.total_keys,
                'overall_completion': round(self.overall_completion, 2),
            },
            'languages': [asdict(lang) for lang in self.languages],
            'tables': [asdict(table) for table in self.tables],
            'missing_translations': self.missing_translations,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON'a dönüştür."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class StatsCalculator:
    """
    Localization istatistik hesaplayıcısı.

    Özellikler:
    - Dil başına tamamlanma yüzdeleri
    - Tablo başına key sayıları
    - Eksik çeviri listesi
    - Genel proje durumu
    """

    # Dil isimleri
    LANGUAGE_NAMES = {
        'ar': 'Arabic', 'de': 'German', 'es': 'Spanish', 'fr': 'French',
        'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'pt': 'Portuguese',
        'ru': 'Russian', 'zh': 'Chinese', 'nl': 'Dutch', 'pl': 'Polish',
        'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish',
        'el': 'Greek', 'he': 'Hebrew', 'hi': 'Hindi', 'th': 'Thai',
        'vi': 'Vietnamese', 'id': 'Indonesian', 'ms': 'Malay', 'cs': 'Czech',
        'hu': 'Hungarian', 'ro': 'Romanian', 'uk': 'Ukrainian', 'ca': 'Catalan',
        'tr': 'Turkish', 'en': 'English',
    }

    def __init__(self, source_lang: str = 'en'):
        """
        İstatistik hesaplayıcıyı başlat.

        Args:
            source_lang: Kaynak dil kodu
        """
        self.source_lang = source_lang

    def calculate(
        self,
        keys_by_language: Dict[str, Dict[str, str]],
        keys_by_table: Optional[Dict[str, Dict[str, str]]] = None,
        project_name: str = ""
    ) -> ProjectStats:
        """
        Tüm istatistikleri hesapla.

        Args:
            keys_by_language: {lang_code: {key: value}} sözlüğü
            keys_by_table: {table_name: {key: value}} sözlüğü (opsiyonel)
            project_name: Proje adı

        Returns:
            ProjectStats
        """
        stats = ProjectStats(
            project_name=project_name,
            generated_at=datetime.now().isoformat(),
            source_language=self.source_lang
        )

        # Kaynak dil key'lerini al
        source_keys = set(keys_by_language.get(self.source_lang, {}).keys())
        stats.total_keys = len(source_keys)
        stats.total_languages = len(keys_by_language)

        # Dil istatistiklerini hesapla
        total_completion = 0.0
        for lang_code, lang_keys in keys_by_language.items():
            lang_key_set = set(lang_keys.keys())

            # Eksik key'ler
            missing = source_keys - lang_key_set
            translated = source_keys & lang_key_set

            # Tamamlanma yüzdesi
            completion = (len(translated) / len(source_keys) * 100) if source_keys else 100.0

            lang_stats = LanguageStats(
                code=lang_code,
                name=self.LANGUAGE_NAMES.get(lang_code, f'Language ({lang_code})'),
                total_keys=len(lang_keys),
                translated_keys=len(translated),
                missing_keys=len(missing),
                completion_percent=round(completion, 2)
            )

            stats.languages.append(lang_stats)

            # Eksik çevirileri kaydet (kaynak dil hariç)
            if lang_code != self.source_lang and missing:
                stats.missing_translations[lang_code] = sorted(list(missing))

            if lang_code != self.source_lang:
                total_completion += completion

        # Genel tamamlanma (kaynak dil hariç)
        other_langs = len(keys_by_language) - 1
        stats.overall_completion = total_completion / other_langs if other_langs > 0 else 100.0

        # Dilleri tamamlanma yüzdesine göre sırala
        stats.languages.sort(key=lambda x: x.completion_percent, reverse=True)

        # Tablo istatistiklerini hesapla
        if keys_by_table:
            stats.total_tables = len(keys_by_table)
            for table_name, table_keys in keys_by_table.items():
                table_stats = TableStats(
                    name=table_name,
                    total_keys=len(table_keys)
                )
                stats.tables.append(table_stats)

            stats.tables.sort(key=lambda x: x.total_keys, reverse=True)

        return stats

    def print_summary(self, stats: ProjectStats):
        """Özet istatistikleri yazdır."""
        print(f"\n{Colors.bold('📊 LOCALIZATION STATISTICS')}")
        print("=" * 70)

        if stats.project_name:
            print(f"Project: {stats.project_name}")
        print(f"Generated: {stats.generated_at}")
        print(f"Source language: {stats.source_language}")
        print()

        # Genel özet
        print(f"{Colors.bold('📈 SUMMARY')}")
        print("-" * 40)
        print(f"  Total languages: {stats.total_languages}")
        print(f"  Total keys: {stats.total_keys}")
        print(f"  Overall completion: {self._completion_bar(stats.overall_completion)}")
        print()

        # Dil detayları
        print(f"{Colors.bold('🌍 LANGUAGES')}")
        print("-" * 40)

        for lang in stats.languages:
            status = Colors.success('✓') if lang.completion_percent >= 100 else (
                Colors.warning('◐') if lang.completion_percent >= 80 else Colors.error('○')
            )

            print(f"  {status} {lang.code} ({lang.name})")
            print(f"     {self._completion_bar(lang.completion_percent)}")
            print(f"     Keys: {lang.translated_keys}/{stats.total_keys}, Missing: {lang.missing_keys}")
            print()

        # Tablo detayları
        if stats.tables:
            print(f"{Colors.bold('📋 TABLES')}")
            print("-" * 40)

            for table in stats.tables[:10]:  # İlk 10 tablo
                print(f"  • {table.name}: {table.total_keys} keys")

            if len(stats.tables) > 10:
                print(f"  ... and {len(stats.tables) - 10} more tables")
            print()

        # Eksik çeviriler
        missing_count = sum(len(keys) for keys in stats.missing_translations.values())
        if missing_count > 0:
            print(f"{Colors.bold('⚠️  MISSING TRANSLATIONS')}")
            print("-" * 40)

            for lang, keys in sorted(stats.missing_translations.items()):
                print(f"  {lang}: {len(keys)} missing")
                for key in keys[:5]:
                    print(f"    - {key}")
                if len(keys) > 5:
                    print(f"    ... and {len(keys) - 5} more")
            print()

    def _completion_bar(self, percent: float, width: int = 20) -> str:
        """Tamamlanma çubuğu oluştur."""
        filled = int(width * percent / 100)
        empty = width - filled

        if percent >= 100:
            color = Colors.success
        elif percent >= 80:
            color = Colors.warning
        else:
            color = Colors.error

        bar = color('█' * filled) + '░' * empty
        return f"[{bar}] {percent:.1f}%"

    def print_missing_details(self, stats: ProjectStats, lang: Optional[str] = None):
        """Eksik çeviri detaylarını yazdır."""
        print(f"\n{Colors.bold('📋 MISSING TRANSLATION DETAILS')}")
        print("=" * 70)

        translations = stats.missing_translations
        if lang:
            translations = {lang: stats.missing_translations.get(lang, [])}

        for lang_code, keys in sorted(translations.items()):
            if not keys:
                continue

            lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code)
            print(f"\n{Colors.bold(f'{lang_code} ({lang_name})')} - {len(keys)} missing:")
            print("-" * 40)

            for key in sorted(keys):
                print(f"  • {key}")

    def export_json(self, stats: ProjectStats, output_path: Path):
        """JSON dosyasına dışa aktar."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(stats.to_json())

        print(f"{Colors.success('✓')} Stats exported to: {output_path}")

    def export_markdown(self, stats: ProjectStats, output_path: Path):
        """Markdown dosyasına dışa aktar."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Localization Statistics",
            f"",
            f"**Generated:** {stats.generated_at}",
            f"**Source Language:** {stats.source_language}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Languages | {stats.total_languages} |",
            f"| Total Keys | {stats.total_keys} |",
            f"| Overall Completion | {stats.overall_completion:.1f}% |",
            f"",
            f"## Languages",
            f"",
            f"| Language | Code | Keys | Missing | Completion |",
            f"|----------|------|------|---------|------------|",
        ]

        for lang in stats.languages:
            status = "✅" if lang.completion_percent >= 100 else (
                "🔶" if lang.completion_percent >= 80 else "❌"
            )
            lines.append(
                f"| {status} {lang.name} | {lang.code} | {lang.translated_keys} | "
                f"{lang.missing_keys} | {lang.completion_percent:.1f}% |"
            )

        if stats.missing_translations:
            lines.extend([
                f"",
                f"## Missing Translations",
                f"",
            ])

            for lang_code, keys in sorted(stats.missing_translations.items()):
                lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code)
                lines.append(f"### {lang_name} ({lang_code}) - {len(keys)} missing")
                lines.append("")
                for key in sorted(keys)[:20]:
                    lines.append(f"- `{key}`")
                if len(keys) > 20:
                    lines.append(f"- ... and {len(keys) - 20} more")
                lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"{Colors.success('✓')} Stats exported to: {output_path}")
