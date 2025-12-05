"""Fix missing localization keys."""

from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict

from ..core.analyzer import AnalysisResult
from ..core.file_manager import LocalizationFileManager
from ..frameworks.base import BaseAdapter
from ..utils.colors import Colors
from .translator import TranslationService, translate_key_value


class MissingKeysFixer:
    """
    Fix missing keys by adding them to localization files.

    Features:
    - Extract context from usage
    - Generate translations
    - Add to all language files
    - Backup support
    """

    def __init__(
        self,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter,
        project_dir: Path,
        dry_run: bool = False,
        source_lang: str = 'en'
    ):
        """
        Initialize missing keys fixer.

        Args:
            file_manager: Localization file manager
            adapter: Framework adapter
            project_dir: Project root directory
            dry_run: Preview mode without making changes
            source_lang: Source language for translations (default: en)
        """
        self.file_manager = file_manager
        self.adapter = adapter
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.source_lang = source_lang
        self.keys_added = 0
        self.keys_failed = 0

        # Translation service with cache
        cache_file = project_dir / '.localization_cache' / 'translations.json'
        self.translator = TranslationService(source_lang=source_lang, cache_file=cache_file)

    def fix_missing_keys(
        self,
        missing_keys: Dict[str, List[str]],
        auto_translate: bool = False
    ) -> Dict[str, int]:
        """
        Fix all missing keys.

        Args:
            missing_keys: Dictionary of {key: [files using it]}
            auto_translate: Try to generate translations

        Returns:
            Dictionary of {language: keys_added_count}
        """
        print(f"\n{Colors.bold('🔧 FIXING MISSING KEYS')}")
        print("=" * 70)

        if self.dry_run:
            print(f"{Colors.info('[DRY RUN - No changes will be made]')}\n")

        results = defaultdict(int)

        for key, files in sorted(missing_keys.items()):
            print(f"\n{Colors.warning('❓')} Missing: {Colors.bold(key)}")
            print(f"   Used in {len(files)} file(s): {', '.join(files[:2])}")
            if len(files) > 2:
                print(f"   ... and {len(files) - 2} more")

            # Try to extract context from code
            context = self._extract_context(key, files[0])

            # Generate translations
            translations = self._generate_translations(key, context, auto_translate)

            if not translations:
                print(f"   {Colors.warning('⚠️')}  Could not generate translations")
                self.keys_failed += 1
                continue

            # Show translations
            print(f"   Suggested translations:")
            for lang, text in translations.items():
                print(f"      {lang}: \"{text}\"")

            # Add to localization files
            if self.dry_run:
                print(f"   {Colors.info('[DRY RUN]')} Would add to all languages")
                self.keys_added += 1
            else:
                success = self.file_manager.add_key(key, translations, dry_run=False)
                if success:
                    print(f"   {Colors.success('✅')} Added to all languages")
                    self.keys_added += 1
                    for lang in translations.keys():
                        results[lang] += 1
                else:
                    print(f"   {Colors.error('❌')} Failed to add")
                    self.keys_failed += 1

        return dict(results)

    def _extract_context(self, key: str, file_path: str) -> Dict[str, str]:
        """
        Extract context from code to help with translation.

        Args:
            key: Localization key
            file_path: File where key is used

        Returns:
            Context dictionary
        """
        context = {
            'key': key,
            'file': file_path,
            'surrounding_code': '',
        }

        try:
            full_path = self.project_dir / file_path
            if not full_path.exists():
                return context

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find usage
            import re
            pattern = rf'String\(\s*localized:\s*"{re.escape(key)}"'
            match = re.search(pattern, content)

            if match:
                # Get surrounding lines
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context['surrounding_code'] = content[start:end]

        except (IOError, OSError, UnicodeDecodeError):
            # File read errors - return context with empty surrounding_code
            pass
        except re.error:
            # Invalid regex pattern - return context as is
            pass

        return context

    def _generate_translations(
        self,
        key: str,
        context: Dict[str, str],
        auto_translate: bool = False
    ) -> Dict[str, str]:
        """
        Generate translations for a key.

        Args:
            key: Localization key
            context: Context from code
            auto_translate: Use automatic translation

        Returns:
            Dictionary of {language: translation}
        """
        # Parse key to generate default translation
        default_text = self._key_to_text(key)

        translations = {}

        # For each language
        for lang_code in self.file_manager.languages.keys():
            if auto_translate and lang_code != self.source_lang:
                # Otomatik çeviri yap
                translated = self.translator.translate(
                    default_text,
                    target_lang=lang_code,
                    source_lang=self.source_lang
                )
                if translated:
                    translations[lang_code] = translated
                    print(f"   🌍 Auto-translated to {lang_code}: \"{translated}\"")
                else:
                    translations[lang_code] = default_text
                    print(f"   ⚠️  Translation failed for {lang_code}, using default")
            else:
                translations[lang_code] = default_text

        return translations

    def _key_to_text(self, key: str) -> str:
        """
        Convert key name to readable text.

        Examples:
            'common.save' -> 'Save'
            'button.cancel' -> 'Cancel'
            'error.network.timeout' -> 'Network Timeout'
        """
        # Remove prefix
        parts = key.split('.')

        # Use last part or last two parts
        if len(parts) > 2:
            text_parts = parts[-2:]
        else:
            text_parts = parts[-1:]

        # Capitalize and join
        text = ' '.join(part.capitalize() for part in text_parts)

        return text

    def analyze_and_categorize(
        self,
        missing_keys: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Categorize missing keys by pattern.

        Returns:
            Dictionary of {category: [keys]}
        """
        categories = defaultdict(list)

        for key in missing_keys.keys():
            parts = key.split('.')

            if len(parts) > 0:
                category = parts[0]
                categories[category].append(key)
            else:
                categories['other'].append(key)

        return dict(categories)

    def print_summary(self):
        """Print fix summary."""
        print(f"\n{'=' * 70}")
        print(f"{Colors.bold('📊 MISSING KEYS FIX SUMMARY')}")
        print("=" * 70)
        print(f"✅ Added: {self.keys_added}")
        print(f"❌ Failed: {self.keys_failed}")
        print(f"📊 Success Rate: {(self.keys_added / (self.keys_added + self.keys_failed) * 100) if (self.keys_added + self.keys_failed) > 0 else 0:.1f}%")
        print("=" * 70)

    def generate_missing_keys_report(
        self,
        missing_keys: Dict[str, List[str]],
        output_path: Path
    ):
        """
        Generate detailed missing keys report.

        Args:
            missing_keys: Missing keys dictionary
            output_path: Output file path
        """
        categories = self.analyze_and_categorize(missing_keys)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Missing Localization Keys Report\n\n")
            f.write(f"Total missing keys: {len(missing_keys)}\n\n")

            for category, keys in sorted(categories.items()):
                f.write(f"## {category.title()} ({len(keys)} keys)\n\n")

                for key in sorted(keys):
                    files = missing_keys[key]
                    f.write(f"### `{key}`\n\n")
                    f.write(f"Used in {len(files)} file(s):\n")
                    for file_path in files:
                        f.write(f"- `{file_path}`\n")
                    f.write("\n")

                    # Suggested translation
                    suggested = self._key_to_text(key)
                    f.write("Suggested translations:\n")
                    f.write("```\n")
                    for lang in self.file_manager.languages.keys():
                        f.write(f'"{key}" = "{suggested}";  // {lang}\n')
                    f.write("```\n\n")

        print(f"\n{Colors.success('✓')} Missing keys report: {output_path}")
