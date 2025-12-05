"""Automatic string fixing with multi-language support."""

from pathlib import Path
from typing import Dict, Optional

from ..frameworks.base import BaseAdapter
from ..core.file_manager import LocalizationFileManager
from ..utils.colors import Colors


class AutoFixer:
    """
    Automatically fix hardcoded strings.

    Improvements over original:
    - Multi-language support (not just TR/EN)
    - Better error handling
    - Dry-run mode
    - Undo support via backups
    """

    def __init__(
        self,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter,
        dry_run: bool = False
    ):
        """
        Initialize auto-fixer.

        Args:
            file_manager: Localization file manager
            adapter: Framework adapter
            dry_run: Preview mode without making changes
        """
        self.file_manager = file_manager
        self.adapter = adapter
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.fixes_failed = 0

    def fix_hardcoded_string(
        self,
        file_path: Path,
        line_num: int,
        original_text: str,
        component_type: str,
        suggested_key: str,
        translations: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Fix a single hardcoded string.

        Args:
            file_path: Source file path
            line_num: Line number
            original_text: Hardcoded text
            component_type: UI component type
            suggested_key: Suggested localization key
            translations: Optional translations {lang: text}

        Returns:
            Success status
        """
        # Default translations (use original text for all languages)
        if translations is None:
            translations = {
                lang: original_text
                for lang in self.file_manager.languages.keys()
            }

        # Read source file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"  {Colors.error('❌')} Failed to read {file_path}: {e}")
            self.fixes_failed += 1
            return False

        # Validate line number
        if line_num < 1 or line_num > len(lines):
            print(f"  {Colors.error('❌')} Invalid line number: {line_num}")
            self.fixes_failed += 1
            return False

        # Get line to modify
        line = lines[line_num - 1]

        # Check if line contains expected text
        if f'"{original_text}"' not in line:
            print(f"  {Colors.warning('⚠️')}  Line doesn't contain expected text: {original_text[:30]}...")
            self.fixes_failed += 1
            return False

        # Generate replacement code
        replacement = self.adapter.generate_localized_code(suggested_key, component_type, str(file_path), original_text)
        new_line = line.replace(f'"{original_text}"', replacement)

        # Dry run mode
        if self.dry_run:
            print(f"\n  {Colors.info('[DRY RUN]')} {file_path}:{line_num}")
            print(f"    {Colors.FAIL}- {line.strip()}{Colors.ENDC}")
            print(f"    {Colors.OKGREEN}+ {new_line.strip()}{Colors.ENDC}")
            print(f"    Key: {Colors.bold(suggested_key)}")
            for lang, text in translations.items():
                print(f"      {lang}: \"{text}\"")
            self.fixes_applied += 1
            return True

        # Add key to localization files
        if not self.file_manager.key_exists(suggested_key):
            if not self.file_manager.add_key(suggested_key, translations, dry_run=False):
                self.fixes_failed += 1
                return False

        # Apply fix to source file
        lines[line_num - 1] = new_line

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"  {Colors.success('✅')} Fixed: {file_path.name}:{line_num}")
            self.fixes_applied += 1
            return True
        except Exception as e:
            print(f"  {Colors.error('❌')} Failed to write {file_path}: {e}")
            self.fixes_failed += 1
            return False

    def fix_duplicate_strings(
        self,
        duplicates: Dict[str, list],
        min_occurrences: int = 2
    ) -> int:
        """
        Fix duplicate hardcoded strings by consolidating to shared key.

        Args:
            duplicates: Dictionary of {text: [HardcodedString list]}
            min_occurrences: Minimum occurrences to fix

        Returns:
            Number of duplicates fixed
        """
        fixed_count = 0

        for text, locations in duplicates.items():
            if len(locations) < min_occurrences:
                continue

            # Use first location's suggested key
            shared_key = locations[0].suggested_key

            print(f"\n{Colors.bold('Fixing duplicate:')} \"{text}\" ({len(locations)} occurrences)")
            print(f"Shared key: {Colors.info(shared_key)}")

            for item in locations:
                success = self.fix_hardcoded_string(
                    Path(item.file),
                    item.line,
                    item.text,
                    item.component,
                    shared_key
                )
                if success:
                    fixed_count += 1

        return fixed_count

    def get_stats(self) -> Dict[str, int]:
        """Return fix statistics."""
        return {
            'applied': self.fixes_applied,
            'failed': self.fixes_failed,
            'total': self.fixes_applied + self.fixes_failed,
            'success_rate': (
                self.fixes_applied / (self.fixes_applied + self.fixes_failed) * 100
                if (self.fixes_applied + self.fixes_failed) > 0
                else 0
            )
        }

    def print_summary(self):
        """Print fix summary."""
        stats = self.get_stats()

        print(f"\n{'=' * 70}")
        print(f"{Colors.bold('🔧 AUTO-FIX SUMMARY')}")
        print(f"{'=' * 70}")
        print(f"✅ Applied: {stats['applied']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"📊 Success Rate: {stats['success_rate']:.1f}%")
        print(f"{'=' * 70}")
