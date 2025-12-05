"""Framework adapters for different platforms."""

from .base import BaseAdapter, LocalizationPattern, HardcodedString, LocalizedUsage
from .swift import SwiftAdapter

__all__ = [
    'BaseAdapter',
    'LocalizationPattern',
    'HardcodedString',
    'LocalizedUsage',
    'SwiftAdapter',
]
