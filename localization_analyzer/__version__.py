"""Version information for localization-analyzer."""

__version__ = "1.10.0"
__author__ = "Sezgin Paksoy"
__description__ = "Professional localization analyzer for multi-platform projects"

# Changelog:
# 1.10.0 - Modüler .strings dosya desteği eklendi
#        - lang --add artık modüler dosyalar oluşturuyor (AI.strings, Common.strings vs.)
#        - PosixPath TypeError hatası düzeltildi (list vs single Path)
#        - Module-aware key writing sistemi eklendi
#        - add_key metoduna module parametresi eklendi
#        - _find_module_file helper metodu eklendi
#        - list_languages module_count bilgisi ekliyor
#        - remove_language modüler dosyaları destekliyor
#        - Bare except clause düzeltildi (analyzer.py)
#
# 1.9.3 - add_key metodu düzeltildi
#       - Artık sadece verilen dillere yazıyor (tüm dillere yazmıyor)
#       - Diğer diller için "No translation" uyarısı kaldırıldı
#
# 1.9.2 - translate --force bug düzeltildi
#       - add_key metoduna overwrite parametresi eklendi
#       - --force ile mevcut key'ler artık güncelleniyor
#       - write_localization_entry replace modu entegrasyonu
#
# 1.9.1 - SSL sertifika hatası düzeltildi
#       - certifi paketi ile SSL context desteği
#       - macOS Python SSL hatası çözüldü
#
# 1.9.0 - Sync komutu eklendi
#       - Yeni 'sync' komutu: localization-analyzer sync --translate
#       - Tüm dilleri kaynak dile göre otomatik senkronize et
#       - Eksik key'leri tespit et ve ekle
#       - Otomatik çeviri entegrasyonu (--translate flag)
#       - Yedekleme desteği (backup öncesi)
#       - Dry-run modu ile önizleme
#       - JSON/Markdown rapor export
#       - CI/CD entegrasyonu (--ci flag)
#       - 21 yeni test eklendi
#
# 1.8.0 - Diff komutu eklendi
#       - Yeni 'diff' komutu: localization-analyzer diff --source en --target tr
#       - İki dil arasındaki farkları göster
#       - Eksik, ekstra, çevrilmiş ve çevrilmemiş key'leri tespit et
#       - JSON, Markdown ve TXT export
#       - Renkli terminal çıktısı
#       - CI/CD için --fail-on-missing flag
#       - 17 yeni test eklendi
#
# 1.7.0 - Stats komutu eklendi
#       - Yeni 'stats' komutu: localization-analyzer stats --missing
#       - Dil başına tamamlanma yüzdeleri
#       - Görsel tamamlanma çubuğu
#       - Eksik çeviri detayları (--missing)
#       - JSON export (--json) - CI/CD entegrasyonu için
#       - Markdown export (--markdown) - raporlama için
#       - Threshold bazlı exit code (--ci --threshold 80)
#       - 18 yeni test eklendi
#
# 1.6.0 - Validate komutu eklendi
#       - Yeni 'validate' komutu: localization-analyzer validate --consistency
#       - Syntax doğrulama (eksik noktalı virgül, geçersiz escape)
#       - Key tutarlılığı kontrolü (diller arası eksik key'ler)
#       - Placeholder tutarlılığı (%@, %d sayısı kontrolü)
#       - Duplicate key tespiti
#       - TODO yorum tespiti
#       - 15 yeni test eklendi
#
# 1.5.0 - Yeni dil ekleme + otomatik çeviri entegrasyonu
#       - lang --add --translate: Yeni dil eklerken otomatik çeviri
#       - LanguageManager'a auto_translate parametresi eklendi
#       - Çeviri sırasında progress indicator
#       - Çeviri başarısız olursa kaynak değer + TODO yorumu
#
# 1.4.0 - Dinamik tablo ve modül keşfi
#       - Yeni 'discover' komutu: localization-analyzer discover --all
#       - Auto-discover tables from .strings files (auto_discover_tables=True)
#       - Auto-detect module mapping from project structure
#       - Config'deki default değerler artık boş (proje-agnostik)
#       - --generate flag ile keşfedilen değerler config'e yazılabiliyor
#
# 1.3.0 - Swift Table Name desteği geliştirildi
#       - Config'e 'tables' mapping eklendi (table -> .strings dosya adı)
#       - Config'e 'use_localized_extension' seçeneği eklendi
#       - SwiftAdapter'a get_table_name() metodu eklendi
#       - SwiftAdapter'a get_strings_file_path() metodu eklendi
#       - Hem .localized(from:) hem L10n enum pattern desteği
#
# 1.2.0 - Otomatik çeviri özelliği eklendi (Google Translate API)
#       - Yeni 'translate' komutu: localization-analyzer translate --source en --target tr
#       - Çeviri önbellekleme (.localization_cache/translations.json)
#       - Interpolation pattern'leri korunarak çeviri yapılıyor (%@, \(var) vb.)
#       - 28+ dil desteği
#       - missing --auto seçeneği artık gerçek çeviri yapıyor
#
# 1.1.0 - Dinamik key filtreleme (interpolation pattern'leri artık false positive olarak gösterilmiyor)
#       - Dinamik key'ler ayrı kategori olarak raporlanıyor
#       - Base pattern kontrolü eklendi
