"""Localization sync module - synchronize all languages."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import shutil

from ..utils.colors import Colors
from .translator import TranslationService


@dataclass
class SyncResult:
    """Senkronizasyon sonucu."""
    language: str
    added_keys: List[str] = field(default_factory=list)
    translated_keys: List[str] = field(default_factory=list)
    failed_keys: List[str] = field(default_factory=list)
    skipped_keys: List[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.added_keys)

    @property
    def success_count(self) -> int:
        return len(self.translated_keys)

    @property
    def failure_count(self) -> int:
        return len(self.failed_keys)


@dataclass
class SyncSummary:
    """Tüm senkronizasyonun özeti."""
    source_lang: str
    results: List[SyncResult] = field(default_factory=list)
    backup_paths: Dict[str, Path] = field(default_factory=dict)
    dry_run: bool = False

    @property
    def total_languages(self) -> int:
        return len(self.results)

    @property
    def total_keys_added(self) -> int:
        return sum(r.total_processed for r in self.results)

    @property
    def total_translations(self) -> int:
        return sum(r.success_count for r in self.results)

    @property
    def total_failures(self) -> int:
        return sum(r.failure_count for r in self.results)

    @property
    def has_changes(self) -> bool:
        return self.total_keys_added > 0


class LocalizationSync:
    """
    Localization senkronizasyon yöneticisi.

    Tüm dilleri kaynak dile göre senkronize eder:
    - Eksik key'leri tespit et
    - Otomatik çeviri yap
    - .strings dosyalarına yaz
    """

    def __init__(
        self,
        source_lang: str = "en",
        auto_translate: bool = True,
        backup: bool = True
    ):
        """
        Sync yöneticisini başlat.

        Args:
            source_lang: Kaynak dil kodu
            auto_translate: Eksik key'leri otomatik çevir
            backup: Değişiklik öncesi yedek al
        """
        self.source_lang = source_lang
        self.auto_translate = auto_translate
        self.backup = backup
        self.translator = TranslationService(source_lang=source_lang) if auto_translate else None

    def sync_all(
        self,
        source_keys: Dict[str, str],
        target_files: Dict[str, Path],
        target_keys: Dict[str, Dict[str, str]],
        dry_run: bool = False
    ) -> SyncSummary:
        """
        Tüm dilleri senkronize et.

        Args:
            source_keys: Kaynak dil key-value'ları
            target_files: Hedef dil dosya yolları {lang: path}
            target_keys: Hedef dil key-value'ları {lang: {key: value}}
            dry_run: True ise dosyalara yazma

        Returns:
            SyncSummary
        """
        summary = SyncSummary(source_lang=self.source_lang, dry_run=dry_run)

        for lang, file_path in target_files.items():
            if lang == self.source_lang:
                continue

            current_keys = target_keys.get(lang, {})
            result = self.sync_language(
                lang=lang,
                source_keys=source_keys,
                current_keys=current_keys,
                file_path=file_path,
                dry_run=dry_run
            )

            summary.results.append(result)

            # Backup path'i kaydet
            if result.total_processed > 0 and self.backup and not dry_run:
                backup_path = self._create_backup(file_path)
                if backup_path:
                    summary.backup_paths[lang] = backup_path

        return summary

    def sync_language(
        self,
        lang: str,
        source_keys: Dict[str, str],
        current_keys: Dict[str, str],
        file_path: Path,
        dry_run: bool = False
    ) -> SyncResult:
        """
        Tek bir dili senkronize et.

        Args:
            lang: Hedef dil kodu
            source_keys: Kaynak dil key-value'ları
            current_keys: Mevcut hedef dil key-value'ları
            file_path: Hedef .strings dosya yolu
            dry_run: True ise dosyaya yazma

        Returns:
            SyncResult
        """
        result = SyncResult(language=lang)

        # Eksik key'leri bul
        source_set = set(source_keys.keys())
        current_set = set(current_keys.keys())
        missing_keys = source_set - current_set

        if not missing_keys:
            return result

        result.added_keys = sorted(missing_keys)

        # Yeni key-value'ları hazırla
        new_entries: Dict[str, str] = {}

        for key in missing_keys:
            source_value = source_keys[key]

            if self.auto_translate and self.translator:
                # Çeviri yap
                translated = self.translator.translate(source_value, lang)

                if translated:
                    new_entries[key] = translated
                    result.translated_keys.append(key)
                else:
                    # Çeviri başarısız - kaynak değeri TODO ile ekle
                    new_entries[key] = f"{source_value} /* TODO: Translate to {lang} */"
                    result.failed_keys.append(key)
            else:
                # Otomatik çeviri kapalı - kaynak değeri ekle
                new_entries[key] = f"{source_value} /* TODO: Translate to {lang} */"
                result.skipped_keys.append(key)

        # Dosyaya yaz
        if not dry_run and new_entries:
            self._append_to_file(file_path, new_entries)

        return result

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Dosyanın yedeğini al."""
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"

        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception:
            return None

    def _append_to_file(self, file_path: Path, entries: Dict[str, str]):
        """Yeni entry'leri dosyaya ekle."""
        if not file_path.exists():
            return

        # Mevcut içeriği oku
        content = file_path.read_text(encoding='utf-8')

        # Yeni satırları hazırla
        new_lines = [
            "",
            "/* === Auto-synced entries === */",
            f"/* Synced at: {datetime.now().isoformat()} */",
            ""
        ]

        for key, value in sorted(entries.items()):
            # Escape double quotes in value
            escaped_value = value.replace('"', '\\"')
            new_lines.append(f'"{key}" = "{escaped_value}";')

        # Dosyaya ekle
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
            f.write('\n')

    def print_summary(self, summary: SyncSummary, verbose: bool = False):
        """Senkronizasyon özetini yazdır."""
        mode = Colors.warning("[DRY RUN]") if summary.dry_run else ""
        print(f"\n{Colors.bold('🔄 LOCALIZATION SYNC')} {mode}")
        print("=" * 60)
        print(f"Source language: {summary.source_lang}")
        print(f"Languages synced: {summary.total_languages}")
        print()

        if not summary.has_changes:
            print(f"{Colors.success('✅ All languages are in sync!')}")
            return

        # Özet tablo
        print(f"{Colors.bold('📊 SUMMARY')}")
        print("-" * 40)
        print(f"  Total keys added: {summary.total_keys_added}")
        print(f"  Translations: {Colors.success(str(summary.total_translations))}")
        print(f"  Failed: {Colors.error(str(summary.total_failures))}")
        print()

        # Dil detayları
        print(f"{Colors.bold('📋 DETAILS BY LANGUAGE')}")
        print("-" * 40)

        for result in summary.results:
            if result.total_processed == 0:
                continue

            status = Colors.success("✓") if result.failure_count == 0 else Colors.warning("⚠")
            print(f"  {status} {result.language}: +{result.total_processed} keys")

            if verbose:
                for key in result.translated_keys[:10]:
                    print(f"      {Colors.success('+')} {key}")
                if len(result.translated_keys) > 10:
                    print(f"      ... and {len(result.translated_keys) - 10} more")

                for key in result.failed_keys:
                    print(f"      {Colors.error('!')} {key} (translation failed)")

        print()

        # Backup bilgisi
        if summary.backup_paths and not summary.dry_run:
            print(f"{Colors.bold('💾 BACKUPS')}")
            print("-" * 40)
            for lang, path in summary.backup_paths.items():
                print(f"  {lang}: {path}")
            print()

        # Final durum
        print("=" * 60)
        if summary.dry_run:
            print(f"{Colors.warning('No files were modified (dry run)')}")
        else:
            print(f"{Colors.success('✅ Sync completed!')}")

    def export_report(
        self,
        summary: SyncSummary,
        output_path: Path,
        format: str = "json"
    ):
        """Senkronizasyon raporunu export et."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            import json
            data = {
                "timestamp": datetime.now().isoformat(),
                "source_lang": summary.source_lang,
                "dry_run": summary.dry_run,
                "summary": {
                    "total_languages": summary.total_languages,
                    "total_keys_added": summary.total_keys_added,
                    "total_translations": summary.total_translations,
                    "total_failures": summary.total_failures
                },
                "languages": [
                    {
                        "code": r.language,
                        "added_keys": r.added_keys,
                        "translated": r.translated_keys,
                        "failed": r.failed_keys,
                        "skipped": r.skipped_keys
                    }
                    for r in summary.results
                ],
                "backups": {k: str(v) for k, v in summary.backup_paths.items()}
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == "md":
            lines = [
                "# Localization Sync Report",
                "",
                f"**Timestamp:** {datetime.now().isoformat()}",
                f"**Source Language:** {summary.source_lang}",
                f"**Dry Run:** {summary.dry_run}",
                "",
                "## Summary",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Languages Synced | {summary.total_languages} |",
                f"| Total Keys Added | {summary.total_keys_added} |",
                f"| Translations | {summary.total_translations} |",
                f"| Failures | {summary.total_failures} |",
                "",
            ]

            if summary.results:
                lines.extend([
                    "## Language Details",
                    "",
                ])

                for result in summary.results:
                    if result.total_processed == 0:
                        continue

                    lines.extend([
                        f"### {result.language}",
                        "",
                        f"- **Added:** {result.total_processed}",
                        f"- **Translated:** {result.success_count}",
                        f"- **Failed:** {result.failure_count}",
                        "",
                    ])

                    if result.added_keys:
                        lines.append("**Keys:**")
                        for key in result.added_keys[:20]:
                            status = "✅" if key in result.translated_keys else "❌"
                            lines.append(f"- {status} `{key}`")
                        if len(result.added_keys) > 20:
                            lines.append(f"- ... and {len(result.added_keys) - 20} more")
                        lines.append("")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        print(f"{Colors.success('✓')} Report exported to: {output_path}")
