# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **IMPORTANT**: Bu dosya, projede önemli değişiklikler yapıldığında (yeni modül ekleme, mimari değişiklik, yeni komut ekleme, API değişikliği vb.) mutlaka güncellenmelidir. Claude Code oturumları bu dosyayı otomatik olarak güncel tutmalıdır.

## Project Overview

**localization-analyzer** is a professional CLI tool for localization analysis and management in multi-platform projects. Currently supports Swift/iOS with modular `.strings` files. Future support planned for React, Flutter, and Android.

## Commands

### Development Setup
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install optional features
pip install -e ".[watch,progress]"
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_validator.py

# Run with coverage
pytest --cov=localization_analyzer

# Run single test
pytest tests/test_validator.py::TestLocalizationValidator::test_validate_valid_file -v
```

### Code Quality
```bash
# Format code
black localization_analyzer tests

# Lint
flake8 localization_analyzer tests
```

### CLI Usage (after install)
```bash
localization-analyzer init --framework swift
localization-analyzer analyze --verbose
localization-analyzer stats
localization-analyzer validate --consistency
```

## Architecture

### Core Components

```
localization_analyzer/
├── cli.py              # CLI entry point - all commands defined here
├── core/               # Analysis engine
│   ├── analyzer.py     # LocalizationAnalyzer - main analysis orchestrator
│   ├── file_manager.py # LocalizationFileManager - file I/O operations
│   └── health_calculator.py # Health score calculation (0-100)
├── frameworks/         # Framework adapters (Strategy pattern)
│   ├── base.py         # BaseAdapter - abstract interface
│   └── swift.py        # SwiftAdapter - iOS/Swift implementation
├── features/           # Feature modules
│   ├── translator.py   # Google Translate integration (free, no API key)
│   ├── validator.py    # Syntax, placeholder, consistency validation
│   ├── stats.py        # Statistics calculation
│   ├── diff.py         # Language comparison
│   ├── sync.py         # Cross-language synchronization
│   ├── auto_fixer.py   # Auto-fix hardcoded strings
│   ├── language_manager.py # Add/remove/list languages
│   └── missing_keys_fixer.py # Fix missing keys
├── reports/            # Report generators
│   ├── console_reporter.py
│   └── json_reporter.py
└── utils/              # Utilities
    ├── config.py       # YAML config loading/saving
    ├── backup.py       # Backup creation before modifications
    ├── colors.py       # Terminal colors
    └── validators.py   # String validation helpers
```

### Key Design Patterns

**Framework Adapter Pattern**: `BaseAdapter` defines the interface; `SwiftAdapter` implements Swift-specific parsing and pattern detection. New frameworks extend `BaseAdapter`.

**Configuration**: Uses `.localization.yml` in project root. Template in `localization_analyzer/templates/.localization.yml`.

### Data Flow

1. `Config.from_file()` loads configuration
2. `SwiftAdapter` or other adapter created based on framework
3. `LocalizationAnalyzer` orchestrates analysis
4. `LocalizationFileManager` handles file operations
5. Feature modules (translator, validator, etc.) provide specific functionality
6. Reporters output results

### Key Classes

- `LocalizationAnalyzer`: Main entry point, coordinates analysis, detects hardcoded strings, missing keys, dead keys
- `LocalizationFileManager`: Loads/saves `.strings` files, manages keys across languages and modules
- `BaseAdapter`: Abstract interface - implement `get_file_extensions()`, `parse_localization_file()`, `write_localization_entry()`, `generate_localized_code()`
- `AnalysisResult`: Contains `health`, `hardcoded_strings`, `missing_keys`, `dead_keys`, `dynamic_keys`
- `HealthScore`: Score (0-100), grade (A-F), localization rate, issue counts

### Dynamic Key Detection

The analyzer intelligently skips false positives for dynamic keys containing interpolation:
- Swift: `"activity.\(id)"` - not flagged as missing if `activity.work`, `activity.friends` exist
- Supports patterns like `"style.\(rawValue).description"`

### Performance Optimizations

- **Pattern Caching**: Regex patterns are compiled once at class level (`_compiled_emoji_pattern`, `_compiled_exclusion_patterns`)
- **Character Map**: `CHAR_MAP` dictionary for O(1) character lookups during text-to-key conversion

### Multi-Language Support

The `text_to_key()` method supports special characters from 15+ languages:
- Turkish (ç, ğ, ı, ö, ş, ü)
- German (ä, ö, ü, ß)
- French (à, â, é, è, ê, ë, î, ï, ô, ù, û, ÿ, œ, æ)
- Spanish (á, é, í, ó, ú, ñ)
- Portuguese (ã, õ)
- Polish (ą, ć, ę, ł, ń, ś, ź, ż)
- Czech (č, ď, ě, ň, ř, ť, ů, ý, ž)
- Hungarian (ő, ű)
- Romanian (ă, â, î, ș, ț)
- Scandinavian (å, ø)

### PyPI Publishing

```bash
# Build
rm -rf dist/ build/ && python -m build

# Upload (token stored in pypi_token.txt - gitignored)
python -m twine upload dist/* --username __token__ --password $(cat pypi_token.txt)
```
