"""Automatic translation service for localization."""

import re
import json
import ssl
import urllib.request
import urllib.parse
from typing import Dict, Optional, List
from pathlib import Path

# SSL context for secure connections
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fallback: create unverified context if certifi not available
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

from ..utils.colors import Colors


class TranslationService:
    """
    Otomatik çeviri servisi.

    Google Translate API (ücretsiz) kullanarak çeviri yapar.
    Desteklenen diller: en, tr, de, fr, es, it, pt, ru, ja, ko, zh, ar, nl, pl, sv
    """

    # Dil kodları ve isimleri
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'tr': 'Turkish',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'nl': 'Dutch',
        'pl': 'Polish',
        'sv': 'Swedish',
        'da': 'Danish',
        'no': 'Norwegian',
        'fi': 'Finnish',
        'cs': 'Czech',
        'hu': 'Hungarian',
        'ro': 'Romanian',
        'uk': 'Ukrainian',
        'he': 'Hebrew',
        'hi': 'Hindi',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'id': 'Indonesian',
        'ms': 'Malay',
    }

    def __init__(self, source_lang: str = 'en', cache_file: Optional[Path] = None):
        """
        Çeviri servisini başlat.

        Args:
            source_lang: Kaynak dil kodu (varsayılan: en)
            cache_file: Çeviri önbellek dosyası (opsiyonel)
        """
        self.source_lang = source_lang
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, str]] = {}
        self._load_cache()

    def _load_cache(self):
        """Önbelleği dosyadan yükle."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                # Cache file corrupted or unreadable, start fresh
                print(f"{Colors.warning('⚠️')}  Cache load failed ({e.__class__.__name__}), starting fresh")
                self.cache = {}

    def _save_cache(self):
        """Önbelleği dosyaya kaydet."""
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
            except (IOError, OSError, PermissionError) as e:
                # Non-critical: cache save failure doesn't break functionality
                print(f"{Colors.warning('⚠️')}  Cache save failed: {e}")

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Optional[str]:
        """
        Metni hedef dile çevir.

        Args:
            text: Çevrilecek metin
            target_lang: Hedef dil kodu
            source_lang: Kaynak dil kodu (opsiyonel, varsayılan self.source_lang)

        Returns:
            Çevrilmiş metin veya None (hata durumunda)
        """
        if not text or not text.strip():
            return text

        source = source_lang or self.source_lang

        # Aynı dil ise çeviri yapma
        if source == target_lang:
            return text

        # Önbellekte var mı kontrol et
        cache_key = f"{source}:{target_lang}:{text}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Google Translate API (ücretsiz endpoint)
        try:
            translated = self._google_translate(text, source, target_lang)
            if translated:
                self.cache[cache_key] = translated
                self._save_cache()
                return translated
        except Exception as e:
            print(f"{Colors.warning('⚠️')}  Translation error: {e}")

        return None

    def _google_translate(self, text: str, source: str, target: str) -> Optional[str]:
        """
        Google Translate ücretsiz API kullanarak çeviri yap.

        Args:
            text: Çevrilecek metin
            source: Kaynak dil
            target: Hedef dil

        Returns:
            Çevrilmiş metin
        """
        # URL encode
        encoded_text = urllib.parse.quote(text)

        # Google Translate API endpoint (ücretsiz)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl={target}&dt=t&q={encoded_text}"

        try:
            # Request gönder
            request = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )

            with urllib.request.urlopen(request, timeout=10, context=SSL_CONTEXT) as response:
                data = json.loads(response.read().decode('utf-8'))

                # Çeviriyi parse et
                if data and isinstance(data, list) and data[0]:
                    translated_parts = []
                    for part in data[0]:
                        if part and isinstance(part, list) and part[0]:
                            translated_parts.append(part[0])
                    return ''.join(translated_parts)

        except urllib.error.URLError as e:
            print(f"{Colors.error('❌')} Network error: {e}")
        except json.JSONDecodeError as e:
            print(f"{Colors.error('❌')} Parse error: {e}")
        except Exception as e:
            print(f"{Colors.error('❌')} Translation failed: {e}")

        return None

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Birden fazla metni toplu çevir.

        Args:
            texts: Çevrilecek metinler listesi
            target_lang: Hedef dil kodu
            source_lang: Kaynak dil kodu

        Returns:
            {orijinal_metin: çevrilmiş_metin} sözlüğü
        """
        results = {}

        for text in texts:
            translated = self.translate(text, target_lang, source_lang)
            results[text] = translated if translated else text

        return results

    def translate_to_all_languages(
        self,
        text: str,
        target_languages: List[str],
        source_lang: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Metni tüm hedef dillere çevir.

        Args:
            text: Çevrilecek metin
            target_languages: Hedef dil kodları listesi
            source_lang: Kaynak dil kodu

        Returns:
            {dil_kodu: çevrilmiş_metin} sözlüğü
        """
        source = source_lang or self.source_lang
        results = {source: text}  # Kaynak dili ekle

        for lang in target_languages:
            if lang != source:
                translated = self.translate(text, lang, source)
                results[lang] = translated if translated else text

        return results

    def is_supported(self, lang_code: str) -> bool:
        """Dil kodunun desteklenip desteklenmediğini kontrol et."""
        return lang_code in self.SUPPORTED_LANGUAGES

    def get_language_name(self, lang_code: str) -> str:
        """Dil kodundan dil ismini al."""
        return self.SUPPORTED_LANGUAGES.get(lang_code, f'Unknown ({lang_code})')


def translate_key_value(
    key: str,
    value: str,
    source_lang: str,
    target_lang: str,
    translator: Optional[TranslationService] = None
) -> str:
    """
    Localization key değerini çevir.

    Interpolation pattern'leri koruyarak çeviri yapar.
    Örnek: "Hello %@" -> "Merhaba %@"

    Args:
        key: Localization key
        value: Çevrilecek değer
        source_lang: Kaynak dil
        target_lang: Hedef dil
        translator: TranslationService instance (opsiyonel)

    Returns:
        Çevrilmiş değer
    """
    if not value:
        return value

    # Translator oluştur
    if translator is None:
        translator = TranslationService(source_lang=source_lang)

    # Interpolation pattern'leri bul ve koru
    # Swift: %@, %d, %f, %ld, %lld, \(variable)
    # iOS: {{variable}}, {0}, {1}
    patterns = [
        (r'%[@dflsS]', 'PLACEHOLDER'),
        (r'%l?l?d', 'PLACEHOLDER'),
        (r'\\\([^)]+\)', 'INTERPOLATION'),
        (r'\{\{[^}]+\}\}', 'TEMPLATE'),
        (r'\{[0-9]+\}', 'INDEXED'),
    ]

    # Pattern'leri geçici değerlerle değiştir
    placeholders = []
    protected_value = value

    for pattern, prefix in patterns:
        matches = re.findall(pattern, protected_value)
        for i, match in enumerate(matches):
            placeholder = f"__{prefix}{len(placeholders)}__"
            placeholders.append((placeholder, match))
            protected_value = protected_value.replace(match, placeholder, 1)

    # Çevir
    translated = translator.translate(protected_value, target_lang, source_lang)

    if translated:
        # Placeholder'ları geri koy
        for placeholder, original in placeholders:
            translated = translated.replace(placeholder, original)
        return translated

    return value
