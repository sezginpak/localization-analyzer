"""Tests for emoji filtering in localization analyzer."""

import pytest
from localization_analyzer.frameworks.swift import SwiftAdapter
from localization_analyzer.frameworks.base import BaseAdapter


class TestEmojiFiltering:
    """Test cases for emoji string filtering."""

    def setup_method(self):
        """Her test oncesinde SwiftAdapter olustur."""
        self.adapter = SwiftAdapter()

    def test_pure_emoji_excluded(self):
        """Pure emoji stringleri exclude edilmeli."""
        pure_emojis = [
            "😀",
            "🎉",
            "❤️",
            "🔥",
            "✨",
            "👍",
            "🙌",
            "😍😍😍",
            "🌟⭐🌟",
            "🎯",
            "🚀",
            "💡",
            "📱",
            "🏠",
            "🔒",
            "⚡",
            "☀️",
            "🌙",
            "🌈",
            "🎵",
            "🎮",
            "🍕",
            "🍎",
            "🚗",
            "✅",
            "❌",
            "⚠️",
            "🔴",
            "🟢",
            "🟡",
        ]

        for emoji in pure_emojis:
            assert self.adapter.should_exclude_string(emoji), f"Pure emoji '{emoji}' should be excluded"

    def test_emoji_with_text_not_excluded(self):
        """Emoji + text kombinasyonlari exclude edilmemeli."""
        emoji_with_text = [
            "Hello 👋",
            "🎉 Congratulations!",
            "Error ❌ Something went wrong",
            "✅ Success",
            "Warning ⚠️ Please check",
            "🔥 Hot deals",
            "Save 💾",
        ]

        for text in emoji_with_text:
            assert not self.adapter.should_exclude_string(text), f"Text with emoji '{text}' should NOT be excluded"

    def test_compound_emojis_excluded(self):
        """Bilesik emojiler (ZWJ ile) exclude edilmeli."""
        compound_emojis = [
            "👨‍👩‍👧‍👦",  # Family
            "👩‍💻",      # Woman technologist
            "🏳️‍🌈",     # Rainbow flag
        ]

        for emoji in compound_emojis:
            assert self.adapter.should_exclude_string(emoji), f"Compound emoji '{emoji}' should be excluded"

    def test_flag_emojis_excluded(self):
        """Bayrak emojileri exclude edilmeli."""
        flag_emojis = [
            "🇹🇷",  # Turkey
            "🇺🇸",  # USA
            "🇬🇧",  # UK
            "🇩🇪",  # Germany
        ]

        for emoji in flag_emojis:
            assert self.adapter.should_exclude_string(emoji), f"Flag emoji '{emoji}' should be excluded"


class TestEmojiPriority:
    """Test cases for emoji priority calculation."""

    def setup_method(self):
        """Her test oncesinde SwiftAdapter olustur."""
        self.adapter = SwiftAdapter()

    def test_pure_emoji_zero_priority(self):
        """Pure emoji stringleri 0 priority olmali."""
        pure_emojis = ["😀", "🎉", "❤️", "🔥", "✨", "👍", "🏠", "📱", "🎵"]

        for emoji in pure_emojis:
            priority = self.adapter.calculate_priority("Text", "visible_ui", emoji)
            assert priority == 0, f"Pure emoji '{emoji}' should have 0 priority, got {priority}"

    def test_text_with_emoji_has_priority(self):
        """Emoji + text kombinasyonlari priority olmali."""
        texts_with_emoji = [
            ("Hello 👋", "Text", "visible_ui"),
            ("🎉 Success!", "Alert", "error_messages"),
            ("Save 💾", "Button", "visible_ui"),
        ]

        for text, component, category in texts_with_emoji:
            priority = self.adapter.calculate_priority(component, category, text)
            assert priority > 0, f"Text with emoji '{text}' should have priority > 0, got {priority}"

    def test_regular_text_has_priority(self):
        """Normal text priority olmali."""
        texts = [
            ("Hello World", "Text", "visible_ui"),
            ("Save", "Button", "visible_ui"),
            ("Error occurred", "Alert", "error_messages"),
        ]

        for text, component, category in texts:
            priority = self.adapter.calculate_priority(component, category, text)
            assert priority > 0, f"Text '{text}' should have priority > 0, got {priority}"


class TestValidatorsEmojiFilter:
    """Test validators.py emoji filtering."""

    def test_is_excluded_string_pure_emoji(self):
        """validators.is_excluded_string pure emoji'leri exclude etmeli."""
        from localization_analyzer.utils.validators import is_excluded_string

        pure_emojis = ["😀", "🎉", "❤️", "🔥", "✨", "🏠📱🎵"]

        for emoji in pure_emojis:
            assert is_excluded_string(emoji), f"Pure emoji '{emoji}' should be excluded by is_excluded_string"

    def test_is_excluded_string_text_with_emoji(self):
        """validators.is_excluded_string emoji+text'i exclude etmemeli."""
        from localization_analyzer.utils.validators import is_excluded_string

        texts = ["Hello 👋", "🎉 Success", "Warning ⚠️"]

        for text in texts:
            assert not is_excluded_string(text), f"Text with emoji '{text}' should NOT be excluded"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
