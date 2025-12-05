"""Tests for multi-language character support in localization analyzer."""

import pytest
from localization_analyzer.frameworks.swift import SwiftAdapter


class TestTextToKeyMultiLanguage:
    """Test cases for text_to_key with multi-language character support."""

    def setup_method(self):
        """Setup test adapter."""
        self.adapter = SwiftAdapter()

    def test_turkish_characters(self):
        """Turkish characters should be converted correctly."""
        test_cases = [
            ("Çıkış", "cikis"),
            ("Güncelle", "guncelle"),
            ("Şifre", "sifre"),
            ("Üye Ol", "uyeOl"),
            ("İletişim", "iletisim"),
            ("Ödemeler", "odemeler"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_german_characters(self):
        """German characters should be converted correctly."""
        test_cases = [
            ("Größe", "grosse"),
            ("Ändern", "andern"),
            ("Öffnen", "offnen"),
            ("Über uns", "uberUns"),
            ("Schließen", "schliessen"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_french_characters(self):
        """French characters should be converted correctly."""
        test_cases = [
            ("Déconnexion", "deconnexion"),
            ("Paramètres", "parametres"),
            ("Créer", "creer"),
            ("Français", "francais"),
            ("Œuvre", "oeuvre"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_spanish_characters(self):
        """Spanish characters should be converted correctly."""
        test_cases = [
            ("Año", "ano"),
            ("Señor", "senor"),
            ("Información", "informacion"),
            ("Búsqueda", "busqueda"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_polish_characters(self):
        """Polish characters should be converted correctly."""
        test_cases = [
            ("Zażółć", "zazolc"),
            ("Łódź", "lodz"),
            ("Świętość", "swietosc"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_czech_characters(self):
        """Czech characters should be converted correctly."""
        test_cases = [
            ("Říční", "ricni"),
            ("Žába", "zaba"),
            ("Člověk", "clovek"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_scandinavian_characters(self):
        """Scandinavian characters should be converted correctly."""
        test_cases = [
            ("Årsrapport", "arsrapport"),
            ("København", "kobenhavn"),
            ("Øresund", "oresund"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_mixed_special_characters(self):
        """Mixed special characters from different languages should work."""
        test_cases = [
            ("Größe ändern", "grosseAndern"),
            ("Çıkış Yap", "cikisYap"),
            ("Información útil", "informacionUtil"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"

    def test_plain_english(self):
        """Plain English text should work as before."""
        test_cases = [
            ("Save", "save"),
            ("Cancel Changes", "cancelChanges"),
            ("Delete Item", "deleteItem"),
        ]
        for text, expected in test_cases:
            result = self.adapter.text_to_key(text)
            assert result == expected, f"'{text}' should convert to '{expected}', got '{result}'"


class TestCharMapCompleteness:
    """Test CHAR_MAP completeness."""

    def setup_method(self):
        """Setup test adapter."""
        self.adapter = SwiftAdapter()

    def test_char_map_has_turkish(self):
        """CHAR_MAP should contain Turkish characters."""
        turkish_chars = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'Ç', 'Ğ', 'İ', 'Ö', 'Ş', 'Ü']
        for char in turkish_chars:
            assert char in self.adapter.CHAR_MAP, f"Turkish char '{char}' missing from CHAR_MAP"

    def test_char_map_has_german(self):
        """CHAR_MAP should contain German characters."""
        german_chars = ['ä', 'ö', 'ü', 'ß', 'Ä', 'Ö', 'Ü']
        for char in german_chars:
            assert char in self.adapter.CHAR_MAP, f"German char '{char}' missing from CHAR_MAP"

    def test_char_map_has_french(self):
        """CHAR_MAP should contain French characters."""
        french_chars = ['à', 'â', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'ÿ', 'œ', 'æ']
        for char in french_chars:
            assert char in self.adapter.CHAR_MAP, f"French char '{char}' missing from CHAR_MAP"

    def test_char_map_has_spanish(self):
        """CHAR_MAP should contain Spanish characters."""
        spanish_chars = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'Ñ']
        for char in spanish_chars:
            assert char in self.adapter.CHAR_MAP, f"Spanish char '{char}' missing from CHAR_MAP"

    def test_char_map_has_polish(self):
        """CHAR_MAP should contain Polish characters."""
        polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ś', 'ź', 'ż']
        for char in polish_chars:
            assert char in self.adapter.CHAR_MAP, f"Polish char '{char}' missing from CHAR_MAP"


class TestPatternCaching:
    """Test regex pattern caching for performance."""

    def test_emoji_pattern_cached(self):
        """Emoji pattern should be cached at class level."""
        adapter1 = SwiftAdapter()
        adapter2 = SwiftAdapter()

        # First call compiles the pattern
        pattern1 = adapter1._get_compiled_emoji_pattern()
        # Second call should return the same cached pattern
        pattern2 = adapter2._get_compiled_emoji_pattern()

        assert pattern1 is pattern2, "Emoji pattern should be cached at class level"

    def test_exclusion_patterns_cached(self):
        """Exclusion patterns should be cached at class level."""
        adapter1 = SwiftAdapter()
        adapter2 = SwiftAdapter()

        # First call compiles the patterns
        patterns1 = adapter1._get_compiled_exclusion_patterns(adapter1.exclusion_patterns)
        # Second call should return the same cached patterns
        patterns2 = adapter2._get_compiled_exclusion_patterns(adapter2.exclusion_patterns)

        assert patterns1 is patterns2, "Exclusion patterns should be cached at class level"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
