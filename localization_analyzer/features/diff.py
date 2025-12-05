"""Localization diff module - compare languages."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from ..utils.colors import Colors


class DiffType(Enum):
    """Fark tipi."""
    ADDED = "added"      # Hedefte var, kaynakta yok
    REMOVED = "removed"  # Kaynakta var, hedefte yok
    CHANGED = "changed"  # Her ikisinde var ama değer farklı
    SAME = "same"        # Aynı (çevrilmemiş olabilir)


@dataclass
class DiffEntry:
    """Tek bir fark kaydı."""
    key: str
    diff_type: DiffType
    source_value: Optional[str] = None
    target_value: Optional[str] = None


@dataclass
class DiffResult:
    """Diff sonucu."""
    source_lang: str
    target_lang: str
    added: List[DiffEntry] = field(default_factory=list)
    removed: List[DiffEntry] = field(default_factory=list)
    changed: List[DiffEntry] = field(default_factory=list)
    same: List[DiffEntry] = field(default_factory=list)

    @property
    def total_differences(self) -> int:
        return len(self.added) + len(self.removed) + len(self.changed)

    @property
    def has_differences(self) -> bool:
        return self.total_differences > 0


class LocalizationDiff:
    """
    Localization diff hesaplayıcısı.

    İki dil arasındaki farkları bulur:
    - Eksik key'ler (bir dilde var, diğerinde yok)
    - Değişen değerler
    - Çevrilmemiş string'ler (aynı değer)
    """

    def __init__(self):
        """Diff hesaplayıcıyı başlat."""
        pass

    def compare(
        self,
        source_keys: Dict[str, str],
        target_keys: Dict[str, str],
        source_lang: str = "en",
        target_lang: str = "tr"
    ) -> DiffResult:
        """
        İki dil arasındaki farkları hesapla.

        Args:
            source_keys: Kaynak dil key-value'ları
            target_keys: Hedef dil key-value'ları
            source_lang: Kaynak dil kodu
            target_lang: Hedef dil kodu

        Returns:
            DiffResult
        """
        result = DiffResult(source_lang=source_lang, target_lang=target_lang)

        source_set = set(source_keys.keys())
        target_set = set(target_keys.keys())

        # Removed: kaynakta var, hedefte yok
        for key in source_set - target_set:
            result.removed.append(DiffEntry(
                key=key,
                diff_type=DiffType.REMOVED,
                source_value=source_keys[key],
                target_value=None
            ))

        # Added: hedefte var, kaynakta yok
        for key in target_set - source_set:
            result.added.append(DiffEntry(
                key=key,
                diff_type=DiffType.ADDED,
                source_value=None,
                target_value=target_keys[key]
            ))

        # Her ikisinde de var
        for key in source_set & target_set:
            source_value = source_keys[key]
            target_value = target_keys[key]

            if source_value == target_value:
                # Aynı değer - muhtemelen çevrilmemiş
                result.same.append(DiffEntry(
                    key=key,
                    diff_type=DiffType.SAME,
                    source_value=source_value,
                    target_value=target_value
                ))
            else:
                # Farklı değer - çevrilmiş
                result.changed.append(DiffEntry(
                    key=key,
                    diff_type=DiffType.CHANGED,
                    source_value=source_value,
                    target_value=target_value
                ))

        # Sırala
        result.added.sort(key=lambda x: x.key)
        result.removed.sort(key=lambda x: x.key)
        result.changed.sort(key=lambda x: x.key)
        result.same.sort(key=lambda x: x.key)

        return result

    def print_diff(
        self,
        result: DiffResult,
        show_same: bool = False,
        show_values: bool = True,
        limit: int = 50
    ):
        """
        Diff sonucunu yazdır.

        Args:
            result: DiffResult
            show_same: Aynı olan key'leri de göster
            show_values: Değerleri de göster
            limit: Maksimum gösterilecek entry sayısı
        """
        print(f"\n{Colors.bold('📊 LOCALIZATION DIFF')}")
        print("=" * 70)
        print(f"Comparing: {result.source_lang} → {result.target_lang}")
        print()

        # Summary
        print(f"{Colors.bold('📈 SUMMARY')}")
        print("-" * 40)
        print(f"  {Colors.error('−')} Missing in {result.target_lang}: {len(result.removed)}")
        print(f"  {Colors.success('+')} Extra in {result.target_lang}: {len(result.added)}")
        print(f"  {Colors.warning('~')} Translated: {len(result.changed)}")
        if show_same:
            print(f"  {Colors.info('=')} Untranslated (same): {len(result.same)}")
        print()

        # Removed (missing in target)
        if result.removed:
            print(f"{Colors.bold(f'❌ MISSING IN {result.target_lang.upper()}')} ({len(result.removed)})")
            print("-" * 40)

            for entry in result.removed[:limit]:
                print(f"  {Colors.error('−')} {entry.key}")
                if show_values and entry.source_value:
                    print(f"      {result.source_lang}: \"{self._truncate(entry.source_value)}\"")

            if len(result.removed) > limit:
                print(f"  ... and {len(result.removed) - limit} more")
            print()

        # Added (extra in target)
        if result.added:
            print(f"{Colors.bold(f'➕ EXTRA IN {result.target_lang.upper()}')} ({len(result.added)})")
            print("-" * 40)

            for entry in result.added[:limit]:
                print(f"  {Colors.success('+')} {entry.key}")
                if show_values and entry.target_value:
                    print(f"      {result.target_lang}: \"{self._truncate(entry.target_value)}\"")

            if len(result.added) > limit:
                print(f"  ... and {len(result.added) - limit} more")
            print()

        # Changed (translated)
        if result.changed and show_values:
            print(f"{Colors.bold('✅ TRANSLATED')} ({len(result.changed)})")
            print("-" * 40)

            for entry in result.changed[:limit]:
                print(f"  {Colors.warning('~')} {entry.key}")
                print(f"      {result.source_lang}: \"{self._truncate(entry.source_value)}\"")
                print(f"      {result.target_lang}: \"{self._truncate(entry.target_value)}\"")

            if len(result.changed) > limit:
                print(f"  ... and {len(result.changed) - limit} more")
            print()

        # Same (untranslated)
        if show_same and result.same:
            print(f"{Colors.bold('⚠️  UNTRANSLATED (same value)')} ({len(result.same)})")
            print("-" * 40)

            for entry in result.same[:limit]:
                print(f"  {Colors.info('=')} {entry.key}")
                if show_values:
                    print(f"      value: \"{self._truncate(entry.source_value)}\"")

            if len(result.same) > limit:
                print(f"  ... and {len(result.same) - limit} more")
            print()

        # Final summary
        print("=" * 70)
        if not result.has_differences:
            print(f"{Colors.success('✅ No differences found!')}")
        else:
            print(f"Total differences: {result.total_differences}")

    def _truncate(self, text: Optional[str], max_len: int = 50) -> str:
        """Metni kısalt."""
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    def export_diff(self, result: DiffResult, output_path: Path, format: str = "md"):
        """
        Diff sonucunu dosyaya export et.

        Args:
            result: DiffResult
            output_path: Çıktı dosya yolu
            format: Çıktı formatı (md, json, txt)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            import json
            data = {
                "source_lang": result.source_lang,
                "target_lang": result.target_lang,
                "summary": {
                    "missing": len(result.removed),
                    "extra": len(result.added),
                    "translated": len(result.changed),
                    "untranslated": len(result.same)
                },
                "missing": [{"key": e.key, "value": e.source_value} for e in result.removed],
                "extra": [{"key": e.key, "value": e.target_value} for e in result.added],
                "translated": [{"key": e.key, "source": e.source_value, "target": e.target_value} for e in result.changed],
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == "md":
            lines = [
                f"# Localization Diff: {result.source_lang} → {result.target_lang}",
                "",
                "## Summary",
                "",
                f"| Type | Count |",
                f"|------|-------|",
                f"| Missing in {result.target_lang} | {len(result.removed)} |",
                f"| Extra in {result.target_lang} | {len(result.added)} |",
                f"| Translated | {len(result.changed)} |",
                f"| Untranslated | {len(result.same)} |",
                "",
            ]

            if result.removed:
                lines.extend([
                    f"## Missing in {result.target_lang}",
                    "",
                ])
                for entry in result.removed:
                    lines.append(f"- `{entry.key}`: \"{entry.source_value}\"")
                lines.append("")

            if result.added:
                lines.extend([
                    f"## Extra in {result.target_lang}",
                    "",
                ])
                for entry in result.added:
                    lines.append(f"- `{entry.key}`: \"{entry.target_value}\"")
                lines.append("")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        else:  # txt
            lines = [
                f"Localization Diff: {result.source_lang} → {result.target_lang}",
                "=" * 50,
                "",
                f"Missing in {result.target_lang}: {len(result.removed)}",
                f"Extra in {result.target_lang}: {len(result.added)}",
                f"Translated: {len(result.changed)}",
                f"Untranslated: {len(result.same)}",
                "",
            ]

            if result.removed:
                lines.append(f"--- Missing in {result.target_lang} ---")
                for entry in result.removed:
                    lines.append(f"  {entry.key}")
                lines.append("")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        print(f"{Colors.success('✓')} Diff exported to: {output_path}")
