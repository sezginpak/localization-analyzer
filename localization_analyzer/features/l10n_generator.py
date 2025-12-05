"""L10n enum and .strings file generator for Swift projects."""

from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

from ..frameworks.base import BaseAdapter
from ..utils.colors import Colors


@dataclass
class L10nEntry:
    """Represents a single L10n entry."""
    key: str  # camelCase key for Swift (e.g., moodTakibi)
    string_key: str  # key for .strings file (e.g., moodTakibi)
    original_text: str  # Original Turkish text
    english_text: str  # English translation (if available)
    module: str  # L10n module (e.g., About, Profile)
    file_path: str  # Source file where it was found
    line: int  # Line number


class L10nGenerator:
    """
    Generates L10n enum entries and .strings files.

    This class handles:
    1. Grouping hardcoded strings by module
    2. Generating L10n enum code
    3. Adding entries to .strings files
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        project_dir: Path,
        resources_dir: Path,
        dry_run: bool = False
    ):
        self.adapter = adapter
        self.project_dir = project_dir
        self.resources_dir = resources_dir
        self.dry_run = dry_run
        self.entries_by_module: Dict[str, List[L10nEntry]] = defaultdict(list)
        self.generated_count = 0
        self.skipped_count = 0

    def process_hardcoded_strings(self, hardcoded_strings: list) -> Dict[str, List[L10nEntry]]:
        """
        Process hardcoded strings and group them by module.

        Args:
            hardcoded_strings: List of HardcodedString objects from analyzer

        Returns:
            Dictionary of module -> list of L10nEntry
        """
        seen_keys: Dict[str, Set[str]] = defaultdict(set)  # module -> set of keys

        for item in hardcoded_strings:
            # Determine module from file path
            module = self.adapter.determine_module(item.file)

            # Generate clean key
            clean_key = self.adapter.text_to_key(item.text)

            # Skip if key already exists in this module
            if clean_key in seen_keys[module]:
                self.skipped_count += 1
                continue

            seen_keys[module].add(clean_key)

            entry = L10nEntry(
                key=clean_key,
                string_key=clean_key,
                original_text=item.text,
                english_text=item.text,  # For now, same as original
                module=module,
                file_path=item.file,
                line=item.line
            )

            self.entries_by_module[module].append(entry)

        return self.entries_by_module

    def generate_l10n_enum_code(self, module: str, entries: List[L10nEntry]) -> str:
        """
        Generate L10n enum code for a module.

        Args:
            module: Module name (e.g., "About")
            entries: List of L10nEntry for this module

        Returns:
            Swift code for the L10n enum section
        """
        table_name = module.lower()
        lines = [f"    // MARK: - {module}"]
        lines.append(f"    enum {module} {{")

        for entry in sorted(entries, key=lambda e: e.key):
            lines.append(f'        static let {entry.key} = "{entry.string_key}".localized(from: .{table_name})')

        lines.append("    }")
        lines.append("")

        return "\n".join(lines)

    def generate_strings_content(self, entries: List[L10nEntry], language: str) -> str:
        """
        Generate .strings file content.

        Args:
            entries: List of L10nEntry
            language: Language code (tr or en)

        Returns:
            .strings file content
        """
        lines = []

        for entry in sorted(entries, key=lambda e: e.key):
            text = entry.original_text if language == "tr" else entry.english_text
            # Escape quotes in the text
            text = text.replace('"', '\\"')
            lines.append(f'"{entry.string_key}" = "{text}";')

        return "\n".join(lines)

    def update_strings_file(self, module: str, entries: List[L10nEntry], language: str) -> bool:
        """
        Update a .strings file with new entries.

        Args:
            module: Module name (e.g., "About")
            entries: List of L10nEntry
            language: Language code (tr or en)

        Returns:
            Success status
        """
        lproj_dir = self.resources_dir / f"{language}.lproj"
        strings_file = lproj_dir / f"{module}.strings"

        # Read existing content
        existing_keys = set()
        existing_content = ""

        if strings_file.exists():
            try:
                with open(strings_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                    # Extract existing keys
                    import re
                    matches = re.findall(r'^"([^"]+)"\s*=', existing_content, re.MULTILINE)
                    existing_keys = set(matches)
            except Exception as e:
                print(f"  {Colors.error('❌')} Error reading {strings_file}: {e}")
                return False

        # Filter out entries that already exist
        new_entries = [e for e in entries if e.string_key not in existing_keys]

        if not new_entries:
            print(f"  {Colors.info('ℹ️')} {strings_file.name}: No new entries to add")
            return True

        # Generate new content
        new_content = self.generate_strings_content(new_entries, language)

        if self.dry_run:
            print(f"\n  {Colors.info('[DRY RUN]')} Would add to {strings_file}:")
            for entry in new_entries[:5]:  # Show first 5
                text = entry.original_text if language == "tr" else entry.english_text
                print(f"    {Colors.OKGREEN}+ \"{entry.string_key}\" = \"{text[:40]}...\"{Colors.ENDC}" if len(text) > 40 else f"    {Colors.OKGREEN}+ \"{entry.string_key}\" = \"{text}\"{Colors.ENDC}")
            if len(new_entries) > 5:
                print(f"    ... and {len(new_entries) - 5} more")
            return True

        # Append to file
        try:
            with open(strings_file, 'a', encoding='utf-8') as f:
                f.write("\n\n/* Auto-generated entries */\n")
                f.write(new_content)
                f.write("\n")

            print(f"  {Colors.success('✅')} Added {len(new_entries)} entries to {strings_file.name}")
            self.generated_count += len(new_entries)
            return True
        except Exception as e:
            print(f"  {Colors.error('❌')} Error writing {strings_file}: {e}")
            return False

    def generate_all(self, hardcoded_strings: list, languages: List[str] = None) -> Tuple[str, int]:
        """
        Generate L10n enum and update .strings files.

        Args:
            hardcoded_strings: List of HardcodedString objects
            languages: List of language codes (default: ["tr", "en"])

        Returns:
            Tuple of (L10n enum code, number of entries generated)
        """
        if languages is None:
            languages = ["tr", "en"]

        # Process strings
        print(f"\n{Colors.bold('📦 Processing hardcoded strings...')}")
        self.process_hardcoded_strings(hardcoded_strings)

        # Generate L10n enum code
        print(f"\n{Colors.bold('🔧 Generating L10n enum code...')}")
        enum_code_parts = []

        for module, entries in sorted(self.entries_by_module.items()):
            if entries:
                code = self.generate_l10n_enum_code(module, entries)
                enum_code_parts.append(code)
                print(f"  {Colors.success('✅')} {module}: {len(entries)} entries")

        full_enum_code = "\n".join(enum_code_parts)

        # Update .strings files
        print(f"\n{Colors.bold('📝 Updating .strings files...')}")
        for module, entries in sorted(self.entries_by_module.items()):
            if entries:
                for lang in languages:
                    self.update_strings_file(module, entries, lang)

        return full_enum_code, self.generated_count

    def print_summary(self):
        """Print generation summary."""
        total_entries = sum(len(entries) for entries in self.entries_by_module.values())

        print(f"\n{'=' * 70}")
        print(f"{Colors.bold('📊 L10N GENERATION SUMMARY')}")
        print(f"{'=' * 70}")
        print(f"📦 Modules processed: {len(self.entries_by_module)}")
        print(f"✅ Unique entries: {total_entries}")
        print(f"⏭️  Duplicates skipped: {self.skipped_count}")
        print(f"📝 Entries added to .strings: {self.generated_count}")
        print(f"{'=' * 70}")

        # Print L10n enum code for copy-paste
        if self.entries_by_module:
            print(f"\n{Colors.bold('📋 L10n Enum Code (copy to Localization.swift):')}")
            print(f"{'-' * 70}")
            for module, entries in sorted(self.entries_by_module.items()):
                if entries:
                    print(self.generate_l10n_enum_code(module, entries))
