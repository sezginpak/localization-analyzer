"""L10n enum pattern migrator.

Converts L10n.Module.key patterns to "key".localized(from: .module) pattern.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field

from ..utils.colors import Colors


@dataclass
class MigrationResult:
    """Result of a single migration."""
    file_path: Path
    line_num: int
    original: str
    replacement: str
    l10n_pattern: str


@dataclass
class MigrationSummary:
    """Summary of all migrations."""
    total_files: int = 0
    total_replacements: int = 0
    files_modified: Set[str] = field(default_factory=set)
    patterns_found: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class L10nMigrator:
    """Migrates L10n enum patterns to .localized(from:) pattern."""

    # Pattern to match L10n.Module.key or L10n.Module.Submodule.key
    L10N_PATTERN = re.compile(
        r'L10n\.([A-Z][a-zA-Z0-9]*)\.([A-Z][a-zA-Z0-9]*\.)?([a-zA-Z][a-zA-Z0-9]*)'
        r'(?:\(([^)]*)\))?'  # Optional function call with arguments
    )

    # Module name to StringTable case mapping
    MODULE_TO_TABLE = {
        'Common': 'common',
        'Tab': 'tabs',
        'Tabs': 'tabs',
        'Settings': 'settings',
        'Chat': 'chat',
        'Dashboard': 'dashboard',
        'Stats': 'stats',
        'AI': 'ai',
        'Premium': 'premium',
        'About': 'about',
        'Profile': 'profile',
        'CheckIn': 'checkIn',
        'Legal': 'legal',
        'Analyze': 'analyze',
        'Onboarding': 'onboarding',
        # Nested modules
        'Feature': 'premium',  # L10n.Premium.Feature -> premium
        'Package': 'premium',  # L10n.Premium.Package -> premium
        'Usage': 'premium',    # L10n.Premium.Usage -> premium
        'Error': 'premium',    # L10n.Premium.Error -> premium
        'Privacy': 'legal',    # L10n.Legal.Privacy -> legal
        'Terms': 'legal',      # L10n.Legal.Terms -> legal
        'Slide': 'onboarding', # L10n.Onboarding.Slide -> onboarding
        'Preference': 'onboarding',
        'DataManagement': 'profile',
    }

    def __init__(self, project_dir: Path, dry_run: bool = False):
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.summary = MigrationSummary()
        self.results: List[MigrationResult] = []

    def find_swift_files(self) -> List[Path]:
        """Find all Swift files in project."""
        swift_files = []
        for pattern in ['**/*.swift']:
            swift_files.extend(self.project_dir.glob(pattern))

        # Exclude certain files
        excluded = ['Localization.swift', 'l10n_generated.swift']
        return [f for f in swift_files if f.name not in excluded]

    def convert_l10n_match(self, match: re.Match) -> Tuple[str, str]:
        """Convert a single L10n match to .localized(from:) pattern.

        Returns: (replacement_string, key_for_strings_file)
        """
        full_match = match.group(0)
        module = match.group(1)  # e.g., "Premium", "Common"
        submodule = match.group(2)  # e.g., "Feature." or None
        key = match.group(3)  # e.g., "title", "unlimitedChat"
        args = match.group(4)  # e.g., "name" or None (function arguments)

        # Determine the table name
        if submodule:
            # Nested: L10n.Premium.Feature.x -> use submodule mapping
            submodule_name = submodule.rstrip('.')
            table = self.MODULE_TO_TABLE.get(submodule_name, self.MODULE_TO_TABLE.get(module, 'common'))
            # Build the key with prefix
            string_key = f"{submodule_name.lower()}.{key}"
        else:
            table = self.MODULE_TO_TABLE.get(module, 'common')
            string_key = key

        # Handle function calls with arguments
        if args is not None:
            # L10n.Premium.Usage.messagesRemaining(count) -> "messagesRemaining".localized(from: .premium, with: count)
            return f'"{string_key}".localized(from: .{table}, with: {args})', string_key
        else:
            return f'"{string_key}".localized(from: .{table})', string_key

    def process_file(self, file_path: Path) -> List[MigrationResult]:
        """Process a single file and find all L10n patterns."""
        results = []

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                for match in self.L10N_PATTERN.finditer(line):
                    replacement, key = self.convert_l10n_match(match)
                    original = match.group(0)

                    results.append(MigrationResult(
                        file_path=file_path,
                        line_num=line_num,
                        original=original,
                        replacement=replacement,
                        l10n_pattern=original
                    ))

                    # Track patterns
                    pattern_base = original.split('(')[0]  # Remove function args
                    self.summary.patterns_found[pattern_base] = \
                        self.summary.patterns_found.get(pattern_base, 0) + 1

        except Exception as e:
            self.summary.errors.append(f"{file_path}: {e}")

        return results

    def apply_migrations(self, results: List[MigrationResult]) -> int:
        """Apply migrations to files."""
        if self.dry_run:
            return len(results)

        # Group by file
        by_file: Dict[Path, List[MigrationResult]] = {}
        for result in results:
            if result.file_path not in by_file:
                by_file[result.file_path] = []
            by_file[result.file_path].append(result)

        modified_count = 0

        for file_path, file_results in by_file.items():
            try:
                content = file_path.read_text(encoding='utf-8')

                # Sort by line number descending to avoid offset issues
                file_results.sort(key=lambda r: (r.line_num, -content.find(r.original)), reverse=True)

                for result in file_results:
                    # Replace the pattern
                    content = content.replace(result.original, result.replacement, 1)
                    modified_count += 1

                # Write back
                file_path.write_text(content, encoding='utf-8')
                self.summary.files_modified.add(str(file_path))

            except Exception as e:
                self.summary.errors.append(f"Failed to modify {file_path}: {e}")

        return modified_count

    def migrate_all(self) -> MigrationSummary:
        """Run full migration."""
        print(f"\n{Colors.bold('🔄 L10N MIGRATION')}")
        print("=" * 70)

        # Find files
        swift_files = self.find_swift_files()
        self.summary.total_files = len(swift_files)
        print(f"Found {len(swift_files)} Swift files to scan")

        # Process each file
        all_results = []
        for file_path in swift_files:
            results = self.process_file(file_path)
            all_results.extend(results)
            self.results.extend(results)

        print(f"Found {len(all_results)} L10n patterns to migrate")

        if self.dry_run:
            print(f"\n{Colors.info('[DRY RUN - No changes will be made]')}")

        # Apply migrations
        if all_results:
            modified = self.apply_migrations(all_results)
            self.summary.total_replacements = modified

        return self.summary

    def print_preview(self, limit: int = 20):
        """Print preview of migrations."""
        print(f"\n{Colors.bold('📋 MIGRATION PREVIEW')}")
        print("-" * 70)

        for i, result in enumerate(self.results[:limit]):
            rel_path = result.file_path.relative_to(self.project_dir)
            print(f"\n{Colors.info(f'{rel_path}:{result.line_num}')}")
            print(f"  {Colors.error('-')} {result.original}")
            print(f"  {Colors.success('+')} {result.replacement}")

        if len(self.results) > limit:
            print(f"\n... and {len(self.results) - limit} more")

    def print_summary(self):
        """Print migration summary."""
        print(f"\n{Colors.bold('📊 MIGRATION SUMMARY')}")
        print("=" * 70)

        if self.dry_run:
            print(f"Would modify: {self.summary.total_replacements} patterns")
            print(f"In {len(self.summary.files_modified) or len(set(r.file_path for r in self.results))} files")
        else:
            print(f"{Colors.success('✅')} Modified: {self.summary.total_replacements} patterns")
            print(f"   Files changed: {len(self.summary.files_modified)}")

        # Show top patterns
        if self.summary.patterns_found:
            print(f"\n{Colors.bold('Top patterns migrated:')}")
            sorted_patterns = sorted(
                self.summary.patterns_found.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            for pattern, count in sorted_patterns:
                print(f"  {pattern}: {count}x")

        if self.summary.errors:
            print(f"\n{Colors.error('❌ Errors:')}")
            for error in self.summary.errors[:5]:
                print(f"  {error}")
