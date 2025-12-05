# Localization Analyzer

🌍 Professional localization analysis and management tool for multi-platform projects.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.10.0-brightgreen.svg)](https://github.com/sezginpak/localization-analyzer)

## Why localization-analyzer?

Unlike other tools that only handle one aspect of localization, this is an **all-in-one CLI** that covers the entire localization workflow:

| Feature | localization-analyzer | BartyCrouch | translate-toolkit |
|---------|:--------------------:|:-----------:|:-----------------:|
| Analyze hardcoded strings | ✅ | ✅ | ❌ |
| Auto-translate | ✅ | ✅ | ✅ |
| Modular .strings support | ✅ | ❌ | ❌ |
| Health scoring | ✅ | ❌ | ❌ |
| Dynamic key detection | ✅ | ❌ | ❌ |
| Stats & reporting | ✅ | ❌ | ✅ |
| Diff between languages | ✅ | ❌ | ✅ |
| Validation | ✅ | ❌ | ✅ |
| Sync languages | ✅ | ✅ | ✅ |

## Features

### Analysis & Detection
- 🔍 **Smart Detection**: Find hardcoded strings automatically
- 🎯 **Dynamic Key Detection**: Skip false positives like `activity.\(id)`
- 📊 **Health Score**: Track localization quality (0-100)
- 🔑 **Key Management**: Detect missing and dead keys

### Translation & Management
- 🌍 **Auto-Translate**: Google Translate integration (free, no API key)
- 📦 **Modular Support**: Handle AI.strings, Common.strings, etc.
- ➕ **Add Languages**: Create new language with auto-translation
- 🔄 **Sync**: Keep all languages in sync

### Validation & Reporting
- ✅ **Validate**: Check syntax, placeholders, duplicates
- 📈 **Stats**: Completion percentages per language
- 🔀 **Diff**: Compare two languages
- 📋 **Reports**: JSON, Markdown, Console output

### Developer Experience
- ⚡ **Fast**: Multi-threaded analysis
- 💾 **Cache**: Translation caching for speed
- 🔧 **Auto-Fix**: Automatically fix hardcoded strings
- 🔄 **CI/CD Ready**: Exit codes for pipeline integration

## Installation

### From PyPI (recommended)

```bash
pip install localization-analyzer
```

### From Source

```bash
git clone https://github.com/sezginpak/localization-analyzer.git
cd localization-analyzer
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
cd your-project
localization-analyzer init --framework swift
```

This creates `.localization.yml` in your project root.

### 2. Run Analysis

```bash
localization-analyzer analyze --verbose
```

### 3. Check Statistics

```bash
# View completion stats for all languages
localization-analyzer stats

# Show missing keys per language
localization-analyzer stats --missing

# Export as JSON for CI/CD
localization-analyzer stats --json
```

### 4. Add New Language with Translation

```bash
# Add Spanish with auto-translation from English
localization-analyzer lang --add es --translate

# Preview first (dry-run)
localization-analyzer lang --add es --translate --dry-run
```

### 5. Translate Missing Keys

```bash
# Translate missing keys from English to German
localization-analyzer translate --source en --target de

# Force re-translate all keys
localization-analyzer translate --source en --target de --force
```

### 6. Sync Languages

```bash
# Sync all languages with English (source)
localization-analyzer sync --translate

# Sync specific language
localization-analyzer sync --lang de --translate
```

### 7. Compare Languages

```bash
# Diff between English and Spanish
localization-analyzer diff --source en --target es

# Fail if missing keys (for CI)
localization-analyzer diff --source en --target es --fail-on-missing
```

### 8. Validate Files

```bash
# Full validation
localization-analyzer validate --consistency

# Check specific aspects
localization-analyzer validate --syntax
localization-analyzer validate --placeholders
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `init` | Initialize configuration file |
| `analyze` | Run comprehensive analysis |
| `stats` | Show localization statistics |
| `translate` | Auto-translate keys |
| `lang` | Manage languages (add/remove/list/sync) |
| `sync` | Synchronize all languages |
| `diff` | Compare two languages |
| `validate` | Validate localization files |
| `missing` | Find and fix missing keys |
| `fix` | Auto-fix hardcoded strings |
| `generate` | Generate L10n enum |
| `discover` | Auto-discover tables/modules |

## Configuration

Create `.localization.yml` in your project root:

```yaml
project:
  name: MyApp
  framework: swift

paths:
  source: .
  localization: ./Resources
  exclude:
    - build/
    - Pods/
    - .build/

languages:
  primary: en
  supported:
    - en
    - es
    - de
    - tr
    - pt

# Optional: Module mapping
tables:
  AI: AI
  Common: Common
  Garden: Garden

auto_fix:
  enabled: true
  min_priority: 8
  backup: true

reports:
  formats:
    - json
    - console
  output: ./localization_reports/
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Localization Check

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install localization-analyzer
        run: pip install localization-analyzer

      - name: Check localization health
        run: localization-analyzer analyze --fail-below 90

      - name: Validate syntax
        run: localization-analyzer validate --syntax

      - name: Check missing translations
        run: localization-analyzer stats --ci --threshold 95
```

### GitLab CI

```yaml
localization:
  image: python:3.11
  script:
    - pip install localization-analyzer
    - localization-analyzer analyze --fail-below 90
    - localization-analyzer validate --consistency
```

## Python API

```python
from localization_analyzer import LocalizationAnalyzer
from localization_analyzer.frameworks import SwiftAdapter
from localization_analyzer.core.file_manager import LocalizationFileManager
from pathlib import Path

# Create analyzer
adapter = SwiftAdapter()
analyzer = LocalizationAnalyzer(
    project_dir=Path('.'),
    adapter=adapter
)

# Run analysis
result = analyzer.analyze()

# Check results
print(f"Health Score: {result.health.score}/100")
print(f"Localization Rate: {result.health.localization_rate}%")
print(f"Hardcoded Strings: {len(result.hardcoded_strings)}")

# File manager for direct key management
file_manager = LocalizationFileManager(adapter, Path('./Resources'))
file_manager.load_all_keys()

# Add a key to specific module
file_manager.add_key(
    key="new.feature.title",
    translations={"en": "New Feature", "es": "Nueva Función"},
    module="Common"
)
```

## Supported Frameworks

| Framework | Status | File Format |
|-----------|--------|-------------|
| Swift/iOS | ✅ Full Support | `.strings` (modular) |
| React | 🚧 Coming Soon | `.json` |
| Flutter | 🚧 Coming Soon | `.arb` |
| Android | 🚧 Coming Soon | `.xml` |

## Key Features Explained

### Health Score (0-100)

Calculated based on:
- **Localization Rate**: % of localized vs hardcoded strings
- **Missing Keys**: Keys used in code but not in files
- **Dead Keys**: Keys in files but not used in code
- **Consistency**: Same keys across all languages

### Dynamic Key Detection

Smart detection skips false positives:
```swift
// These won't be flagged as missing:
"activity.\(id)".localized      // Dynamic key
"style.\(rawValue)".localized   // Dynamic key
```

### Modular .strings Support

Works with modern Swift projects:
```
Resources/
├── en.lproj/
│   ├── AI.strings
│   ├── Common.strings
│   ├── Garden.strings
│   └── Settings.strings
└── es.lproj/
    ├── AI.strings
    ├── Common.strings
    └── ...
```

### Translation Caching

Translations are cached to avoid re-translating:
```
.localization_cache/
└── translations.json
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/sezginpak/localization-analyzer.git
cd localization-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Project Structure

```
localization-analyzer/
├── localization_analyzer/
│   ├── core/              # Analysis engine
│   │   ├── analyzer.py    # Main analyzer
│   │   └── file_manager.py # File I/O
│   ├── frameworks/        # Framework adapters
│   │   └── swift.py       # Swift/iOS adapter
│   ├── features/          # Feature modules
│   │   ├── translator.py  # Auto-translation
│   │   ├── validator.py   # Validation
│   │   ├── stats.py       # Statistics
│   │   ├── diff.py        # Language diff
│   │   └── sync.py        # Sync languages
│   ├── reports/           # Report generators
│   └── utils/             # Utilities
├── tests/                 # Test suite (40+ tests)
└── examples/              # Example projects
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Sezgin Paksoy**
- GitHub: [@sezginpak](https://github.com/sezginpak)

## Support

- 🐛 Issues: [GitHub Issues](https://github.com/sezginpak/localization-analyzer/issues)
- 📖 Docs: [Documentation](https://github.com/sezginpak/localization-analyzer#readme)

---

Made with ❤️ for the iOS/Swift developer community
