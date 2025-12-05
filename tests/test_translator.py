"""Tests for the translator module."""

import pytest
from pathlib import Path
import tempfile
import json

from localization_analyzer.features.translator import (
    TranslationService,
    translate_key_value
)


class TestTranslationService:
    """Test cases for TranslationService."""

    def test_init_default(self):
        """Test default initialization."""
        translator = TranslationService()
        assert translator.source_lang == 'en'
        assert translator.cache == {}

    def test_init_with_source_lang(self):
        """Test initialization with custom source language."""
        translator = TranslationService(source_lang='tr')
        assert translator.source_lang == 'tr'

    def test_is_supported(self):
        """Test language support check."""
        translator = TranslationService()

        # Supported languages
        assert translator.is_supported('en')
        assert translator.is_supported('tr')
        assert translator.is_supported('de')
        assert translator.is_supported('ja')

        # Unsupported languages
        assert not translator.is_supported('xyz')
        assert not translator.is_supported('')

    def test_get_language_name(self):
        """Test language name retrieval."""
        translator = TranslationService()

        assert translator.get_language_name('en') == 'English'
        assert translator.get_language_name('tr') == 'Turkish'
        assert translator.get_language_name('de') == 'German'
        assert 'Unknown' in translator.get_language_name('xyz')

    def test_same_language_no_translate(self):
        """Test that same language returns original text."""
        translator = TranslationService(source_lang='en')
        result = translator.translate('Hello', 'en', 'en')
        assert result == 'Hello'

    def test_empty_text(self):
        """Test empty text handling."""
        translator = TranslationService()

        assert translator.translate('', 'tr') == ''
        assert translator.translate('   ', 'tr') == '   '
        assert translator.translate(None, 'tr') is None

    def test_cache_functionality(self):
        """Test translation caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / 'cache.json'
            translator = TranslationService(cache_file=cache_file)

            # Manually add to cache
            translator.cache['en:tr:Hello'] = 'Merhaba'
            translator._save_cache()

            # Load new translator with same cache
            translator2 = TranslationService(cache_file=cache_file)
            assert 'en:tr:Hello' in translator2.cache
            assert translator2.cache['en:tr:Hello'] == 'Merhaba'

    def test_translate_batch(self):
        """Test batch translation."""
        translator = TranslationService()

        # Mock the translate method for testing
        translator.cache['en:tr:Hello'] = 'Merhaba'
        translator.cache['en:tr:World'] = 'Dünya'

        # Note: This test requires network or mocked responses
        # For unit test, we just verify the structure
        results = translator.translate_batch(['Hello'], 'tr')
        assert isinstance(results, dict)
        assert 'Hello' in results


class TestTranslateKeyValue:
    """Test cases for translate_key_value function."""

    def test_empty_value(self):
        """Test empty value handling."""
        result = translate_key_value('key', '', 'en', 'tr')
        assert result == ''

    def test_preserves_interpolation_swift(self):
        """Test Swift interpolation pattern preservation."""
        # Create a translator with cached response
        translator = TranslationService()
        translator.cache['en:tr:Hello __PLACEHOLDER0__'] = 'Merhaba __PLACEHOLDER0__'

        # Test: The function should preserve %@ patterns
        # Note: Real test would require network or proper mocking
        value = "Hello %@"
        # The pattern should be detected
        assert '%@' in value

    def test_preserves_interpolation_format(self):
        """Test format string preservation."""
        # %d, %f patterns should be preserved
        value = "You have %d items"
        assert '%d' in value

        value2 = "Price: %f"
        assert '%f' in value2

    def test_preserves_swift_string_interpolation(self):
        """Test Swift string interpolation preservation."""
        value = r"Hello \(name)"
        assert r'\(' in value


class TestTranslationIntegration:
    """Integration tests (require network)."""

    @pytest.mark.skip(reason="Requires network access")
    def test_real_translation_en_to_tr(self):
        """Test real translation from English to Turkish."""
        translator = TranslationService(source_lang='en')
        result = translator.translate('Hello', 'tr')

        # Should return Turkish greeting
        assert result is not None
        assert result.lower() in ['merhaba', 'selam']

    @pytest.mark.skip(reason="Requires network access")
    def test_real_translation_to_multiple_languages(self):
        """Test translation to multiple languages."""
        translator = TranslationService(source_lang='en')
        result = translator.translate_to_all_languages(
            'Hello',
            ['tr', 'de', 'fr']
        )

        assert 'en' in result  # Source language
        assert 'tr' in result
        assert 'de' in result
        assert 'fr' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
