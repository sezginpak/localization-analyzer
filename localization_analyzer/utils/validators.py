"""Validation utilities."""

import re
from typing import Optional


def is_valid_language_code(code: str) -> bool:
    """
    Validate language code (ISO 639-1 or ISO 639-2).

    Examples: en, tr, es, pt-BR, zh-CN
    """
    pattern = r'^[a-z]{2,3}(-[A-Z]{2})?$'
    return bool(re.match(pattern, code))


def is_valid_key_name(key: str) -> bool:
    """
    Validate localization key name.

    Valid formats:
        - common.save
        - button.cancel
        - error.network.timeout
    """
    if not key:
        return False

    # Must contain at least one dot
    if '.' not in key:
        return False

    # Check each part
    parts = key.split('.')
    for part in parts:
        if not part:
            return False
        # Allow alphanumeric, underscores, hyphens
        if not re.match(r'^[a-z0-9_-]+$', part):
            return False

    return True


def sanitize_key_name(text: str, prefix: str = 'text') -> str:
    """
    Generate a valid key name from text.

    Args:
        text: Original text
        prefix: Key prefix (e.g., 'button', 'label')

    Returns:
        Valid key name
    """
    # Remove special characters
    clean_text = re.sub(r'[^\w\s]', '', text.lower())

    # Split into words and take first 4
    words = clean_text.split()[:4]

    if not words:
        words = ['unnamed']

    # Join with dots
    key_parts = [prefix] + words
    return '.'.join(key_parts)


def is_excluded_string(text: str) -> bool:
    """
    Check if string should be excluded from localization.

    Excludes:
        - Emojis (pure emoji strings)
        - URLs
        - Pure numbers
        - SF Symbols
        - Very short strings
        - System identifiers
    """
    if not text or len(text.strip()) <= 1:
        return True

    # Comprehensive emoji pattern
    emoji_pattern = re.compile(
        r'[\U0001F300-\U0001F9FF'  # Misc Symbols & Pictographs, Emoticons, etc.
        r'\U0001F600-\U0001F64F'   # Emoticons
        r'\U0001F680-\U0001F6FF'   # Transport & Map
        r'\U0001FA70-\U0001FAFF'   # Symbols & Pictographs Extended-A
        r'\U00002600-\U000026FF'   # Misc symbols
        r'\U00002700-\U000027BF'   # Dingbats
        r'\U0001F1E0-\U0001F1FF'   # Flags
        r'\U00002300-\U000023FF'   # Misc Technical
        r'\U0000FE00-\U0000FE0F'   # Variation Selectors
        r'\U0001F900-\U0001F9FF'   # Supplemental Symbols
        r']+'
    )

    # Check if string is pure emoji(s)
    text_without_emoji = emoji_pattern.sub('', text.strip())
    if not text_without_emoji:
        return True  # Pure emoji string - exclude

    exclude_patterns = [
        r'^[0-9\s\.\,\-\+\*\/\=\<\>%]+$',  # Numbers/operators only
        r'^(https?://|www\.)',  # URLs
        r'^[A-Z_]+$',  # CONSTANTS
        r'^SF Symbols?:',  # SF Symbols
        r'^\$\d+',  # Currency
        r'^%[@dfs]',  # Format specifiers
        r'^\.{3,}$',  # Ellipsis
        r'^\s*$',  # Whitespace only
        r'^[a-z]+\.[a-z]+',  # Identifiers like "system.fill"
        r'^sk-[a-zA-Z0-9]+',  # API keys
        r'^[A-Za-z0-9]{32,}$',  # Long hashes/tokens
        r'^gpt-',  # Model names
        r'^HH:mm|^dd/MM|^EEEE',  # Date formats
    ]

    for pattern in exclude_patterns:
        if re.match(pattern, text.strip()):
            return True

    # Check if text has enough alphabetic characters (at least 30%)
    alpha_count = sum(c.isalpha() for c in text)
    if len(text) > 0 and alpha_count < len(text) * 0.3:
        return True

    return False


def validate_strings_file_format(content: str) -> tuple[bool, Optional[str]]:
    """
    Validate .strings file format.

    Returns:
        (is_valid, error_message)
    """
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('/*') or line.startswith('*') or line.startswith('//'):
            continue

        # Check format: "key" = "value";
        if '=' in line:
            if not re.match(r'^"[^"]+"\s*=\s*"[^"]*";', line):
                return False, f"Invalid format at line {i}: {line[:50]}..."

    return True, None
