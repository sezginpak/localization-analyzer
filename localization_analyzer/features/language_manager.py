"""Language management for adding/removing languages."""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from ..frameworks.base import BaseAdapter
from ..core.file_manager import LocalizationFileManager
from ..utils.colors import Colors
from ..utils.validators import is_valid_language_code
from .translator import TranslationService


class LanguageManager:
    """
    Manage project languages.

    Features:
    - Add new languages
    - Remove languages
    - List all languages
    - Sync keys across languages
    - Validate language codes
    """

    # Common language names
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

    def __init__(
        self,
        file_manager: LocalizationFileManager,
        adapter: BaseAdapter,
        resources_dir: Path
    ):
        """
        Initialize language manager.

        Args:
            file_manager: Localization file manager
            adapter: Framework adapter
            resources_dir: Resources directory containing .lproj folders
        """
        self.file_manager = file_manager
        self.adapter = adapter
        self.resources_dir = resources_dir

    def list_languages(self) -> List[Dict]:
        """
        List all available languages with statistics.

        Returns:
            List of language info dictionaries
        """
        stats = self.file_manager.get_language_stats()
        result = []

        for lang_code, file_paths in self.file_manager.languages.items():
            lang_stats = stats.get(lang_code, {})
            lang_name = self.LANGUAGE_NAMES.get(lang_code, f'Language ({lang_code})')

            # Handle both single Path and List[Path]
            if isinstance(file_paths, Path):
                file_paths = [file_paths]

            # Check if any file exists
            exists = any(fp.exists() for fp in file_paths) if file_paths else False
            # Show first file path as reference
            path_str = str(file_paths[0].parent) if file_paths else 'N/A'
            # Count modules
            module_count = len(file_paths) if file_paths else 0

            result.append({
                'code': lang_code,
                'name': lang_name,
                'path': path_str,
                'key_count': lang_stats.get('total_keys', 0),
                'missing_keys': lang_stats.get('missing_keys', 0),
                'completion': lang_stats.get('completion_percent', 0),
                'exists': exists,
                'module_count': module_count,
            })

        return sorted(result, key=lambda x: x['completion'], reverse=True)

    def add_language(
        self,
        lang_code: str,
        source_lang: Optional[str] = None,
        empty: bool = False,
        dry_run: bool = False,
        auto_translate: bool = False,
        project_dir: Optional[Path] = None
    ) -> bool:
        """
        Add a new language to the project with modular .strings file support.

        Args:
            lang_code: Language code (e.g., 'es', 'de')
            source_lang: Source language to copy keys from
            empty: Create empty file
            dry_run: Preview mode
            auto_translate: Automatically translate from source language
            project_dir: Project directory for translation cache

        Returns:
            Success status
        """
        # Validate language code
        if not is_valid_language_code(lang_code):
            print(f"{Colors.error('❌')} Invalid language code: {lang_code}")
            return False

        # Check if already exists
        if lang_code in self.file_manager.languages:
            print(f"{Colors.warning('⚠️')}  Language already exists: {lang_code}")
            return False

        # Get language name
        lang_name = self.LANGUAGE_NAMES.get(lang_code, f'Language ({lang_code})')

        print(f"\n{Colors.bold(f'🌍 ADDING LANGUAGE - {lang_name} ({lang_code})')}")
        print("=" * 70)

        # Determine file path based on adapter
        if hasattr(self.adapter, 'create_language_directory'):
            lang_dir = self.adapter.create_language_directory(self.resources_dir, lang_code)
        else:
            # Default: .lproj directory for Swift
            lang_dir = self.resources_dir / f'{lang_code}.lproj'

        # Create directory
        if dry_run:
            print(f"{Colors.info('[DRY RUN]')} Would create: {lang_dir}")
        else:
            lang_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 {Colors.success('✓')} Created: {lang_dir}")

        # Determine source language
        if source_lang is None:
            source_lang = list(self.file_manager.languages.keys())[0] if self.file_manager.languages else 'en'

        if source_lang not in self.file_manager.languages:
            print(f"{Colors.error('❌')} Source language not found: {source_lang}")
            return False

        # Check if source language has modular files
        source_files = self.file_manager.languages.get(source_lang, [])
        if isinstance(source_files, Path):
            source_files = [source_files]

        # Create modular files if source has multiple files
        if len(source_files) > 1:
            print(f"📦 Modular mode: Creating {len(source_files)} .strings files")
            created_files = self._create_modular_files(
                lang_code, lang_name, source_lang, source_files,
                lang_dir, empty, auto_translate, project_dir, dry_run
            )
        else:
            # Single file mode (legacy)
            localization_file = lang_dir / 'Localizable.strings'

            if empty:
                content = self._create_empty_file(lang_code, lang_name)
                print(f"📄 Creating empty localization file")
            else:
                if auto_translate:
                    print(f"🌍 Auto-translating from: {source_lang} → {lang_code}")
                    content = self._create_file_with_translation(
                        lang_code, lang_name, source_lang, project_dir
                    )
                else:
                    print(f"📋 Copying keys from: {source_lang}")
                    content = self._create_file_from_source(lang_code, lang_name, source_lang)

            # Write file
            if dry_run:
                print(f"{Colors.info('[DRY RUN]')} Would write: {localization_file}")
                print(f"   Size: {len(content)} bytes")
            else:
                with open(localization_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"💾 {Colors.success('✓')} Created: {localization_file.name}")

            created_files = [localization_file]

        # Update file manager - IMPORTANT: Must be a list!
        if not dry_run:
            self.file_manager.languages[lang_code] = created_files
            self.file_manager.load_all_keys()

        # Success message
        print(f"\n{Colors.success('✅ Language added successfully!')}")

        # Next steps
        first_file = created_files[0] if created_files else lang_dir / 'Localizable.strings'
        print(f"\n{Colors.bold('📝 Next Steps:')}")
        print(f"1. Review translations in: {first_file.parent}")
        print(f"2. Add to Xcode project (if iOS)")
        print(f"3. Test with device/simulator language settings")

        return True

    def _create_modular_files(
        self,
        target_lang: str,
        target_name: str,
        source_lang: str,
        source_files: List[Path],
        target_dir: Path,
        empty: bool,
        auto_translate: bool,
        project_dir: Optional[Path],
        dry_run: bool
    ) -> List[Path]:
        """
        Create modular .strings files matching source language structure.

        Args:
            target_lang: Target language code
            target_name: Target language name
            source_lang: Source language code
            source_files: List of source .strings files
            target_dir: Target language directory
            empty: Create empty files
            auto_translate: Auto-translate content
            project_dir: Project directory for cache
            dry_run: Preview mode

        Returns:
            List of created file paths
        """
        created_files = []

        # Setup translator if needed
        translator = None
        if auto_translate and project_dir:
            cache_file = project_dir / '.localization_cache' / 'translations.json'
            translator = TranslationService(source_lang=source_lang, cache_file=cache_file)
        elif auto_translate:
            translator = TranslationService(source_lang=source_lang)

        for source_file in source_files:
            module_name = source_file.stem  # e.g., "AI", "Common", "Garden"
            target_file = target_dir / f'{module_name}.strings'

            # Parse source file to get keys for this module
            source_keys = self.adapter.parse_localization_file(source_file)

            if empty:
                content = self._create_empty_module_file(target_lang, target_name, module_name)
            else:
                content = self._create_module_file_content(
                    target_lang, target_name, source_lang,
                    module_name, source_keys, translator
                )

            if dry_run:
                print(f"  {Colors.info('[DRY RUN]')} Would create: {target_file.name} ({len(source_keys)} keys)")
            else:
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  💾 {Colors.success('✓')} Created: {target_file.name} ({len(source_keys)} keys)")

            created_files.append(target_file)

        return created_files

    def _create_empty_module_file(self, lang_code: str, lang_name: str, module_name: str) -> str:
        """Create empty module .strings file with header."""
        return f'''/*
  {module_name}.strings ({lang_name})
  Nara

  Created: {datetime.now().strftime('%Y-%m-%d')}
  Language: {lang_name} ({lang_code})

  TODO: Add translations
*/

'''

    def _create_module_file_content(
        self,
        target_lang: str,
        target_name: str,
        source_lang: str,
        module_name: str,
        source_keys: Dict[str, str],
        translator: Optional[TranslationService]
    ) -> str:
        """
        Create module .strings file content with optional translation.

        Args:
            target_lang: Target language code
            target_name: Target language name
            source_lang: Source language code
            module_name: Module name (e.g., "AI", "Common")
            source_keys: Dict of key -> source value
            translator: Optional translator instance

        Returns:
            File content string
        """
        lines = [
            f'/*',
            f'  {module_name}.strings ({target_name})',
            f'  Nara',
            f'',
            f'  Created: {datetime.now().strftime("%Y-%m-%d")}',
            f'  Language: {target_name} ({target_lang})',
        ]

        if translator:
            lines.append(f'  Auto-translated from: {source_lang}')
            lines.append(f'')
            lines.append(f'  NOTE: Auto-translated - please review for accuracy')
        else:
            lines.append(f'  Copied from: {source_lang}')
            lines.append(f'')
            lines.append(f'  NOTE: Please translate all values to {target_name}')

        lines.extend(['*/', ''])

        translated_count = 0
        failed_count = 0

        for key, source_value in source_keys.items():
            if translator:
                translated = translator.translate(source_value, target_lang, source_lang)
                if translated:
                    # Escape quotes in translated value
                    escaped_value = translated.replace('"', '\\"')
                    lines.append(f'"{key}" = "{escaped_value}";')
                    translated_count += 1
                else:
                    # Fallback to source value
                    lines.append(f'"{key}" = "{source_value}";  // TODO: translate')
                    failed_count += 1
            else:
                lines.append(f'"{key}" = "{source_value}";')

        lines.append('')  # Trailing newline

        if translator:
            print(f"     ✅ {module_name}: {translated_count} translated", end='')
            if failed_count > 0:
                print(f", ⚠️ {failed_count} failed")
            else:
                print()

        return '\n'.join(lines)

    def remove_language(
        self,
        lang_code: str,
        dry_run: bool = False,
        confirm: bool = False
    ) -> bool:
        """
        Remove a language from the project (supports modular files).

        Args:
            lang_code: Language code to remove
            dry_run: Preview mode
            confirm: Confirmation flag

        Returns:
            Success status
        """
        if lang_code not in self.file_manager.languages:
            print(f"{Colors.error('❌')} Language not found: {lang_code}")
            return False

        if not confirm and not dry_run:
            print(f"{Colors.warning('⚠️')}  This will permanently delete language files!")
            print(f"Use --confirm flag to proceed")
            return False

        # Handle both single Path and List[Path]
        file_paths = self.file_manager.languages[lang_code]
        if isinstance(file_paths, Path):
            file_paths = [file_paths]

        lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code)

        print(f"\n{Colors.bold(f'🗑️  REMOVING LANGUAGE - {lang_name} ({lang_code})')}")
        print("=" * 70)
        print(f"📁 Files to delete: {len(file_paths)}")

        if dry_run:
            for file_path in file_paths:
                print(f"  {Colors.info('[DRY RUN]')} Would delete: {file_path.name}")
            if file_paths:
                print(f"  {Colors.info('[DRY RUN]')} Would delete directory: {file_paths[0].parent}")
        else:
            import shutil

            # Delete all files
            for file_path in file_paths:
                if file_path.exists():
                    file_path.unlink()
                    print(f"  {Colors.success('✓')} Deleted: {file_path.name}")

            # Delete directory if empty
            if file_paths:
                lang_dir = file_paths[0].parent
                if lang_dir.exists():
                    try:
                        lang_dir.rmdir()
                        print(f"{Colors.success('✓')} Deleted directory: {lang_dir}")
                    except OSError:
                        print(f"{Colors.info('ℹ️')}  Directory not empty, keeping: {lang_dir}")

            # Update file manager
            del self.file_manager.languages[lang_code]

            print(f"\n{Colors.success('✅ Language removed successfully!')}")

        return True

    def _create_empty_file(self, lang_code: str, lang_name: str) -> str:
        """Create empty localization file with header."""
        if hasattr(self.adapter, 'create_strings_file_header'):
            return self.adapter.create_strings_file_header(lang_name, '')

        # Default header
        return f'''/*
  Localizable.strings ({lang_name})

  Created: {datetime.now().strftime('%Y-%m-%d')}
  Language: {lang_name} ({lang_code})

  TODO: Add translations
*/

'''

    def _create_file_from_source(
        self,
        target_lang: str,
        target_name: str,
        source_lang: str
    ) -> str:
        """Create localization file by copying from source."""
        lines = [
            f'/*',
            f'  Localizable.strings ({target_name})',
            f'',
            f'  Created: {datetime.now().strftime("%Y-%m-%d")}',
            f'  Language: {target_name} ({target_lang})',
            f'  Copied from: {source_lang}',
            f'',
            f'  NOTE: Please translate all values to {target_name}',
            f'*/',
            f''
        ]

        # Add all keys from file manager
        for key, translations in self.file_manager.keys.items():
            if source_lang in translations:
                value = translations[source_lang]
                lines.append(f'"{key}" = "{value}";')

        lines.append('')  # Trailing newline

        return '\n'.join(lines)

    def _create_file_with_translation(
        self,
        target_lang: str,
        target_name: str,
        source_lang: str,
        project_dir: Optional[Path] = None
    ) -> str:
        """
        Kaynak dilden otomatik çeviri yaparak localization dosyası oluştur.

        Args:
            target_lang: Hedef dil kodu
            target_name: Hedef dil adı
            source_lang: Kaynak dil kodu
            project_dir: Proje dizini (çeviri cache için)

        Returns:
            Çevrilmiş .strings dosya içeriği
        """
        # Create translator with cache
        cache_file = None
        if project_dir:
            cache_file = project_dir / '.localization_cache' / 'translations.json'

        translator = TranslationService(source_lang=source_lang, cache_file=cache_file)

        lines = [
            f'/*',
            f'  Localizable.strings ({target_name})',
            f'',
            f'  Created: {datetime.now().strftime("%Y-%m-%d")}',
            f'  Language: {target_name} ({target_lang})',
            f'  Auto-translated from: {source_lang}',
            f'',
            f'  NOTE: Auto-translated - please review for accuracy',
            f'*/',
            f''
        ]

        translated_count = 0
        failed_count = 0
        total_keys = len(self.file_manager.keys)

        # Add all keys with translations
        for i, (key, translations) in enumerate(self.file_manager.keys.items()):
            if source_lang in translations:
                source_value = translations[source_lang]

                # Translate
                translated = translator.translate(source_value, target_lang, source_lang)

                if translated:
                    # Escape quotes in translated value
                    escaped_value = translated.replace('"', '\\"')
                    lines.append(f'"{key}" = "{escaped_value}";')
                    translated_count += 1
                else:
                    # Fallback to source value
                    lines.append(f'"{key}" = "{source_value}";  // TODO: translate')
                    failed_count += 1

                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{total_keys} keys...")

        lines.append('')  # Trailing newline

        # Summary
        print(f"   ✅ Translated: {translated_count}")
        if failed_count > 0:
            print(f"   ⚠️  Failed (using source): {failed_count}")

        return '\n'.join(lines)

    def sync_all_languages(
        self,
        source_lang: str,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Sync all languages with source language.

        Adds missing keys from source to other languages.

        Args:
            source_lang: Source language code
            dry_run: Preview mode

        Returns:
            Dictionary of {lang_code: keys_added_count}
        """
        print(f"\n{Colors.bold(f'🔄 SYNCING LANGUAGES from {source_lang}')}")
        print("=" * 70)

        result = self.file_manager.sync_keys_across_languages(source_lang, dry_run)

        if dry_run:
            print(f"\n{Colors.info('[DRY RUN]')} Sync preview complete")
        else:
            print(f"\n{Colors.success('✅ Sync complete!')}")

        for lang, count in result.items():
            print(f"   {lang}: +{count} keys")

        return result
