"""
Localization Analyzer
=====================

Professional localization analysis tool for mobile and web applications.
Supports Swift/iOS, React, Flutter, and Android projects.

Usage:
    from localization_analyzer import LocalizationAnalyzer

    analyzer = LocalizationAnalyzer(project_dir='./my-project')
    results = analyzer.analyze()
    print(f"Localization coverage: {results.coverage}%")

CLI:
    localization-analyzer analyze
    localization-analyzer fix --interactive
    localization-analyzer lang add es
"""

from .__version__ import __version__, __author__, __description__

# Core exports
from .core.analyzer import LocalizationAnalyzer
from .core.file_manager import LocalizationFileManager
from .core.health_calculator import HealthCalculator

# Framework adapters
from .frameworks.swift import SwiftAdapter
from .frameworks.base import BaseAdapter

# Features
from .features.auto_fixer import AutoFixer
from .features.language_manager import LanguageManager

__all__ = [
    '__version__',
    '__author__',
    '__description__',
    'LocalizationAnalyzer',
    'LocalizationFileManager',
    'HealthCalculator',
    'SwiftAdapter',
    'BaseAdapter',
    'AutoFixer',
    'LanguageManager',
]
