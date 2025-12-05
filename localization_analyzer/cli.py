"""Command-line interface for localization analyzer."""

import sys
import argparse
from pathlib import Path

from .__version__ import __version__
from .utils.colors import Colors
from .utils.config import Config, create_default_config, ConfigValidationError
from .utils.backup import create_backup
from .frameworks.swift import SwiftAdapter
from .core.analyzer import LocalizationAnalyzer
from .core.file_manager import LocalizationFileManager
from .features.auto_fixer import AutoFixer
from .features.language_manager import LanguageManager
from .features.missing_keys_fixer import MissingKeysFixer
from .features.l10n_generator import L10nGenerator
from .features.l10n_migrator import L10nMigrator
from .features.translator import TranslationService
from .features.validator import LocalizationValidator, ValidationResult
from .features.stats import StatsCalculator, ProjectStats
from .features.diff import LocalizationDiff, DiffResult
from .features.sync import LocalizationSync, SyncSummary
from .reports.json_reporter import JSONReporter
from .reports.console_reporter import ConsoleReporter
from .reports.html_reporter import HTMLReporter
from .utils.server import serve_report, ReportServer


def load_and_validate_config(validate: bool = True, verbose: bool = False) -> Config:
    """
    Load configuration and optionally validate it.

    Args:
        validate: Whether to validate the config
        verbose: Whether to print warnings

    Returns:
        Loaded Config object

    Raises:
        ConfigValidationError: If validation fails with errors
    """
    config = Config.from_file()

    if validate:
        errors, warnings = config.validate()

        # Print warnings if verbose
        if verbose and warnings:
            for warning in warnings:
                print(f"{Colors.warning('⚠️')}  Config warning: {warning}")

        # Raise on errors
        if errors:
            print(f"{Colors.error('❌')} Configuration errors:")
            for error in errors:
                print(f"   • {error}")
            raise ConfigValidationError(errors)

    return config


def cmd_init(args):
    """Initialize configuration file."""
    config_path = Path.cwd() / '.localization.yml'

    if config_path.exists() and not args.force:
        print(f"{Colors.error('❌')} Config already exists: {config_path}")
        print(f"   Use --force to overwrite")
        return 1

    config = create_default_config(args.framework)
    config.save(config_path)

    print(f"{Colors.success('✅')} Created: {config_path}")
    print(f"\n{Colors.bold('Next steps:')}")
    print(f"1. Edit .localization.yml to configure your project")
    print(f"2. Run: localization-analyzer analyze")

    return 0


def cmd_analyze(args):
    """Run analysis."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=args.verbose)
    except ConfigValidationError:
        return 1

    # Determine framework
    if args.framework:
        framework = args.framework
    else:
        framework = config.project.framework

    # Create adapter
    if framework == 'swift':
        adapter = SwiftAdapter(l10n_config=config.l10n)
    else:
        print(f"{Colors.error('❌')} Unsupported framework: {framework}")
        print(f"   Supported: swift")
        return 1

    # Setup paths
    project_dir = Path(config.paths.source)
    localization_dir = project_dir

    # Create analyzer
    analyzer = LocalizationAnalyzer(
        project_dir=project_dir,
        adapter=adapter,
        localization_dir=localization_dir,
        use_threads=not args.no_threads
    )

    # Run analysis
    result = analyzer.analyze(verbose=not args.quiet)

    # Generate reports
    if 'json' in config.reports.formats or args.json:
        JSONReporter.generate(
            result=result,
            file_manager=analyzer.file_manager,
            adapter=adapter,
            output_path=Path(config.reports.output) / 'report.json' if not args.json else Path(args.json)
        )

    if 'console' in config.reports.formats or args.verbose:
        ConsoleReporter.print_full_report(
            result=result,
            file_manager=analyzer.file_manager,
            show_details=args.verbose
        )

    # HTML report
    html_path = None
    if 'html' in config.reports.formats or args.html or args.serve:
        html_output = Path(args.html) if args.html else Path(config.reports.output) / 'report.html'
        html_path = HTMLReporter.generate(
            result=result,
            file_manager=analyzer.file_manager,
            adapter=adapter,
            output_path=html_output
        )

    # Serve HTML if requested
    if args.serve and html_path:
        serve_report(
            report_path=html_path,
            port=args.port,
            open_browser=not args.no_browser,
            blocking=True,
            editable=args.edit,
            localization_dir=Path(config.paths.localization) if args.edit else None,
            languages=config.languages.supported if args.edit else None
        )

    # Check threshold
    if args.fail_below and result.health.score < args.fail_below:
        print(f"\n{Colors.error('❌')} Health score below threshold: {result.health.score} < {args.fail_below}")
        return 1

    return 0


def cmd_fix(args):
    """Fix hardcoded strings."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)

    # Create analyzer
    analyzer = LocalizationAnalyzer(
        project_dir=project_dir,
        adapter=adapter,
    )

    # Run analysis
    result = analyzer.analyze(verbose=True)

    # Create backup
    if not args.no_backup and not args.dry_run:
        backup_dir = create_backup(
            source_dir=project_dir,
            include_patterns=['*.strings', '*.swift']
        )

    # Create auto-fixer
    fixer = AutoFixer(
        file_manager=analyzer.file_manager,
        adapter=adapter,
        dry_run=args.dry_run
    )

    # Filter strings by priority
    to_fix = [
        item for item in result.hardcoded_strings
        if item.priority >= args.min_priority
    ]

    print(f"\n{Colors.bold('⚡ AUTO-FIX MODE')}")
    print(f"Found {len(to_fix)} strings with priority >= {args.min_priority}")

    if args.dry_run:
        print(f"{Colors.info('[DRY RUN - No changes will be made]')}\n")

    # Fix strings
    for item in to_fix:
        fixer.fix_hardcoded_string(
            file_path=project_dir / item.file,
            line_num=item.line,
            original_text=item.text,
            component_type=item.component,
            suggested_key=item.suggested_key
        )

    fixer.print_summary()

    return 0


def cmd_missing(args):
    """Fix missing keys."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)

    # Create analyzer
    analyzer = LocalizationAnalyzer(
        project_dir=project_dir,
        adapter=adapter,
    )

    # Run analysis
    print(f"{Colors.bold('🔍 Analyzing project...')}")
    result = analyzer.analyze(verbose=False)

    if not result.missing_keys:
        print(f"\n{Colors.success('✅')} No missing keys found!")
        return 0

    # Create fixer
    fixer = MissingKeysFixer(
        file_manager=analyzer.file_manager,
        adapter=adapter,
        project_dir=project_dir,
        dry_run=args.dry_run
    )

    # Generate report if requested
    if args.report:
        report_path = Path(args.report)
        fixer.generate_missing_keys_report(result.missing_keys, report_path)

    # Fix missing keys
    if args.fix:
        # Create backup
        if not args.no_backup and not args.dry_run:
            create_backup(
                source_dir=project_dir,
                include_patterns=['*.strings']
            )

        # Fix
        fixer.fix_missing_keys(result.missing_keys, auto_translate=args.auto)
        fixer.print_summary()
    else:
        # Just show them
        print(f"\n{Colors.bold('🔴 MISSING KEYS')}")
        print("=" * 70)

        categories = fixer.analyze_and_categorize(result.missing_keys)
        for category, keys in sorted(categories.items()):
            print(f"\n{Colors.bold(category.upper())} ({len(keys)} keys):")
            for key in sorted(keys)[:10]:
                files = result.missing_keys[key]
                print(f"  • {key}")
                print(f"    Used in: {files[0]}")
            if len(keys) > 10:
                print(f"  ... and {len(keys) - 10} more")

        print(f"\n{Colors.info('💡 Tip:')} Use --fix to add these keys to localization files")
        print(f"         Use --report missing_keys.md to generate detailed report")

    return 0


def cmd_generate(args):
    """Generate L10n enum and .strings entries."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    if not config.l10n.enabled:
        print(f"{Colors.error('❌')} L10n is not enabled in config")
        print(f"   Add 'l10n.enabled: true' to .localization.yml")
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create analyzer
    analyzer = LocalizationAnalyzer(
        project_dir=project_dir,
        adapter=adapter,
    )

    # Run analysis
    print(f"{Colors.bold('🔍 Analyzing project...')}")
    result = analyzer.analyze(verbose=False)

    if not result.hardcoded_strings:
        print(f"\n{Colors.success('✅')} No hardcoded strings found!")
        return 0

    # Filter by priority
    to_process = [
        item for item in result.hardcoded_strings
        if item.priority >= args.min_priority
    ]

    print(f"Found {len(to_process)} strings with priority >= {args.min_priority}")

    # Create backup
    if not args.no_backup and not args.dry_run:
        create_backup(
            source_dir=resources_dir,
            include_patterns=['*.strings']
        )

    # Create generator
    generator = L10nGenerator(
        adapter=adapter,
        project_dir=project_dir,
        resources_dir=resources_dir,
        dry_run=args.dry_run
    )

    # Generate
    enum_code, count = generator.generate_all(
        to_process,
        languages=config.languages.supported
    )

    generator.print_summary()

    # Save enum code to file if requested
    if args.output and not args.dry_run:
        output_path = Path(args.output)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("// Auto-generated L10n entries\n")
                f.write("// Add these to your Localization.swift file\n\n")
                f.write(enum_code)
            print(f"\n{Colors.success('✅')} L10n code saved to: {output_path}")
        except Exception as e:
            print(f"{Colors.error('❌')} Error saving output: {e}")

    return 0


def cmd_migrate(args):
    """Migrate L10n enum patterns to .localized(from:) pattern."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Setup paths
    project_dir = Path(config.paths.source)

    # Create backup
    if not args.no_backup and not args.dry_run:
        from .utils.backup import create_backup
        backup_dir = create_backup(
            source_dir=project_dir,
            include_patterns=['*.swift']
        )
        print(f"{Colors.success('✅')} Backup created: {backup_dir}")

    # Create migrator
    migrator = L10nMigrator(
        project_dir=project_dir,
        dry_run=args.dry_run
    )

    # Run migration
    summary = migrator.migrate_all()

    # Show preview
    if args.preview or args.dry_run:
        migrator.print_preview(limit=args.limit)

    migrator.print_summary()

    return 0


def cmd_lang(args):
    """Manage languages."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup file manager
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'  # Updated path

    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    lang_manager = LanguageManager(file_manager, adapter, resources_dir)

    # List languages
    if args.list:
        languages = lang_manager.list_languages()

        print(f"\n{Colors.bold('🌍 AVAILABLE LANGUAGES')}")
        print("=" * 70)

        for lang in languages:
            status = Colors.success('✓') if lang['exists'] else Colors.error('✗')
            print(f"{status} {Colors.bold(lang['code'])} - {lang['name']}")
            print(f"   Keys: {lang['key_count']}, Missing: {lang['missing_keys']}, "
                  f"Completion: {lang['completion']:.1f}%")
            print()

        return 0

    # Add language
    if args.add:
        return 0 if lang_manager.add_language(
            lang_code=args.add,
            source_lang=args.source,
            empty=args.empty,
            dry_run=args.dry_run,
            auto_translate=args.translate,
            project_dir=project_dir
        ) else 1

    # Remove language
    if args.remove:
        return 0 if lang_manager.remove_language(
            lang_code=args.remove,
            dry_run=args.dry_run,
            confirm=args.confirm
        ) else 1

    # Sync languages
    if args.sync:
        lang_manager.sync_all_languages(
            source_lang=args.sync,
            dry_run=args.dry_run
        )
        return 0

    print(f"{Colors.warning('⚠️')}  No action specified. Use --list, --add, --remove, or --sync")
    return 1


def cmd_diff(args):
    """Compare two languages."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=args.verbose)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create file manager
    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    # Get language keys
    source_keys = file_manager.keys_by_language.get(args.source, {})
    target_keys = file_manager.keys_by_language.get(args.target, {})

    if not source_keys:
        print(f"{Colors.error('❌')} Source language not found: {args.source}")
        return 1

    if not target_keys:
        print(f"{Colors.error('❌')} Target language not found: {args.target}")
        return 1

    # Create diff calculator
    differ = LocalizationDiff()

    # Calculate diff
    result = differ.compare(
        source_keys=source_keys,
        target_keys=target_keys,
        source_lang=args.source,
        target_lang=args.target
    )

    # Export or print
    if args.output:
        output_path = Path(args.output)
        format = args.format or output_path.suffix.lstrip('.') or 'md'
        differ.export_diff(result, output_path, format=format)
    else:
        differ.print_diff(
            result,
            show_same=args.untranslated,
            show_values=args.verbose,
            limit=args.limit
        )

    # Exit code for CI
    if args.fail_on_missing and result.removed:
        return 1

    return 0


def cmd_sync(args):
    """Synchronize all languages with source language."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=args.verbose)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create file manager
    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    # Get source keys
    source_keys = file_manager.keys_by_language.get(args.source, {})

    if not source_keys:
        print(f"{Colors.error('❌')} No keys found in source language: {args.source}")
        return 1

    # Build target files dict
    target_files = {}
    for lang_code, file_paths in file_manager.languages.items():
        if lang_code == args.source:
            continue
        if isinstance(file_paths, list):
            target_files[lang_code] = file_paths[0]
        else:
            target_files[lang_code] = file_paths

    # Filter by specific language if requested
    if args.lang:
        if args.lang not in target_files:
            print(f"{Colors.error('❌')} Language not found: {args.lang}")
            return 1
        target_files = {args.lang: target_files[args.lang]}

    # Create sync manager
    syncer = LocalizationSync(
        source_lang=args.source,
        auto_translate=args.translate,
        backup=not args.no_backup
    )

    # Run sync
    summary = syncer.sync_all(
        source_keys=source_keys,
        target_files=target_files,
        target_keys=file_manager.keys_by_language,
        dry_run=args.dry_run
    )

    # Print summary
    syncer.print_summary(summary, verbose=args.verbose)

    # Export report if requested
    if args.output:
        output_path = Path(args.output)
        format = args.format or output_path.suffix.lstrip('.') or 'json'
        syncer.export_report(summary, output_path, format=format)

    # Exit code for CI
    if args.ci:
        return 0 if not summary.has_changes else (0 if summary.total_failures == 0 else 1)

    return 0


def cmd_stats(args):
    """Show localization statistics."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create file manager
    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    # Create stats calculator
    calculator = StatsCalculator(source_lang=args.source)

    # Calculate stats
    stats = calculator.calculate(
        keys_by_language=file_manager.keys_by_language,
        keys_by_table=getattr(file_manager, 'keys_by_table', None),
        project_name=config.project.name
    )

    # Print or export
    if args.json:
        output_path = Path(args.json)
        calculator.export_json(stats, output_path)
    elif args.markdown:
        output_path = Path(args.markdown)
        calculator.export_markdown(stats, output_path)
    else:
        calculator.print_summary(stats)

        # Show missing details if requested
        if args.missing:
            calculator.print_missing_details(stats, lang=args.lang)

    # JSON output for CI/CD
    if args.ci:
        print(stats.to_json())
        return 0 if stats.overall_completion >= args.threshold else 1

    return 0


def cmd_validate(args):
    """Validate localization files."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=args.verbose)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create file manager
    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    # Create validator
    validator = LocalizationValidator(source_lang=args.source)

    print(f"\n{Colors.bold('🔍 VALIDATING LOCALIZATION FILES')}")
    print("=" * 70)
    print(f"Source language: {args.source}")
    print(f"Resources: {resources_dir}")
    print()

    all_results = {}

    # Validate syntax for each file
    print(f"{Colors.bold('📋 SYNTAX VALIDATION')}")
    print("-" * 40)

    for lang_code, file_paths in file_manager.languages.items():
        for file_path in (file_paths if isinstance(file_paths, list) else [file_paths]):
            if file_path.exists():
                result = validator.validate_file(file_path)
                all_results[f"{lang_code}:{file_path.name}"] = result

                if result.total_issues == 0:
                    print(f"  {Colors.success('✓')} {lang_code}/{file_path.name}")
                else:
                    print(f"  {Colors.warning('!')} {lang_code}/{file_path.name}: {result.total_issues} issues")

    print()

    # Validate consistency
    if args.consistency:
        print(f"{Colors.bold('🔄 CONSISTENCY VALIDATION')}")
        print("-" * 40)

        # Get source keys
        source_keys = file_manager.keys_by_language.get(args.source, {})

        if source_keys:
            # Build files dict
            files_dict = {}
            for lang_code, file_paths in file_manager.languages.items():
                if isinstance(file_paths, list):
                    files_dict[lang_code] = file_paths[0]  # Use first file
                else:
                    files_dict[lang_code] = file_paths

            consistency_results = validator.validate_consistency(files_dict, source_keys)

            for lang, result in consistency_results.items():
                all_results[f"{lang}:consistency"] = result

            validator.print_results(consistency_results)
        else:
            print(f"  {Colors.warning('⚠️')}  No keys found in source language: {args.source}")

    # Print detailed results if verbose
    if args.verbose:
        print(f"\n{Colors.bold('📊 DETAILED RESULTS')}")
        print("-" * 40)
        validator.print_results(all_results)

    # Summary
    total_errors = sum(len(r.errors) for r in all_results.values())
    total_warnings = sum(len(r.warnings) for r in all_results.values())

    print(f"\n{'=' * 70}")
    print(f"{Colors.bold('📊 VALIDATION SUMMARY')}")
    print("=" * 70)
    print(f"Files checked: {len(all_results)}")
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors > 0:
        print(f"\n{Colors.error('❌ Validation FAILED')}")
        return 1
    elif total_warnings > 0:
        print(f"\n{Colors.warning('⚠️  Validation passed with warnings')}")
        return 0
    else:
        print(f"\n{Colors.success('✅ Validation PASSED')}")
        return 0


def cmd_discover(args):
    """Discover tables and modules from project structure."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=False)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    print(f"\n{Colors.bold('🔍 AUTO-DISCOVERY')}")
    print("=" * 70)
    print(f"Project: {project_dir}")
    print(f"Resources: {resources_dir}")
    print()

    # Discover tables
    if args.tables or args.all:
        print(f"{Colors.bold('📋 DISCOVERED TABLES')}")
        print("-" * 40)

        tables = adapter.discover_tables(resources_dir)

        if tables:
            for key, name in sorted(tables.items()):
                print(f"  {Colors.success('✓')} {key}: {name}.strings")

            # Show YAML config snippet
            print(f"\n{Colors.info('💡 Add to .localization.yml:')}")
            print("l10n:")
            print("  enabled: true")
            print("  tables:")
            for key, name in sorted(tables.items()):
                print(f"    {key}: {name}")
        else:
            print(f"  {Colors.warning('⚠️')}  No .strings files found")
        print()

    # Discover module mapping
    if args.modules or args.all:
        print(f"{Colors.bold('📁 DISCOVERED MODULES')}")
        print("-" * 40)

        modules = adapter.auto_detect_module_mapping(project_dir)

        if modules:
            for pattern, module in sorted(modules.items()):
                print(f"  {Colors.success('✓')} {pattern} → {module}")

            # Show YAML config snippet
            print(f"\n{Colors.info('💡 Add to .localization.yml:')}")
            print("l10n:")
            print("  enabled: true")
            print("  module_mapping:")
            for pattern, module in sorted(modules.items()):
                print(f"    {pattern}: {module}")
        else:
            print(f"  {Colors.warning('⚠️')}  No modules found")
        print()

    # Generate config if requested
    if args.generate:
        tables = adapter.discover_tables(resources_dir)
        modules = adapter.auto_detect_module_mapping(project_dir)

        # Update config
        if tables:
            config.l10n.tables = tables
        if modules:
            config.l10n.module_mapping = modules
        config.l10n.enabled = True

        # Save config
        config_path = Path.cwd() / '.localization.yml'
        config.save(config_path)

        print(f"{Colors.success('✅')} Config updated: {config_path}")

    return 0


def cmd_translate(args):
    """Translate localization files."""
    # Load and validate config
    try:
        config = load_and_validate_config(validate=True, verbose=args.verbose)
    except ConfigValidationError:
        return 1

    # Create adapter
    adapter = SwiftAdapter(l10n_config=config.l10n)

    # Setup paths
    project_dir = Path(config.paths.source)
    resources_dir = project_dir / 'Resources'

    # Create file manager
    file_manager = LocalizationFileManager(adapter, resources_dir)
    file_manager.load_all_keys()

    # Create translator
    cache_file = project_dir / '.localization_cache' / 'translations.json'
    translator = TranslationService(source_lang=args.source, cache_file=cache_file)

    print(f"\n{Colors.bold('🌍 AUTOMATIC TRANSLATION')}")
    print("=" * 70)
    print(f"Source language: {args.source}")
    print(f"Target language(s): {args.target or 'all'}")

    if args.dry_run:
        print(f"{Colors.info('[DRY RUN - No changes will be made]')}\n")

    # Get target languages
    if args.target:
        target_langs = [args.target]
    else:
        target_langs = [lang for lang in file_manager.languages.keys() if lang != args.source]

    if not target_langs:
        print(f"{Colors.warning('⚠️')}  No target languages found")
        return 1

    print(f"Languages to translate: {', '.join(target_langs)}")
    print()

    # Get keys to translate
    source_keys = file_manager.keys_by_language.get(args.source, {})

    if not source_keys:
        print(f"{Colors.error('❌')} No keys found in source language: {args.source}")
        return 1

    print(f"Keys to translate: {len(source_keys)}")

    translated_count = 0
    skipped_count = 0
    failed_count = 0

    for key, source_value in source_keys.items():
        if args.key and key != args.key:
            continue

        for target_lang in target_langs:
            # Check if already translated
            existing = file_manager.keys.get(key, {}).get(target_lang)
            if existing and not args.force:
                skipped_count += 1
                continue

            # Translate
            translated = translator.translate(source_value, target_lang, args.source)

            if translated:
                if args.verbose:
                    print(f"  {Colors.success('✓')} {key}")
                    print(f"    {args.source}: {source_value}")
                    print(f"    {target_lang}: {translated}")

                if not args.dry_run:
                    # Write to file (overwrite if --force flag is used)
                    file_manager.add_key(key, {target_lang: translated}, dry_run=False, overwrite=args.force)

                translated_count += 1
            else:
                failed_count += 1
                if args.verbose:
                    print(f"  {Colors.error('✗')} {key} - translation failed")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"{Colors.bold('📊 TRANSLATION SUMMARY')}")
    print("=" * 70)
    print(f"✅ Translated: {translated_count}")
    print(f"⏭️  Skipped (already exists): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print("=" * 70)

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='localization-analyzer',
        description='Professional localization analyzer for mobile and web projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # init command
    init_parser = subparsers.add_parser('init', help='Initialize configuration file')
    init_parser.add_argument('--framework', choices=['swift', 'react', 'flutter', 'android'],
                            default='swift', help='Framework type')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing config')

    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze localization')
    analyze_parser.add_argument('--framework', choices=['swift'], help='Override framework')
    analyze_parser.add_argument('--json', metavar='PATH', help='Output JSON report')
    analyze_parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    analyze_parser.add_argument('--quiet', action='store_true', help='Minimal output')
    analyze_parser.add_argument('--no-threads', action='store_true', help='Disable multi-threading')
    analyze_parser.add_argument('--fail-below', type=int, metavar='SCORE',
                               help='Exit with error if score below threshold')
    analyze_parser.add_argument('--html', metavar='PATH', help='Output HTML report')
    analyze_parser.add_argument('--serve', action='store_true',
                               help='Start local server and open HTML report in browser')
    analyze_parser.add_argument('--port', type=int, metavar='PORT',
                               help='Server port (default: auto)')
    analyze_parser.add_argument('--no-browser', action='store_true',
                               help='Do not open browser automatically')
    analyze_parser.add_argument('--edit', action='store_true',
                               help='Enable edit mode in HTML dashboard (with --serve)')

    # fix command
    fix_parser = subparsers.add_parser('fix', help='Auto-fix hardcoded strings')
    fix_parser.add_argument('--min-priority', type=int, default=8,
                           help='Minimum priority to fix (default: 8)')
    fix_parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    fix_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')

    # missing command
    missing_parser = subparsers.add_parser('missing', help='Fix missing localization keys')
    missing_parser.add_argument('--fix', action='store_true', help='Add missing keys to files')
    missing_parser.add_argument('--report', metavar='PATH', help='Generate detailed markdown report')
    missing_parser.add_argument('--auto', action='store_true', help='Auto-translate (experimental)')
    missing_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    missing_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')

    # generate command
    generate_parser = subparsers.add_parser('generate', help='Generate L10n enum and .strings entries')
    generate_parser.add_argument('--min-priority', type=int, default=5,
                                help='Minimum priority to process (default: 5)')
    generate_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    generate_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    generate_parser.add_argument('--output', '-o', metavar='PATH',
                                help='Save L10n enum code to file')

    # migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate L10n enums to .localized(from:)')
    migrate_parser.add_argument('--dry-run', action='store_true', help='Preview only, no changes')
    migrate_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    migrate_parser.add_argument('--preview', action='store_true', help='Show detailed preview')
    migrate_parser.add_argument('--limit', type=int, default=20, help='Limit preview items (default: 20)')

    # lang command
    lang_parser = subparsers.add_parser('lang', help='Manage languages')
    lang_parser.add_argument('--list', action='store_true', help='List all languages')
    lang_parser.add_argument('--add', metavar='CODE', help='Add new language')
    lang_parser.add_argument('--remove', metavar='CODE', help='Remove language')
    lang_parser.add_argument('--sync', metavar='CODE', help='Sync from source language')
    lang_parser.add_argument('--source', default='en', help='Source language (default: en)')
    lang_parser.add_argument('--empty', action='store_true', help='Create empty file')
    lang_parser.add_argument('--translate', '-t', action='store_true', help='Auto-translate from source language')
    lang_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    lang_parser.add_argument('--confirm', action='store_true', help='Confirm removal')

    # translate command
    translate_parser = subparsers.add_parser('translate', help='Automatically translate localization files')
    translate_parser.add_argument('--source', '-s', default='en', help='Source language (default: en)')
    translate_parser.add_argument('--target', '-t', metavar='CODE', help='Target language (default: all)')
    translate_parser.add_argument('--key', '-k', metavar='KEY', help='Translate specific key only')
    translate_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing translations')
    translate_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    translate_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    # discover command
    discover_parser = subparsers.add_parser('discover', help='Auto-discover tables and modules from project')
    discover_parser.add_argument('--tables', action='store_true', help='Discover .strings table files')
    discover_parser.add_argument('--modules', action='store_true', help='Discover module mappings from code structure')
    discover_parser.add_argument('--all', '-a', action='store_true', help='Discover both tables and modules')
    discover_parser.add_argument('--generate', '-g', action='store_true', help='Generate/update .localization.yml with discovered values')

    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate localization files')
    validate_parser.add_argument('--source', '-s', default='en', help='Source language (default: en)')
    validate_parser.add_argument('--consistency', '-c', action='store_true', help='Check cross-language consistency')
    validate_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    validate_parser.add_argument('--fail-on-warning', action='store_true', help='Exit with error on warnings')

    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show localization statistics')
    stats_parser.add_argument('--source', '-s', default='en', help='Source language (default: en)')
    stats_parser.add_argument('--json', metavar='PATH', help='Export stats as JSON')
    stats_parser.add_argument('--markdown', metavar='PATH', help='Export stats as Markdown')
    stats_parser.add_argument('--missing', '-m', action='store_true', help='Show missing translation details')
    stats_parser.add_argument('--lang', '-l', metavar='CODE', help='Filter by language code')
    stats_parser.add_argument('--ci', action='store_true', help='CI/CD mode (JSON output, exit code based on threshold)')
    stats_parser.add_argument('--threshold', type=float, default=80.0, help='Completion threshold for CI (default: 80)')

    # diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two languages')
    diff_parser.add_argument('--source', '-s', default='en', help='Source language (default: en)')
    diff_parser.add_argument('--target', '-t', required=True, help='Target language to compare')
    diff_parser.add_argument('--output', '-o', metavar='PATH', help='Export diff to file')
    diff_parser.add_argument('--format', '-f', choices=['md', 'json', 'txt'], help='Output format')
    diff_parser.add_argument('--untranslated', '-u', action='store_true', help='Show untranslated (same value) keys')
    diff_parser.add_argument('--verbose', '-v', action='store_true', help='Show values')
    diff_parser.add_argument('--limit', type=int, default=50, help='Max entries to show (default: 50)')
    diff_parser.add_argument('--fail-on-missing', action='store_true', help='Exit with error if missing keys found')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Synchronize all languages with source language')
    sync_parser.add_argument('--source', '-s', default='en', help='Source language (default: en)')
    sync_parser.add_argument('--lang', '-l', metavar='CODE', help='Sync only specific language')
    sync_parser.add_argument('--translate', '-t', action='store_true', help='Auto-translate missing keys')
    sync_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    sync_parser.add_argument('--dry-run', action='store_true', help='Preview only')
    sync_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    sync_parser.add_argument('--output', '-o', metavar='PATH', help='Export sync report to file')
    sync_parser.add_argument('--format', '-f', choices=['json', 'md'], help='Output format')
    sync_parser.add_argument('--ci', action='store_true', help='CI/CD mode')

    args = parser.parse_args()

    # Execute command
    if args.command == 'init':
        return cmd_init(args)
    elif args.command == 'analyze':
        return cmd_analyze(args)
    elif args.command == 'fix':
        return cmd_fix(args)
    elif args.command == 'missing':
        return cmd_missing(args)
    elif args.command == 'generate':
        return cmd_generate(args)
    elif args.command == 'migrate':
        return cmd_migrate(args)
    elif args.command == 'lang':
        return cmd_lang(args)
    elif args.command == 'translate':
        return cmd_translate(args)
    elif args.command == 'discover':
        return cmd_discover(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'stats':
        return cmd_stats(args)
    elif args.command == 'diff':
        return cmd_diff(args)
    elif args.command == 'sync':
        return cmd_sync(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
