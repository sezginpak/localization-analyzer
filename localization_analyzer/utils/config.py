"""Configuration management for localization analyzer."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    """Project configuration."""
    name: str = "Unnamed Project"
    framework: str = "swift"  # swift | react | flutter | android


@dataclass
class PathsConfig:
    """Paths configuration."""
    source: str = "."
    localization: str = ""
    exclude: List[str] = field(default_factory=lambda: [
        'build/', '.build/', 'DerivedData/', 'Pods/',
        'Carthage/', 'vendor/', '.git/', 'node_modules/'
    ])


@dataclass
class LanguagesConfig:
    """Languages configuration."""
    primary: str = "en"
    supported: List[str] = field(default_factory=lambda: ["en"])


@dataclass
class PatternsConfig:
    """Pattern configuration."""
    hardcoded: List[str] = field(default_factory=list)
    localized: List[str] = field(default_factory=list)


@dataclass
class AutoFixConfig:
    """Auto-fix configuration."""
    enabled: bool = False
    min_priority: int = 8
    backup: bool = True


@dataclass
class L10nConfig:
    """L10n pattern configuration for Swift projects."""
    enabled: bool = False
    enum_name: str = "L10n"  # The name of L10n enum (e.g., L10n, Strings, etc.)
    # Module mapping: maps file path patterns to L10n categories
    # Empty by default - will be auto-discovered or configured per project
    module_mapping: Dict[str, str] = field(default_factory=dict)
    # Default module for strings that don't match any pattern
    default_module: str = "Common"
    # Table configuration for Swift .strings files
    # Maps table names to .strings file names (without .strings extension)
    # Empty by default - will be auto-discovered from .strings files
    tables: Dict[str, str] = field(default_factory=dict)
    # Use .localized(from:) pattern instead of L10n enum
    use_localized_extension: bool = True
    # Auto-discover tables from .strings files in Resources directory
    auto_discover_tables: bool = True


@dataclass
class ReportsConfig:
    """Reports configuration."""
    formats: List[str] = field(default_factory=lambda: ["json", "console"])
    output: str = "./localization_reports/"


@dataclass
class Config:
    """Main configuration class."""
    project: ProjectConfig = field(default_factory=ProjectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    languages: LanguagesConfig = field(default_factory=LanguagesConfig)
    patterns: PatternsConfig = field(default_factory=PatternsConfig)
    auto_fix: AutoFixConfig = field(default_factory=AutoFixConfig)
    reports: ReportsConfig = field(default_factory=ReportsConfig)
    l10n: L10nConfig = field(default_factory=L10nConfig)

    @classmethod
    def from_file(cls, config_path: Optional[Path] = None) -> 'Config':
        """Load configuration from YAML file."""
        if config_path is None:
            # Look for .localization.yml in current directory
            config_path = Path.cwd() / '.localization.yml'

            if not config_path.exists():
                # Return default config
                return cls()

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return cls(
            project=ProjectConfig(**data.get('project', {})),
            paths=PathsConfig(**data.get('paths', {})),
            languages=LanguagesConfig(**data.get('languages', {})),
            patterns=PatternsConfig(**data.get('patterns', {})),
            auto_fix=AutoFixConfig(**data.get('auto_fix', {})),
            reports=ReportsConfig(**data.get('reports', {})),
            l10n=L10nConfig(**data.get('l10n', {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'project': {
                'name': self.project.name,
                'framework': self.project.framework,
            },
            'paths': {
                'source': self.paths.source,
                'localization': self.paths.localization,
                'exclude': self.paths.exclude,
            },
            'languages': {
                'primary': self.languages.primary,
                'supported': self.languages.supported,
            },
            'patterns': {
                'hardcoded': self.patterns.hardcoded,
                'localized': self.patterns.localized,
            },
            'auto_fix': {
                'enabled': self.auto_fix.enabled,
                'min_priority': self.auto_fix.min_priority,
                'backup': self.auto_fix.backup,
            },
            'reports': {
                'formats': self.reports.formats,
                'output': self.reports.output,
            },
            'l10n': {
                'enabled': self.l10n.enabled,
                'enum_name': self.l10n.enum_name,
                'module_mapping': self.l10n.module_mapping,
                'default_module': self.l10n.default_module,
                'tables': self.l10n.tables,
                'use_localized_extension': self.l10n.use_localized_extension,
                'auto_discover_tables': self.l10n.auto_discover_tables,
            },
        }

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to YAML file."""
        if config_path is None:
            config_path = Path.cwd() / '.localization.yml'

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def create_default_config(framework: str = 'swift') -> Config:
    """Create default configuration for a framework."""
    config = Config()
    config.project.framework = framework

    # Framework-specific defaults
    if framework == 'swift':
        config.paths.localization = './*/Resources/*.lproj/Localizable.strings'
    elif framework == 'react':
        config.paths.localization = './src/locales/*/*.json'
    elif framework == 'flutter':
        config.paths.localization = './lib/l10n/*.arb'
    elif framework == 'android':
        config.paths.localization = './res/values*/strings.xml'

    return config
