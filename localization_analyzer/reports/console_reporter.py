"""Console report generator."""

from pathlib import Path
from typing import Optional

from ..core.analyzer import AnalysisResult
from ..core.file_manager import LocalizationFileManager
from ..core.health_calculator import HealthCalculator
from ..utils.colors import Colors


class ConsoleReporter:
    """Generate beautiful console reports."""

    @staticmethod
    def print_full_report(
        result: AnalysisResult,
        file_manager: LocalizationFileManager,
        show_details: bool = False
    ):
        """
        Print comprehensive console report.

        Args:
            result: Analysis result
            file_manager: File manager instance
            show_details: Show detailed breakdowns
        """
        ConsoleReporter._print_header()
        ConsoleReporter._print_health_score(result.health)
        ConsoleReporter._print_language_stats(file_manager)

        if show_details:
            ConsoleReporter._print_hardcoded_strings(result.hardcoded_strings[:10])
            ConsoleReporter._print_missing_keys(result.missing_keys, file_manager, limit=10)
            ConsoleReporter._print_dynamic_keys(result.dynamic_keys, limit=5)
            ConsoleReporter._print_dead_keys(result.dead_keys, file_manager, limit=10)
            ConsoleReporter._print_duplicates(result.duplicates, limit=5)

        ConsoleReporter._print_recommendations(result.health)

    @staticmethod
    def _print_header():
        """Print report header."""
        print("\n" + "=" * 70)
        print(f"{Colors.bold('📊 LOCALIZATION ANALYSIS REPORT')}")
        print("=" * 70)

    @staticmethod
    def _print_health_score(health):
        """Print health score section."""
        print(f"\n{Colors.bold('🏥 HEALTH SCORE')}")
        print("-" * 70)

        grade_color = HealthCalculator.get_grade_color(health.grade)
        print(f"Overall Score: {grade_color}{health.score}/100 ({health.grade}){Colors.ENDC}")
        print(f"Localization Rate: {health.localization_rate}%")
        print()
        print(f"✅ Localized Strings: {health.localized_count:,}")
        print(f"⚠️  Hardcoded Strings: {health.hardcoded_count}")
        print(f"🔴 Missing Keys: {health.missing_keys_count}")
        print(f"🟡 Dead Keys: {health.dead_keys_count}")
        print(f"📦 Duplicate Strings: {health.duplicate_count}")

    @staticmethod
    def _print_language_stats(file_manager: LocalizationFileManager):
        """Print language statistics."""
        print(f"\n{Colors.bold('🌍 LANGUAGES')}")
        print("-" * 70)

        stats = file_manager.get_language_stats()

        if not stats:
            print("No languages found")
            return

        # Header
        print(f"{'Language':<15} {'Keys':<10} {'Missing':<10} {'Completion':<15}")
        print("-" * 70)

        # Languages
        for lang_code in sorted(stats.keys()):
            lang_stats = stats[lang_code]
            # Get language name (use code if no files)
            files = file_manager.languages.get(lang_code, [])
            name = files[0].parent.name.replace('.lproj', '') if files else lang_code

            completion = lang_stats['completion_percent']
            completion_bar = ConsoleReporter._create_progress_bar(completion)

            print(f"{name:<15} {lang_stats['total_keys']:<10} "
                  f"{lang_stats['missing_keys']:<10} {completion_bar}")

    @staticmethod
    def _print_hardcoded_strings(strings: list, limit: int = 10):
        """Print hardcoded strings."""
        if not strings:
            return

        print(f"\n{Colors.bold('⚠️  TOP HARDCODED STRINGS')}")
        print("-" * 70)

        for i, item in enumerate(strings[:limit], 1):
            priority_color = Colors.FAIL if item.priority >= 8 else Colors.WARNING
            print(f"{i}. [{priority_color}P{item.priority}{Colors.ENDC}] "
                  f"{item.file}:{item.line}")
            print(f"   Text: \"{item.text[:50]}...\" if len(item.text) > 50 else \"{item.text}\"")
            print(f"   Key: {Colors.info(item.suggested_key)}")
            print()

    @staticmethod
    def _print_missing_keys(missing: dict, file_manager: LocalizationFileManager, limit: int = 10):
        """Print missing keys with module info."""
        if not missing:
            return

        print(f"\n{Colors.bold('🔴 MISSING KEYS (in code but not in strings)')}")
        print("-" * 70)

        for i, (key, files) in enumerate(list(missing.items())[:limit], 1):
            module = file_manager.key_modules.get(key, 'Unknown')
            print(f"{i}. {Colors.warning(key)} [{Colors.info(module)}]")
            print(f"   Used in {len(files)} file(s): {', '.join(files[:3])}")
            if len(files) > 3:
                print(f"   ... and {len(files) - 3} more")
            print()

    @staticmethod
    def _print_dynamic_keys(dynamic_keys: dict, limit: int = 5):
        """Print dynamic keys (informational)."""
        if not dynamic_keys:
            return

        print(f"\n{Colors.bold('🔄 DYNAMIC KEYS (runtime-generated, not missing)')}")
        print("-" * 70)
        print(f"{Colors.info('ℹ️  These keys contain interpolation and are resolved at runtime.')}")
        print(f"{Colors.info('   They have matching base patterns in your strings files.')}")
        print()

        for i, (key, files) in enumerate(list(dynamic_keys.items())[:limit], 1):
            print(f"{i}. {Colors.OKCYAN}{key}{Colors.ENDC}")
            print(f"   Used in {len(files)} file(s)")

        if len(dynamic_keys) > limit:
            print(f"\n... and {len(dynamic_keys) - limit} more dynamic keys")
        print()

    @staticmethod
    def _print_dead_keys(dead_keys: set, file_manager: LocalizationFileManager, limit: int = 10):
        """Print dead keys with module info."""
        if not dead_keys:
            return

        print(f"\n{Colors.bold('🟡 DEAD KEYS (in strings but not used in code)')}")
        print("-" * 70)

        for i, key in enumerate(sorted(list(dead_keys))[:limit], 1):
            module = file_manager.key_modules.get(key, 'Unknown')
            print(f"{i}. {key} [{Colors.info(module)}]")

        if len(dead_keys) > limit:
            print(f"\n... and {len(dead_keys) - limit} more")

    @staticmethod
    def _print_duplicates(duplicates: dict, limit: int = 5):
        """Print duplicate strings."""
        if not duplicates:
            return

        print(f"\n{Colors.bold('📦 DUPLICATE STRINGS')}")
        print("-" * 70)

        sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)

        for i, (text, locations) in enumerate(sorted_dups[:limit], 1):
            print(f"{i}. \"{text[:50]}...\" ({len(locations)} occurrences)")
            for loc in locations[:3]:
                print(f"   - {loc.file}:{loc.line}")
            if len(locations) > 3:
                print(f"   ... and {len(locations) - 3} more")
            print()

    @staticmethod
    def _print_recommendations(health):
        """Print recommendations."""
        recommendations = HealthCalculator.get_recommendations(health)

        if not recommendations:
            return

        print(f"\n{Colors.bold('💡 RECOMMENDATIONS')}")
        print("-" * 70)

        for rec in recommendations:
            print(f"   {rec}")

        print()

    @staticmethod
    def _create_progress_bar(percent: float, width: int = 20) -> str:
        """Create ASCII progress bar."""
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)

        if percent >= 90:
            color = Colors.OKGREEN
        elif percent >= 70:
            color = Colors.OKCYAN
        else:
            color = Colors.WARNING

        return f"{color}{bar}{Colors.ENDC} {percent:.1f}%"
