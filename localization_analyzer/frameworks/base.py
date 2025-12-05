"""Base adapter interface for different frameworks."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class LocalizationPattern:
    """Represents a localization pattern."""
    pattern: str  # Regex pattern
    component_type: str  # UI component type
    category: str  # Category for priority calculation


@dataclass
class HardcodedString:
    """Represents a hardcoded string found in code."""
    file: str
    line: int
    text: str
    component: str
    category: str
    priority: int
    suggested_key: str


@dataclass
class LocalizedUsage:
    """Represents a localized string usage."""
    file: str
    line: int
    key: str
    component: str


class BaseAdapter(ABC):
    """Base adapter for framework-specific localization handling."""

    def __init__(self):
        self.hardcoded_patterns: List[LocalizationPattern] = []
        self.localized_patterns: List[LocalizationPattern] = []
        self.exclude_patterns: List[str] = []
        self.priority_weights: Dict[str, int] = {
            'visible_ui': 10,
            'user_facing': 8,
            'error_messages': 9,
            'navigation': 7,
            'labels': 6,
            'placeholders': 5,
            'internal': 2,
        }

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return list of file extensions to analyze (e.g., ['.swift', '.m'])."""
        pass

    @abstractmethod
    def get_localization_file_pattern(self) -> str:
        """Return glob pattern for localization files (e.g., '*.lproj/Localizable.strings')."""
        pass

    @abstractmethod
    def parse_localization_file(self, file_path: Path) -> Dict[str, str]:
        """
        Parse localization file and return key-value pairs.

        Args:
            file_path: Path to localization file

        Returns:
            Dictionary of key-value pairs
        """
        pass

    @abstractmethod
    def write_localization_entry(
        self,
        file_path: Path,
        key: str,
        value: str,
        append: bool = True
    ) -> bool:
        """
        Write a localization entry to file.

        Args:
            file_path: Path to localization file
            key: Localization key
            value: Localized text
            append: Whether to append (True) or replace (False)

        Returns:
            Success status
        """
        pass

    @abstractmethod
    def generate_localized_code(self, key: str, component_type: str) -> str:
        """
        Generate code for using localized string.

        Args:
            key: Localization key
            component_type: UI component type

        Returns:
            Code snippet for localized string
        """
        pass

    def calculate_priority(self, component_type: str, category: str, text: str) -> int:
        """
        Calculate priority score for a hardcoded string.

        Args:
            component_type: UI component type
            category: String category
            text: The actual text

        Returns:
            Priority score (0-10), 0 means skip
        """
        import re

        # Skip emoji-only strings
        emoji_pattern = re.compile(
            r'[\U0001F300-\U0001F9FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF'
            r'\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF'
            r'\U0001F1E0-\U0001F1FF\U00002300-\U000023FF\U0000FE00-\U0000FE0F'
            r'\U0001F900-\U0001F9FF]+'
        )
        text_without_emoji = emoji_pattern.sub('', text.strip())
        if not text_without_emoji:
            return 0  # Pure emoji - skip

        # Skip very short strings that are likely symbols
        if len(text.strip()) <= 2:
            return 0

        base_score = self.priority_weights.get(category, 5)

        # Boost priority for short strings (easier to fix)
        if len(text) < 20:
            base_score += 2

        # Boost priority for error/warning/success messages
        if any(word in text.lower() for word in ['error', 'warning', 'failed', 'success']):
            base_score += 3

        # Boost priority for user-facing components
        if component_type in ['Button', 'Label', 'Menu', 'Alert']:
            base_score += 2

        return min(10, base_score)

    def suggest_key_name(self, text: str, component_type: str) -> str:
        """
        Suggest a localization key name.

        Args:
            text: Original text
            component_type: UI component type

        Returns:
            Suggested key name
        """
        import re

        # Clean text
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()[:4]

        # Determine prefix
        prefix_map = {
            'Button': 'button',
            'Label': 'label',
            'Text': 'text',
            'NavigationTitle': 'nav',
            'Alert': 'alert',
            'TextField': 'placeholder',
            'Menu': 'menu',
            'Section': 'section',
        }

        prefix = prefix_map.get(component_type, 'common')

        # Build key
        key_parts = [prefix] + words
        return '.'.join(key_parts)

    def should_exclude_file(self, file_path: Path) -> bool:
        """
        Check if file should be excluded from analysis.

        Args:
            file_path: File path to check

        Returns:
            True if file should be excluded
        """
        exclude_dirs = {
            'build', 'Build', 'DerivedData', '.build',
            'Pods', 'Carthage', 'vendor', '.git',
            'node_modules', 'dist', 'coverage',
        }

        # Check if any excluded directory in path
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            return True

        # Check if generated file
        if 'Generated' in str(file_path) or 'generated' in file_path.name:
            return True

        return False
