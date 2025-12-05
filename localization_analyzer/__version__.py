"""Version information for localization-analyzer."""

__version__ = "1.13.1"
__author__ = "Sezgin Paksoy"
__description__ = "Professional localization analyzer for multi-platform projects"

# Changelog:
# 1.13.1 - Security fixes and improvements
#        - Fixed XSS vulnerability in HTML reporter (JSON injection)
#        - Fixed path traversal vulnerability in server (SecureHandler)
#        - Server now only allows access to the report file
#        - Added HTMLReporter to reports/__init__.py exports
#
# 1.13.0 - Interactive HTML Dashboard Report
#        - New HTMLReporter class with full-featured dashboard
#        - Dark/Light theme support with theme toggle
#        - Filterable and searchable data tables
#        - Collapsible sections for better navigation
#        - JSON export functionality from browser
#        - Pagination for large datasets
#        - Local HTTP server for serving reports (--serve flag)
#        - Auto-open in browser with --serve option
#        - ReportServer class for programmatic server control
#        - Context manager support for server lifecycle
#        - Added 45 new tests (22 HTML reporter, 23 server)
#
# 1.12.0 - Improved error handling across all modules
#        - Empty except:pass blocks replaced with proper error handling
#        - Multi-language character support (15+ languages)
#        - Turkish, German, French, Spanish, Portuguese, Polish, Czech,
#          Hungarian, Romanian, Swedish, Norwegian, Danish, Finnish supported
#        - Regex pattern caching for better performance
#        - Class-level compiled patterns (emoji, exclusion patterns)
#        - Extended common UI words list for better detection
#        - Added 16 new multi-language character tests
#        - Config validation system (framework, languages, paths, l10n)
#        - ConfigValidationError and ConfigValidationWarning classes
#        - All CLI commands now validate config before execution
#        - Language code validation (ISO 639-1 and locale variants)
#        - Added 24 new config validation tests
#        - Structured logging system (localization_analyzer.utils.logging)
#        - ColoredFormatter with ANSI color support
#        - File logging support with timestamps
#        - Verbose/quiet mode configuration
#        - Added 23 new logging tests
#        - Test coverage increased from 31% to 46% (148 new tests)
#        - Added comprehensive reporter tests (console, JSON)
#        - Added analyzer and file_manager tests
#        - Added health_calculator tests (99% coverage)
#        - Added swift_adapter tests (60% coverage)
#        - Total tests: 323 (was 155)
#        - Progress indicator utilities (localization_analyzer.utils.progress)
#        - tqdm integration for progress bars (optional dependency)
#        - Fallback to simple progress when tqdm not installed
#        - ProgressBar class with consistent API
#        - spinner() context manager for long operations
#        - Added 20 progress indicator tests
#
# 1.11.0 - Improved emoji filtering
#        - Pure emoji strings are no longer flagged as hardcoded
#        - Comprehensive Unicode emoji pattern support (all emoji ranges)
#        - Compound emoji support (ZWJ character emojis)
#        - Flag emoji support
#        - Emoji + text combinations are still detected
#        - Added 9 new emoji filtering tests
#
# 1.10.0 - Added modular .strings file support
#        - lang --add now creates modular files (AI.strings, Common.strings etc.)
#        - Fixed PosixPath TypeError (list vs single Path)
#        - Module-aware key writing system added
#        - Added module parameter to add_key method
#        - Added _find_module_file helper method
#        - list_languages now includes module_count info
#        - remove_language supports modular files
#        - Fixed bare except clause (analyzer.py)
#
# 1.9.3 - Fixed add_key method
#       - Now writes only to specified languages (not all)
#       - Removed "No translation" warning for other languages
#
# 1.9.2 - Fixed translate --force bug
#       - Added overwrite parameter to add_key method
#       - --force now updates existing keys
#       - Integrated write_localization_entry replace mode
#
# 1.9.1 - Fixed SSL certificate error
#       - SSL context support with certifi package
#       - Fixed macOS Python SSL issue
#
# 1.9.0 - Added sync command
#       - New 'sync' command: localization-analyzer sync --translate
#       - Auto-sync all languages with source language
#       - Detect and add missing keys
#       - Auto-translation integration (--translate flag)
#       - Backup support (before sync)
#       - Dry-run mode for preview
#       - JSON/Markdown report export
#       - CI/CD integration (--ci flag)
#       - Added 21 new tests
#
# 1.8.0 - Added diff command
#       - New 'diff' command: localization-analyzer diff --source en --target tr
#       - Show differences between two languages
#       - Detect missing, extra, translated and untranslated keys
#       - JSON, Markdown and TXT export
#       - Colored terminal output
#       - --fail-on-missing flag for CI/CD
#       - Added 17 new tests
#
# 1.7.0 - Added stats command
#       - New 'stats' command: localization-analyzer stats --missing
#       - Completion percentages per language
#       - Visual completion bar
#       - Missing translation details (--missing)
#       - JSON export (--json) - for CI/CD integration
#       - Markdown export (--markdown) - for reporting
#       - Threshold-based exit code (--ci --threshold 80)
#       - Added 18 new tests
#
# 1.6.0 - Added validate command
#       - New 'validate' command: localization-analyzer validate --consistency
#       - Syntax validation (missing semicolon, invalid escape)
#       - Key consistency check (missing keys across languages)
#       - Placeholder consistency (%@, %d count check)
#       - Duplicate key detection
#       - TODO comment detection
#       - Added 15 new tests
#
# 1.5.0 - New language addition + auto-translation integration
#       - lang --add --translate: Auto-translate when adding new language
#       - Added auto_translate parameter to LanguageManager
#       - Progress indicator during translation
#       - Source value + TODO comment on translation failure
#
# 1.4.0 - Dynamic table and module discovery
#       - New 'discover' command: localization-analyzer discover --all
#       - Auto-discover tables from .strings files (auto_discover_tables=True)
#       - Auto-detect module mapping from project structure
#       - Config defaults now empty (project-agnostic)
#       - --generate flag writes discovered values to config
#
# 1.3.0 - Improved Swift Table Name support
#       - Added 'tables' mapping to config (table -> .strings filename)
#       - Added 'use_localized_extension' option to config
#       - Added get_table_name() method to SwiftAdapter
#       - Added get_strings_file_path() method to SwiftAdapter
#       - Support for both .localized(from:) and L10n enum patterns
#
# 1.2.0 - Added auto-translation feature (Google Translate API)
#       - New 'translate' command: localization-analyzer translate --source en --target tr
#       - Translation caching (.localization_cache/translations.json)
#       - Translation preserves interpolation patterns (%@, \(var) etc.)
#       - 28+ language support
#       - missing --auto option now performs real translation
#
# 1.1.0 - Dynamic key filtering (interpolation patterns no longer shown as false positives)
#       - Dynamic keys reported in separate category
#       - Base pattern check added
