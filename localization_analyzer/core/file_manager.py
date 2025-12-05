"""Multi-language localization file manager."""

from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

from ..frameworks.base import BaseAdapter
from ..utils.colors import Colors


class LocalizationFileManager:
    """
    Manages localization files for multiple languages.

    Improvements over original:
    - Support for unlimited languages (not just TR and EN)
    - Automatic language detection
    - Cross-language validation
    - Missing translation detection
    """

    def __init__(self, adapter: BaseAdapter, localization_dir: Path):
        """
        Initialize file manager.

        Args:
            adapter: Framework adapter (e.g., SwiftAdapter)
            localization_dir: Directory containing localization files
        """
        self.adapter = adapter
        self.localization_dir = localization_dir
        self.languages: Dict[str, List[Path]] = defaultdict(list)  # lang_code -> [file_paths]
        self.keys: Dict[str, Dict[str, str]] = defaultdict(dict)  # key -> {lang: value}
        self.key_modules: Dict[str, str] = {}  # key -> module_name (e.g., "AI", "Common")

        self._discover_languages()

    def _discover_languages(self):
        """Discover all available language files (supports modular .strings files)."""
        if not self.localization_dir.exists():
            print(f"{Colors.warning('⚠️')}  Localization directory not found: {self.localization_dir}")
            return

        pattern = self.adapter.get_localization_file_pattern()

        # Group files by language
        lang_files_count = defaultdict(int)

        for file_path in self.localization_dir.rglob(pattern.split('/')[-1]):
            if self.adapter.should_exclude_file(file_path):
                continue

            # Skip disabled files
            if file_path.name.endswith('.DISABLED'):
                continue

            # Extract language code (framework-specific)
            if hasattr(self.adapter, 'extract_language_code'):
                lang_code = self.adapter.extract_language_code(file_path)
            else:
                # Default: assume parent directory name
                lang_code = file_path.parent.name.replace('.lproj', '')

            self.languages[lang_code].append(file_path)
            lang_files_count[lang_code] += 1

        # Print summary
        if not self.languages:
            print(f"{Colors.error('❌')} No localization files found!")
        else:
            print(f"{Colors.info('📊')} Found {len(self.languages)} languages:")
            for lang_code, files in sorted(self.languages.items()):
                print(f"   {Colors.success('✓')} {Colors.bold(lang_code)}: {len(files)} modules")
            print()

    def load_all_keys(self):
        """Load all keys from all language files (supports modular files)."""
        print(f"\n📚 Loading localization keys...")

        total_files = sum(len(files) for files in self.languages.values())
        processed = 0

        for lang_code, file_paths in self.languages.items():
            for file_path in file_paths:
                # Extract module name from filename (e.g., "AI.strings" -> "AI")
                module_name = file_path.stem  # Gets filename without extension

                lang_keys = self.adapter.parse_localization_file(file_path)

                for key, value in lang_keys.items():
                    self.keys[key][lang_code] = value
                    # Store module info (only once per key, from first occurrence)
                    if key not in self.key_modules:
                        self.key_modules[key] = module_name

                processed += 1

        print(f"   {Colors.success('✓')} Loaded {len(self.keys)} unique keys from {total_files} module files across {len(self.languages)} languages")

    def add_key(
        self,
        key: str,
        translations: Dict[str, str],
        dry_run: bool = False,
        overwrite: bool = False,
        module: Optional[str] = None
    ) -> bool:
        """
        Add a key to language files with module-aware routing.

        Args:
            key: Localization key
            translations: Dictionary of {lang_code: translated_value}
            dry_run: Preview only, don't write
            overwrite: If True, update existing keys
            module: Target module name (e.g., "Common", "AI"). If None, uses key_modules lookup

        Returns:
            Success status
        """
        if key in self.keys and not overwrite:
            print(f"  {Colors.warning('⚠️')}  Key already exists: {key}")
            return False

        if dry_run:
            print(f"  [DRY RUN] Would add key: {Colors.bold(key)}")
            for lang_code, value in translations.items():
                print(f"    {lang_code}: \"{value}\"")
            return True

        # Determine target module
        target_module = module or self.key_modules.get(key)

        success = True
        # Only write to languages that have translations provided
        for lang_code, value in translations.items():
            if not value:
                continue

            file_paths = self.languages.get(lang_code, [])
            if not file_paths:
                # Language folder doesn't exist, skip silently
                continue

            # Handle both Path and List[Path]
            if isinstance(file_paths, Path):
                file_paths = [file_paths]

            # Find the correct module file
            target_file = self._find_module_file(file_paths, target_module)

            if target_file:
                # Use append=False when overwriting to replace existing entries
                if self.adapter.write_localization_entry(target_file, key, value, append=not overwrite):
                    self.keys[key][lang_code] = value
                    # Store module info if not already set
                    if key not in self.key_modules and target_module:
                        self.key_modules[key] = target_module
                else:
                    success = False

        return success

    def _find_module_file(self, file_paths: List[Path], module: Optional[str]) -> Optional[Path]:
        """
        Find the correct module file from a list of paths.

        Args:
            file_paths: List of .strings file paths
            module: Target module name (e.g., "Common", "AI")

        Returns:
            Path to the target file, or first file if no module match
        """
        if not file_paths:
            return None

        if not module:
            # No module specified, use first file
            return file_paths[0]

        # Search for matching module file
        for file_path in file_paths:
            if file_path.stem == module:
                return file_path

        # No exact match, use first file as fallback
        return file_paths[0]

    def key_exists(self, key: str) -> bool:
        """Check if a key exists in any language."""
        return key in self.keys

    def get_key_translations(self, key: str) -> Dict[str, str]:
        """Get all translations for a key."""
        return self.keys.get(key, {})

    @property
    def keys_by_language(self) -> Dict[str, Dict[str, str]]:
        """
        Key'leri dil bazında döndürür.

        Returns:
            {lang_code: {key: value}} sözlüğü

        Örnek:
            {
                "en": {"save": "Save", "cancel": "Cancel"},
                "tr": {"save": "Kaydet", "cancel": "İptal"}
            }
        """
        result: Dict[str, Dict[str, str]] = defaultdict(dict)

        for key, translations in self.keys.items():
            for lang_code, value in translations.items():
                result[lang_code][key] = value

        return dict(result)

    def find_missing_translations(self) -> Dict[str, Set[str]]:
        """
        Find keys that are missing in some languages.

        Returns:
            Dictionary of {key: set of missing languages}
        """
        missing = {}

        for key, translations in self.keys.items():
            missing_langs = set(self.languages.keys()) - set(translations.keys())
            if missing_langs:
                missing[key] = missing_langs

        return missing

    def find_untranslated_keys(self, source_lang: str = 'en') -> Dict[str, Set[str]]:
        """
        Find keys where translation is same as source (likely untranslated).

        Args:
            source_lang: Source language to compare against

        Returns:
            Dictionary of {key: set of languages with identical text}
        """
        untranslated = {}

        for key, translations in self.keys.items():
            if source_lang not in translations:
                continue

            source_text = translations[source_lang]
            same_langs = set()

            for lang_code, text in translations.items():
                if lang_code != source_lang and text == source_text:
                    same_langs.add(lang_code)

            if same_langs:
                untranslated[key] = same_langs

        return untranslated

    def get_language_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for each language.

        Returns:
            Dictionary of {lang_code: {total_keys, missing_keys, completion_percent}}
        """
        stats = {}
        total_keys = len(self.keys)

        for lang_code in self.languages.keys():
            translated_keys = sum(1 for key_translations in self.keys.values()
                                 if lang_code in key_translations)
            missing_keys = total_keys - translated_keys
            completion = (translated_keys / total_keys * 100) if total_keys > 0 else 100

            stats[lang_code] = {
                'total_keys': translated_keys,
                'missing_keys': missing_keys,
                'completion_percent': round(completion, 1),
            }

        return stats

    def validate_all_files(self) -> Dict[str, List[str]]:
        """
        Validate format of all localization files (supports modular files).

        Returns:
            Dictionary of {lang_code: list of errors}
        """
        from ..utils.validators import validate_strings_file_format

        errors = defaultdict(list)

        for lang_code, file_paths in self.languages.items():
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    is_valid, error_msg = validate_strings_file_format(content)
                    if not is_valid:
                        errors[lang_code].append(f"{file_path.name}: {error_msg}")
                except Exception as e:
                    errors[lang_code].append(f"{file_path.name}: {str(e)}")

        return dict(errors)

    def sync_keys_across_languages(
        self,
        source_lang: str,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Sync all keys from source language to other languages.
        Adds missing keys with source language text (to be translated later).

        Args:
            source_lang: Source language code
            dry_run: Preview only

        Returns:
            Dictionary of {lang_code: keys_added_count}
        """
        if source_lang not in self.languages:
            print(f"{Colors.error('❌')} Source language not found: {source_lang}")
            return {}

        added_count = defaultdict(int)

        for key, translations in self.keys.items():
            if source_lang not in translations:
                continue

            source_text = translations[source_lang]

            for lang_code, file_paths in self.languages.items():
                if lang_code == source_lang:
                    continue

                if lang_code not in translations and file_paths:
                    file_path = file_paths[0]  # Use first file by default
                    if dry_run:
                        print(f"  [DRY RUN] Would add to {lang_code}: {key}")
                    else:
                        if self.adapter.write_localization_entry(file_path, key, source_text):
                            self.keys[key][lang_code] = source_text
                            added_count[lang_code] += 1

        return dict(added_count)
