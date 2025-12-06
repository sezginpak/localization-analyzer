"""Feature modules."""

from .auto_fixer import AutoFixer
from .dynamic_key_analyzer import DynamicKeyAnalyzer
from .language_manager import LanguageManager
from .missing_keys_fixer import MissingKeysFixer
from .translator import TranslationService, translate_key_value
from .validator import LocalizationValidator
from .stats import StatsCalculator
from .diff import LocalizationDiff
from .sync import LocalizationSync

__all__ = [
    'AutoFixer',
    'DynamicKeyAnalyzer',
    'LanguageManager',
    'MissingKeysFixer',
    'TranslationService',
    'translate_key_value',
    'LocalizationValidator',
    'StatsCalculator',
    'LocalizationDiff',
    'LocalizationSync',
]
