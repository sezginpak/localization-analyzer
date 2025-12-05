"""Swift/iOS framework adapter for localization analysis."""

import re
from pathlib import Path
from typing import Dict, List

from .base import BaseAdapter, LocalizationPattern


class SwiftAdapter(BaseAdapter):
    """Adapter for Swift/iOS projects using .strings files."""

    # Class-level compiled pattern cache for performance
    _compiled_hardcoded_patterns = None
    _compiled_localized_patterns = None
    _compiled_exclusion_patterns = None
    _compiled_emoji_pattern = None

    def __init__(self, l10n_config=None):
        super().__init__()
        self.l10n_config = l10n_config
        self._discovered_tables = {}  # Cache for discovered tables

        # Swift-specific hardcoded patterns
        self.hardcoded_patterns = [
            # Basic UI Components
            LocalizationPattern(
                pattern=r'Text\(\s*"([^"]+)"\s*\)',
                component_type='Text',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Label\(\s*"([^"]+)"',
                component_type='Label',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Button\(\s*"([^"]+)"',
                component_type='Button',
                category='visible_ui'
            ),

            # Navigation
            LocalizationPattern(
                pattern=r'\.navigationTitle\(\s*"([^"]+)"\s*\)',
                component_type='NavigationTitle',
                category='navigation'
            ),
            LocalizationPattern(
                pattern=r'\.navigationBarTitle\(\s*"([^"]+)"\s*\)',
                component_type='NavigationBarTitle',
                category='navigation'
            ),

            # Alerts and Dialogs
            LocalizationPattern(
                pattern=r'Alert\([^)]*title:\s*Text\(\s*"([^"]+)"\s*\)',
                component_type='Alert',
                category='error_messages'
            ),
            LocalizationPattern(
                pattern=r'Alert\(\s*"([^"]+)"',
                component_type='Alert',
                category='error_messages'
            ),
            LocalizationPattern(
                pattern=r'\.confirmationDialog\(\s*"([^"]+)"',
                component_type='ConfirmationDialog',
                category='user_facing'
            ),

            # Form Elements
            LocalizationPattern(
                pattern=r'TextField\(\s*"([^"]+)"',
                component_type='TextField',
                category='placeholders'
            ),
            LocalizationPattern(
                pattern=r'SecureField\(\s*"([^"]+)"',
                component_type='SecureField',
                category='placeholders'
            ),
            LocalizationPattern(
                pattern=r'Toggle\(\s*"([^"]+)"',
                component_type='Toggle',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Picker\(\s*"([^"]+)"',
                component_type='Picker',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Stepper\(\s*"([^"]+)"',
                component_type='Stepper',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Slider\(\s*value:[^,]+,\s*label:\s*\{\s*Text\(\s*"([^"]+)"\s*\)',
                component_type='Slider',
                category='visible_ui'
            ),

            # Containers and Groups
            LocalizationPattern(
                pattern=r'Menu\(\s*"([^"]+)"',
                component_type='Menu',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Section\(\s*"([^"]+)"',
                component_type='Section',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'Section\(\s*header:\s*Text\(\s*"([^"]+)"\s*\)',
                component_type='Section',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'GroupBox\(\s*"([^"]+)"',
                component_type='GroupBox',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'DisclosureGroup\(\s*"([^"]+)"',
                component_type='DisclosureGroup',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'LabeledContent\(\s*"([^"]+)"',
                component_type='LabeledContent',
                category='labels'
            ),

            # Links and Navigation
            LocalizationPattern(
                pattern=r'Link\(\s*"([^"]+)"',
                component_type='Link',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'NavigationLink\(\s*"([^"]+)"',
                component_type='NavigationLink',
                category='visible_ui'
            ),

            # Modifiers
            LocalizationPattern(
                pattern=r'\.accessibilityLabel\(\s*"([^"]+)"\s*\)',
                component_type='AccessibilityLabel',
                category='user_facing'
            ),
            LocalizationPattern(
                pattern=r'\.placeholder\(\s*"([^"]+)"\s*\)',
                component_type='Placeholder',
                category='placeholders'
            ),
            LocalizationPattern(
                pattern=r'\.help\(\s*"([^"]+)"\s*\)',
                component_type='Help',
                category='user_facing'
            ),
            LocalizationPattern(
                pattern=r'\.badge\(\s*"([^"]+)"\s*\)',
                component_type='Badge',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'\.badge\(\s*Text\(\s*"([^"]+)"\s*\)\s*\)',
                component_type='Badge',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'\.searchPrompt\(\s*"([^"]+)"\s*\)',
                component_type='SearchPrompt',
                category='placeholders'
            ),
            LocalizationPattern(
                pattern=r'\.prompt\(\s*"([^"]+)"\s*\)',
                component_type='Prompt',
                category='placeholders'
            ),

            # Tab Items
            LocalizationPattern(
                pattern=r'\.tabItem\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='TabItem',
                category='navigation'
            ),

            # Toolbar
            LocalizationPattern(
                pattern=r'ToolbarItem\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='ToolbarItem',
                category='visible_ui'
            ),

            # Context Menu
            LocalizationPattern(
                pattern=r'\.contextMenu\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='ContextMenu',
                category='visible_ui'
            ),

            # Swipe Actions
            LocalizationPattern(
                pattern=r'\.swipeActions\s*\{[^}]*Button\(\s*"([^"]+)"',
                component_type='SwipeAction',
                category='visible_ui'
            ),

            # Sheets and Presentations
            LocalizationPattern(
                pattern=r'\.sheet\([^)]*\)\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='Sheet',
                category='visible_ui'
            ),
            LocalizationPattern(
                pattern=r'\.popover\([^)]*\)\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='Popover',
                category='visible_ui'
            ),

            # Empty States
            LocalizationPattern(
                pattern=r'ContentUnavailableView\(\s*"([^"]+)"',
                component_type='EmptyState',
                category='visible_ui'
            ),

            # Form Labels
            LocalizationPattern(
                pattern=r'Form\s*\{[^}]*Section\([^)]*header:\s*Text\(\s*"([^"]+)"\s*\)',
                component_type='FormSection',
                category='visible_ui'
            ),

            # List Section Headers
            LocalizationPattern(
                pattern=r'List\s*\{[^}]*Section\(\s*"([^"]+)"',
                component_type='ListSection',
                category='visible_ui'
            ),

            # Error Messages in Views
            LocalizationPattern(
                pattern=r'if\s+.*error.*Text\(\s*"([^"]+)"\s*\)',
                component_type='ErrorMessage',
                category='error_messages'
            ),

            # Toast/Banner Messages
            LocalizationPattern(
                pattern=r'\.toast\(\s*"([^"]+)"',
                component_type='Toast',
                category='user_facing'
            ),
            LocalizationPattern(
                pattern=r'\.banner\(\s*"([^"]+)"',
                component_type='Banner',
                category='user_facing'
            ),

            # Overlay Messages
            LocalizationPattern(
                pattern=r'\.overlay\([^)]*\)\s*\{[^}]*Text\(\s*"([^"]+)"\s*\)',
                component_type='Overlay',
                category='visible_ui'
            ),

            # Custom Notification Content
            LocalizationPattern(
                pattern=r'UNMutableNotificationContent\(\)\.title\s*=\s*"([^"]+)"',
                component_type='NotificationTitle',
                category='user_facing'
            ),
            LocalizationPattern(
                pattern=r'UNMutableNotificationContent\(\)\.body\s*=\s*"([^"]+)"',
                component_type='NotificationBody',
                category='user_facing'
            ),

            # Enum Cases - Switch Return Statements
            LocalizationPattern(
                pattern=r'case\s+\.\w+:\s*return\s+"([^"]+)"',
                component_type='EnumCase',
                category='enum_localization'
            ),

            # Switch-Case Numeric Range Returns (e.g., mood emojis, status messages)
            LocalizationPattern(
                pattern=r'case\s+\d+(?:\.\.<|\.\.\.)\d+:\s*return\s+"([^"]+)"',
                component_type='SwitchCaseRange',
                category='user_facing'
            ),

            # Switch-Case Simple Numeric Returns
            LocalizationPattern(
                pattern=r'case\s+\d+:\s*return\s+"([^"]+)"',
                component_type='SwitchCaseNumeric',
                category='user_facing'
            ),

            # Default Case Returns
            LocalizationPattern(
                pattern=r'default:\s*return\s+"([^"]+)"',
                component_type='DefaultCase',
                category='user_facing'
            ),

            # Enum Cases - Computed Property Returns
            LocalizationPattern(
                pattern=r'(?:var|let)\s+\w+:\s*String\s*\{\s*return\s+"([^"]+)"\s*\}',
                component_type='ComputedProperty',
                category='enum_localization'
            ),

            # Enum Raw Values
            LocalizationPattern(
                pattern=r'case\s+\w+\s*=\s*"([^"]+)"',
                component_type='EnumRawValue',
                category='enum_localization'
            ),

            # Variable/Property Assignment
            LocalizationPattern(
                pattern=r'(?:var|let)?\s*\w+\s*=\s*"([^"]+)"',
                component_type='VariableAssignment',
                category='user_facing'
            ),

            # Array Append Method
            LocalizationPattern(
                pattern=r'\.append\(\s*"([^"]+)"\s*\)',
                component_type='ArrayAppend',
                category='user_facing'
            ),

            # Array Literal Elements
            LocalizationPattern(
                pattern=r'\[\s*(?:"[^"]*",\s*)*"([^"]+)"',
                component_type='ArrayLiteral',
                category='user_facing'
            ),

            # Dictionary Literals with String Values
            LocalizationPattern(
                pattern=r':\s*\[.*?:\s*"([^"]+)"\s*\]',
                component_type='DictionaryValue',
                category='data_structure'
            ),

            # Array Literals - String Arrays
            LocalizationPattern(
                pattern=r'\[\s*"([^"]+)"\s*,',
                component_type='ArrayLiteral',
                category='data_structure'
            ),
            LocalizationPattern(
                pattern=r',\s*"([^"]+)"\s*\]',
                component_type='ArrayLiteral',
                category='data_structure'
            ),
            LocalizationPattern(
                pattern=r',\s*"([^"]+)"\s*,',
                component_type='ArrayLiteral',
                category='data_structure'
            ),

            # Error Messages - Throw Statements
            LocalizationPattern(
                pattern=r'throw\s+\w+Error\.[a-zA-Z]+\("([^"]+)"\)',
                component_type='ErrorMessage',
                category='error_messages'
            ),
            LocalizationPattern(
                pattern=r'NSError\([^)]*NSLocalizedDescriptionKey:\s*"([^"]+)"',
                component_type='ErrorDescription',
                category='error_messages'
            ),

            # SwiftUI Alert Messages (multi-line)
            LocalizationPattern(
                pattern=r'Alert\s*\([^)]*message:\s*Text\("([^"]+)"\)',
                component_type='AlertMessage',
                category='user_facing'
            ),

            # Toast/HUD Messages
            LocalizationPattern(
                pattern=r'showToast\("([^"]+)"\)',
                component_type='ToastMessage',
                category='user_facing'
            ),
            LocalizationPattern(
                pattern=r'HUD\.show\("([^"]+)"\)',
                component_type='HUDMessage',
                category='user_facing'
            ),

            # Struct/Function Named Parameters (Common UI parameters)
            LocalizationPattern(
                pattern=r'(?:label|title|placeholder|text|message|description|name|subtitle|header|footer|caption|hint|prompt):\s*"([^"]+)"',
                component_type='NamedParameter',
                category='user_facing'
            ),

            # Return Statements - Simple Strings
            LocalizationPattern(
                pattern=r'return\s+"([^"]+)"(?!\s*\+)',
                component_type='ReturnStatement',
                category='user_facing'
            ),

            # Return Statements - String Interpolation
            # Matches: return "text \(variable) more text"
            LocalizationPattern(
                pattern=r'return\s+"([^"]*\\\([^)]+\)[^"]*)"',
                component_type='ReturnInterpolation',
                category='user_facing'
            ),
        ]

        # Swift localization patterns
        self.localized_patterns = [
            LocalizationPattern(
                pattern=r'String\(\s*localized:\s*"([^"]+)"',
                component_type='String.localized',
                category='localized'
            ),
            LocalizationPattern(
                pattern=r'NSLocalizedString\(\s*"([^"]+)"\s*,\s*comment:',
                component_type='NSLocalizedString',
                category='localized'
            ),
            LocalizationPattern(
                pattern=r'LocalizedStringKey\(\s*"([^"]+)"\s*\)',
                component_type='LocalizedStringKey',
                category='localized'
            ),
            LocalizationPattern(
                pattern=r'Text\(\s*String\(\s*localized:\s*"([^"]+)"',
                component_type='Text+String.localized',
                category='localized'
            ),
            LocalizationPattern(
                pattern=r'Button\(\s*String\(\s*localized:\s*"([^"]+)"',
                component_type='Button+String.localized',
                category='localized'
            ),
            # L10n enum pattern (e.g., L10n.Common.save, L10n.Settings.title)
            LocalizationPattern(
                pattern=r'L10n\.[A-Z][a-zA-Z]+\.[a-zA-Z]+',
                component_type='L10n',
                category='localized'
            ),
            # .localized extension pattern (e.g., "key".localized)
            LocalizationPattern(
                pattern=r'"([^"]+)"\.localized',
                component_type='StringExtension',
                category='localized'
            ),
            # .localized(from:) pattern (e.g., "key".localized(from: .common))
            LocalizationPattern(
                pattern=r'"([^"]+)"\.localized\(from:\s*\.[a-zA-Z]+\)',
                component_type='StringExtensionTable',
                category='localized'
            ),
        ]

        # Exclusion patterns - strings that should NOT be localized
        self.exclusion_patterns = [
            # Technical identifiers
            r'^[a-z][a-zA-Z0-9_]*$',  # camelCase identifiers
            r'^[A-Z][A-Z0-9_]*$',  # CONSTANT_NAMES

            # File paths and URLs
            r'^[./]',  # Starts with . or /
            r'https?://',  # HTTP/HTTPS URLs
            r'\.com|\.org|\.net',  # Domain names

            # Format strings and regex
            r'%[@dflsS]',  # Format specifiers
            r'\\[nrt]',  # Escape sequences
            r'[\[\]{}()^$*+?.|\\]',  # Regex characters

            # Version strings
            r'^\d+\.\d+',  # Version numbers like 1.0
            r'^v\d+',  # Version like v1

            # Short technical strings
            r'^[A-Z]{2,}$',  # Abbreviations like API, URL
            r'^\d+$',  # Pure numbers

            # System keys
            r'^@\w+',  # Property wrappers
            r'^\$\w+',  # Dollar prefixed

            # Empty or whitespace only
            r'^\s*$',

            # API Keys and secrets
            r'^sk-',  # OpenAI API keys
            r'^pk_',  # Stripe public keys
            r'^sk_',  # Stripe secret keys
            r'^AIza',  # Google API keys
            r'^[A-Za-z0-9]{32,}$',  # Long alphanumeric strings (likely tokens/keys)

            # Single characters (but NOT emojis in UI context)
            r'^[a-zA-Z]$',  # Single ASCII letter
            r'^[0-9]$',     # Single digit

            # NOTE: Emoji patterns removed - emojis can be meaningful UI elements
            # They will be checked contextually in should_exclude_string method

            # SF Symbols (Apple's system icons)
            r'\.(fill|slash|circle|square|badge)$',  # Common SF Symbol suffixes
            r'^(house|person|gear|chart|heart|star|flag|bell|envelope|phone)',  # Common SF Symbols
            r'\.(fill|slash)$',
            r'^[a-z]+\.(fill|circle|square)',  # icon.fill patterns

            # Technical enum values
            r'^[a-z]+([A-Z][a-z]+)+$',  # camelCase without spaces (enum raw values)

            # Debug/Log strings (lowercase)
            r'^(log|debug|info|warning|error)[:=]',

            # Color hex codes
            r'^[0-9A-Fa-f]{6}$',  # Hex colors like "E74C3C"

            # System property names
            r'^(backgroundColor|textColor|borderColor|shadowColor)',  # Property names

            # UserInfo keys and technical identifiers
            r'^(type|id|key|action|category|identifier|status|code|domain)$',  # Common technical keys
            r'^[a-z]+_[a-z]+',  # snake_case (technical identifiers)

            # Array literal technical values
            r'^(TL|USD|EUR|GBP)$',  # Currency codes
            r'^(blue|green|red|purple|orange|pink|gray|yellow|white|black)$',  # Color names (single words)

            # Date/Time format patterns
            r'^[dMyhHmsS/:.\-\s]+$',  # Date format strings like dd/MM/yyyy, HH:mm:ss
            r'^(dd|MM|yyyy|HH|mm|ss|yy)$',  # Individual date components

            # Punctuation and symbols only
            r'^[\s·\-:;,./\|•→←↑↓…\(\)\[\]\{\}]+$',  # Pure symbols/punctuation

            # Asset/Resource identifiers
            r'^[a-zA-Z]+_\d+$',  # asset_001, avatar_12 patterns
            r'^(avatar|asset|image|icon|sprite|texture|model|anim)[_\-]?\d*$',  # Asset prefixes
            r'^\d+[xX]\d+$',  # Dimension strings like 2x3, 100x100

            # 3D/Animation technical names
            r'^(idle|walk|run|jump|attack|death|spawn|hit)[_\-]?\d*$',  # Animation names
            r'^(mesh|bone|joint|node|layer|blend)[_\-]?\w*$',  # 3D technical terms
            r'^[A-Z][a-z]+(?:Animation|Mesh|Texture|Material|Shader|Prefab)$',  # Asset type suffixes

            # Debug/Development strings
            r'^(DEBUG|TODO|FIXME|HACK|NOTE|XXX|MARK)[:=\s-]',  # Debug markers
            r'^\[DEBUG\]',  # Debug prefix
            r'^(print|log|debug|trace|dump)\s*:',  # Debug output prefixes

            # AI/Backend context strings (not user-facing)
            r'^(system|user|assistant):\s*',  # AI role markers
            r'^(prompt|context|instruction)[:=]',  # AI-related prefixes
            r'^\{[a-z_]+\}$',  # Template variables like {user_name}

            # Technical measurement units
            r'^\d+\s*(px|pt|em|rem|%|dp|sp|vw|vh)$',  # CSS/UI units
            r'^\d+(\.\d+)?\s*(mb|kb|gb|ms|fps|hz)$',  # Technical units (case insensitive handled elsewhere)

            # JSON/Code structure strings
            r'^\{|\}$',  # Single braces
            r'^\[|\]$',  # Single brackets
            r'^<[^>]+>$',  # HTML/XML tags
            r'^[a-zA-Z]+\(\)$',  # Function call patterns like "init()"

            # Filename patterns (without path)
            r'^\w+\.(png|jpg|jpeg|gif|svg|pdf|json|xml|plist|strings|swift|m|h)$',  # File extensions
        ]

    @classmethod
    def _get_compiled_emoji_pattern(cls):
        """Get cached compiled emoji pattern for performance."""
        if cls._compiled_emoji_pattern is None:
            cls._compiled_emoji_pattern = re.compile(
                r'[\U0001F300-\U0001F9FF'  # Misc Symbols & Pictographs, Emoticons, etc.
                r'\U0001F600-\U0001F64F'   # Emoticons
                r'\U0001F680-\U0001F6FF'   # Transport & Map
                r'\U0001FA70-\U0001FAFF'   # Symbols & Pictographs Extended-A
                r'\U00002600-\U000026FF'   # Misc symbols (sun, cloud, etc.)
                r'\U00002700-\U000027BF'   # Dingbats
                r'\U0001F1E0-\U0001F1FF'   # Flags
                r'\U00002300-\U000023FF'   # Misc Technical
                r'\U0000FE00-\U0000FE0F'   # Variation Selectors
                r'\U0001F900-\U0001F9FF'   # Supplemental Symbols
                r'\U00002702-\U000027B0'   # Dingbats
                r'\U0001FA00-\U0001FA6F'   # Chess symbols, etc.
                r'\U00002194-\U00002199'   # Arrows
                r'\U000021A9-\U000021AA'   # More arrows
                r'\U0000231A-\U0000231B'   # Watch, hourglass
                r'\U000023E9-\U000023F3'   # Media symbols
                r'\U000023F8-\U000023FA'   # Media controls
                r'\U000025AA-\U000025AB'   # Squares
                r'\U000025B6\U000025C0'    # Play buttons
                r'\U000025FB-\U000025FE'   # Squares
                r'\U00002614-\U00002615'   # Umbrella, hot beverage
                r'\U00002648-\U00002653'   # Zodiac
                r'\U0000267F'              # Wheelchair
                r'\U00002693'              # Anchor
                r'\U000026A1'              # High voltage
                r'\U000026AA-\U000026AB'   # Circles
                r'\U000026BD-\U000026BE'   # Sports
                r'\U000026C4-\U000026C5'   # Weather
                r'\U000026CE'              # Ophiuchus
                r'\U000026D4'              # No entry
                r'\U000026EA'              # Church
                r'\U000026F2-\U000026F3'   # Fountain, golf
                r'\U000026F5'              # Sailboat
                r'\U000026FA'              # Tent
                r'\U000026FD'              # Fuel pump
                r'\U00002934-\U00002935'   # Arrows
                r'\U00002B05-\U00002B07'   # Arrows
                r'\U00002B1B-\U00002B1C'   # Squares
                r'\U00002B50'              # Star
                r'\U00002B55'              # Circle
                r'\U00003030'              # Wavy dash
                r'\U0000303D'              # Part alternation mark
                r'\U00003297'              # Circled Ideograph Congratulation
                r'\U00003299'              # Circled Ideograph Secret
                r'\U0000200D'              # Zero Width Joiner (for compound emojis)
                r'\U0000FE0F'              # Variation Selector-16
                r']+'
            )
        return cls._compiled_emoji_pattern

    @classmethod
    def _get_compiled_exclusion_patterns(cls, patterns):
        """Get cached compiled exclusion patterns for performance."""
        # Invalidate cache if patterns changed (using tuple for hashability)
        patterns_tuple = tuple(patterns)
        if cls._compiled_exclusion_patterns is None or \
           not hasattr(cls, '_exclusion_patterns_key') or \
           cls._exclusion_patterns_key != patterns_tuple:
            cls._compiled_exclusion_patterns = [re.compile(p) for p in patterns]
            cls._exclusion_patterns_key = patterns_tuple
        return cls._compiled_exclusion_patterns

    def should_exclude_string(self, text: str) -> bool:
        """
        Check if a string should be excluded from localization.

        Args:
            text: The string to check

        Returns:
            True if string should be excluded, False otherwise
        """
        if not text or not text.strip():
            return True

        # Use cached compiled emoji pattern for performance
        emoji_pattern = self._get_compiled_emoji_pattern()

        # Check if string is pure emoji(s) - NO alphabetic text at all
        text_without_emoji = emoji_pattern.sub('', text).strip()

        # If nothing left after removing emojis, it's a pure emoji string - EXCLUDE IT
        if not text_without_emoji:
            return True

        # Use cached compiled exclusion patterns for performance
        compiled_patterns = self._get_compiled_exclusion_patterns(self.exclusion_patterns)
        for pattern in compiled_patterns:
            if pattern.search(text):
                return True

        # Exclude single English words without special characters (likely technical identifiers)
        # But keep localized words and multi-word phrases
        # Check for special characters from multiple languages
        special_chars = set(self.CHAR_MAP.keys())
        has_special_char = any(char in text for char in special_chars)
        has_space = ' ' in text

        # If it's a single word without special chars, likely technical
        if not has_special_char and not has_space and len(text.split()) == 1:
            # Check if it's all ASCII letters (no numbers, symbols)
            if text.isalpha() and text.isascii():
                # But allow common UI words that should be localized
                common_ui_words = ['Home', 'Save', 'Cancel', 'Delete', 'Edit', 'Settings',
                                   'Profile', 'Search', 'Filter', 'Sort', 'View', 'Add',
                                   'Back', 'Next', 'Done', 'OK', 'Yes', 'No', 'Close',
                                   'Open', 'Create', 'Update', 'Submit', 'Send', 'Share']
                if text not in common_ui_words:
                    return True

        # Keep special characters and multi-word phrases
        return False

    def get_file_extensions(self) -> List[str]:
        """Return Swift file extensions."""
        return ['.swift']

    def get_localization_file_pattern(self) -> str:
        """Return pattern for .strings files (supports modular strings)."""
        return '*.lproj/*.strings'

    def parse_localization_file(self, file_path: Path) -> Dict[str, str]:
        """
        Parse .strings file format.

        Format: "key" = "value";

        Note: Supports escaped characters in values (e.g., \", \\, \n)
        """
        keys = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Pattern supports escaped characters: \" \\ \n etc.
                # (?:[^"\\]|\\.)* matches: non-quote/non-backslash chars OR backslash+any char
                pattern = r'^"([^"]+)"\s*=\s*"((?:[^"\\]|\\.)*)";'
                matches = re.finditer(pattern, content, re.MULTILINE)

                for match in matches:
                    key, value = match.groups()
                    keys[key] = value
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return keys

    def write_localization_entry(
        self,
        file_path: Path,
        key: str,
        value: str,
        append: bool = True
    ) -> bool:
        """
        Write entry to .strings file.

        Format: "key" = "value";
        """
        try:
            if append:
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f'\n"{key}" = "{value}";\n')
            else:
                # Replace mode - read, modify, write
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Replace or append
                pattern = rf'^"{re.escape(key)}"\s*=\s*"[^"]*";'
                new_entry = f'"{key}" = "{value}";'

                if re.search(pattern, content, re.MULTILINE):
                    content = re.sub(pattern, new_entry, content, flags=re.MULTILINE)
                else:
                    content += f'\n{new_entry}\n'

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            return True
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
            return False

    def determine_module(self, file_path: str) -> str:
        """
        Determine which L10n module a file belongs to based on its path.

        Args:
            file_path: Path to the source file

        Returns:
            Module name (e.g., 'Settings', 'Chat', 'Common')
        """
        if not self.l10n_config:
            return "Common"

        file_path_lower = file_path.lower()

        # Check each mapping pattern
        for pattern, module in self.l10n_config.module_mapping.items():
            if pattern.lower() in file_path_lower:
                return module

        return self.l10n_config.default_module

    # Character mapping for multiple languages (special characters to ASCII)
    # Supports: Turkish, German, French, Spanish, Portuguese, Polish, Czech,
    # Hungarian, Romanian, Swedish, Norwegian, Danish, Finnish, Italian, Dutch
    CHAR_MAP = {
        # Turkish
        'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U',
        # German
        'ä': 'a', 'Ä': 'A', 'ß': 'ss',
        # French
        'à': 'a', 'â': 'a', 'æ': 'ae', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'î': 'i', 'ï': 'i', 'ô': 'o', 'œ': 'oe', 'ù': 'u', 'û': 'u', 'ÿ': 'y',
        'À': 'A', 'Â': 'A', 'Æ': 'AE', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Î': 'I', 'Ï': 'I', 'Ô': 'O', 'Œ': 'OE', 'Ù': 'U', 'Û': 'U', 'Ÿ': 'Y',
        # Spanish
        'á': 'a', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n',
        'Á': 'A', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ñ': 'N',
        # Portuguese
        'ã': 'a', 'õ': 'o',
        'Ã': 'A', 'Õ': 'O',
        # Polish
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
        # Czech
        'č': 'c', 'ď': 'd', 'ě': 'e', 'ň': 'n', 'ř': 'r', 'ť': 't', 'ů': 'u', 'ý': 'y', 'ž': 'z',
        'Č': 'C', 'Ď': 'D', 'Ě': 'E', 'Ň': 'N', 'Ř': 'R', 'Ť': 'T', 'Ů': 'U', 'Ý': 'Y', 'Ž': 'Z',
        # Hungarian
        'ő': 'o', 'ű': 'u',
        'Ő': 'O', 'Ű': 'U',
        # Romanian
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T',
        # Scandinavian (Swedish, Norwegian, Danish)
        'å': 'a', 'Å': 'A', 'ø': 'o', 'Ø': 'O',
        # Dutch
        'ĳ': 'ij', 'Ĳ': 'IJ',
        # General Latin Extended
        'ð': 'd', 'Ð': 'D', 'þ': 'th', 'Þ': 'TH',
    }

    def text_to_key(self, text: str) -> str:
        """
        Convert text to a localization key.

        Supports special characters from multiple languages:
        Turkish, German, French, Spanish, Portuguese, Polish, Czech,
        Hungarian, Romanian, Swedish, Norwegian, Danish, Finnish, Italian, Dutch

        Args:
            text: Original text

        Returns:
            Localization key (camelCase)
        """
        import unicodedata

        # First, apply explicit character mappings for known special chars
        for char, replacement in self.CHAR_MAP.items():
            text = text.replace(char, replacement)

        # Normalize unicode characters (handles remaining accents)
        text = unicodedata.normalize('NFKD', text)

        # Remove combining characters (accents that weren't mapped)
        text = ''.join(c for c in text if not unicodedata.combining(c))

        # Split into words
        words = re.split(r'[^a-zA-Z0-9]+', text)
        words = [w for w in words if w]

        if not words:
            return "unknown"

        # Convert to camelCase
        result = words[0].lower()
        for word in words[1:]:
            result += word.capitalize()

        return result

    def generate_localized_code(self, key: str, component_type: str, file_path: str = None, original_text: str = None) -> str:
        """
        Generate Swift code for localized string.

        Args:
            key: Localization key (may contain module prefix like "common.save")
            component_type: UI component type
            file_path: Source file path (used for L10n module detection)
            original_text: Original hardcoded text

        Returns:
            Code snippet using configured localization pattern
        """
        # Determine module/table from file path
        if self.l10n_config and self.l10n_config.enabled:
            module = self.determine_module(file_path) if file_path else self.l10n_config.default_module
        else:
            module = "common"

        # Extract just the key part if it has a module prefix (e.g., "common.save" -> "save")
        if '.' in key:
            key_parts = key.split('.')
            clean_key = key_parts[-1]  # Take the last part as the actual key
        else:
            clean_key = key

        # Convert module name to StringTable case (e.g., "Settings" -> "settings", "CheckIn" -> "checkIn")
        table_case = module[0].lower() + module[1:] if module else "common"

        # Check if we should use .localized(from:) or L10n enum pattern
        if self.l10n_config and hasattr(self.l10n_config, 'use_localized_extension') and self.l10n_config.use_localized_extension:
            # Generate "key".localized(from: .table) pattern
            return f'"{clean_key}".localized(from: .{table_case})'
        else:
            # Generate L10n.Module.key pattern
            return f'{self.l10n_config.enum_name if self.l10n_config else "L10n"}.{module}.{clean_key}'

    def get_table_name(self, file_path: str) -> str:
        """
        Get the table name for a given source file path.

        Args:
            file_path: Path to the source file

        Returns:
            Table name (e.g., "Common", "Chat", "Settings")
        """
        if not self.l10n_config or not self.l10n_config.enabled:
            return "Localizable"

        module = self.determine_module(file_path)

        # Check if module is in tables mapping
        if hasattr(self.l10n_config, 'tables') and self.l10n_config.tables:
            # Try lowercase lookup first
            module_lower = module.lower() if module else "common"
            if module_lower in self.l10n_config.tables:
                return self.l10n_config.tables[module_lower]
            # Try original case
            if module in self.l10n_config.tables:
                return self.l10n_config.tables[module]

        return module if module else "Common"

    def get_strings_file_path(self, lang_code: str, table_name: str, resources_dir: Path) -> Path:
        """
        Get the path to a .strings file for a given language and table.

        Args:
            lang_code: Language code (e.g., "en", "tr")
            table_name: Table name (e.g., "Common", "Chat")
            resources_dir: Resources directory containing .lproj folders

        Returns:
            Path to the .strings file
        """
        return resources_dir / f"{lang_code}.lproj" / f"{table_name}.strings"

    def discover_tables(self, resources_dir: Path) -> Dict[str, str]:
        """
        Dinamik olarak .strings dosyalarından tablo isimlerini keşfeder.

        Args:
            resources_dir: Resources dizini (.lproj klasörlerini içeren)

        Returns:
            {table_key: table_name} sözlüğü
            Örnek: {"common": "Common", "chat": "Chat", "settings": "Settings"}
        """
        if self._discovered_tables:
            return self._discovered_tables

        tables = {}

        # Find all .lproj directories
        lproj_dirs = list(resources_dir.glob("*.lproj"))

        if not lproj_dirs:
            # Try subdirectories (e.g., ProjectName/Resources/)
            for subdir in resources_dir.iterdir():
                if subdir.is_dir():
                    lproj_dirs.extend(subdir.glob("*.lproj"))

        # Use first .lproj directory as reference (usually en.lproj)
        if lproj_dirs:
            # Prefer en.lproj, otherwise use first available
            ref_dir = None
            for lproj in lproj_dirs:
                if lproj.name == "en.lproj":
                    ref_dir = lproj
                    break
            if not ref_dir:
                ref_dir = lproj_dirs[0]

            # Find all .strings files
            for strings_file in ref_dir.glob("*.strings"):
                table_name = strings_file.stem  # e.g., "Common" from "Common.strings"
                # Generate table key (camelCase, lowercase first letter)
                table_key = table_name[0].lower() + table_name[1:] if table_name else table_name.lower()
                tables[table_key] = table_name

        self._discovered_tables = tables
        return tables

    def get_all_tables(self, resources_dir: Path) -> Dict[str, str]:
        """
        Tüm tabloları döndürür (config + keşfedilen).

        Config'deki tablolar önceliklidir.
        auto_discover_tables=True ise, eksik tablolar otomatik keşfedilir.

        Args:
            resources_dir: Resources dizini

        Returns:
            {table_key: table_name} sözlüğü
        """
        # Start with config tables
        tables = {}

        if self.l10n_config and hasattr(self.l10n_config, 'tables'):
            tables.update(self.l10n_config.tables)

        # Auto-discover if enabled
        if self.l10n_config and hasattr(self.l10n_config, 'auto_discover_tables') and self.l10n_config.auto_discover_tables:
            discovered = self.discover_tables(resources_dir)
            # Add discovered tables that aren't already in config
            for key, name in discovered.items():
                if key not in tables:
                    tables[key] = name

        # If no tables found, use default
        if not tables:
            tables = {"localizable": "Localizable"}

        return tables

    def auto_detect_module_mapping(self, source_dir: Path) -> Dict[str, str]:
        """
        Kaynak kod dizininden otomatik modül mapping keşfeder.

        View/ViewModel dosyalarından modül isimlerini çıkarır.

        Args:
            source_dir: Kaynak kod dizini

        Returns:
            {pattern: module_name} sözlüğü
        """
        mapping = {}

        # Common directory patterns that indicate modules
        module_patterns = [
            "Views", "ViewModels", "Screens", "Features", "Modules",
            "Controllers", "Presenters", "Components"
        ]

        for pattern in module_patterns:
            pattern_dir = source_dir / pattern
            if pattern_dir.exists():
                # Get subdirectories as module names
                for subdir in pattern_dir.iterdir():
                    if subdir.is_dir() and not subdir.name.startswith('.'):
                        module_name = subdir.name
                        # Add mapping: directory name -> module name
                        mapping[module_name] = module_name

        # Also check for direct Swift files with View/ViewModel suffix
        for swift_file in source_dir.rglob("*View.swift"):
            # Extract module name from file name
            file_name = swift_file.stem  # e.g., "SettingsView"
            if file_name.endswith("View"):
                module_name = file_name[:-4]  # Remove "View" suffix
                if module_name and module_name not in mapping:
                    mapping[module_name] = module_name

        return mapping

    def extract_language_code(self, file_path: Path) -> str:
        """
        Extract language code from .lproj directory.

        Example: /path/to/en.lproj/Localizable.strings -> en
        """
        lproj_dir = file_path.parent
        if lproj_dir.name.endswith('.lproj'):
            return lproj_dir.name.replace('.lproj', '')
        return 'unknown'

    def create_strings_file_header(self, language: str, project_name: str = '') -> str:
        """
        Create header for .strings file.

        Args:
            language: Language name
            project_name: Project name

        Returns:
            Header text
        """
        from datetime import datetime

        return f'''/*
  Localizable.strings ({language})
  {project_name}

  Created: {datetime.now().strftime('%Y-%m-%d')}
  Language: {language}
*/

'''
