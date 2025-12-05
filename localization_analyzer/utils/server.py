"""Simple HTTP server for serving HTML reports with edit capabilities."""

import http.server
import socketserver
import webbrowser
import threading
import socket
import json
import re
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from functools import partial
from urllib.parse import parse_qs, urlparse

from .colors import Colors


def find_free_port(start: int = 8000, end: int = 9000) -> int:
    """
    Boş bir port bulur.

    Args:
        start: Başlangıç port numarası
        end: Bitiş port numarası

    Returns:
        Kullanılabilir port numarası

    Raises:
        RuntimeError: Boş port bulunamazsa
    """
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


class EditableHandler(http.server.SimpleHTTPRequestHandler):
    """
    Düzenlenebilir HTML rapor handler'ı.

    Özellikler:
    - Sadece belirtilen dosyaya erişim izni verir (path traversal koruması)
    - POST /api/update-key: Tek key güncelleme
    - POST /api/update-keys: Toplu key güncelleme
    - GET /api/languages: Dil listesi
    - Log mesajlarını bastırır
    """

    allowed_file: Optional[str] = None
    update_callback: Optional[Callable] = None
    localization_dir: Optional[Path] = None
    languages: list = []
    adapter = None

    def __init__(self, *args, directory: str = None, allowed_file: str = None, **kwargs):
        self.directory = directory
        if allowed_file:
            EditableHandler.allowed_file = allowed_file
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        """GET isteklerini işler."""
        parsed = urlparse(self.path)
        path = parsed.path.lstrip('/')

        # API endpoint'leri
        if path == 'api/languages':
            self._handle_get_languages()
            return

        # Query string varsa kaldır
        if '?' in path:
            path = path.split('?')[0]

        # Sadece izin verilen dosyaya erişim
        if EditableHandler.allowed_file and path != EditableHandler.allowed_file:
            self.send_error(403, "Forbidden: Access denied")
            return

        # Path traversal kontrolü (../ saldırıları)
        if '..' in path or path.startswith('/'):
            self.send_error(403, "Forbidden: Invalid path")
            return

        super().do_GET()

    def do_POST(self):
        """POST isteklerini işler."""
        parsed = urlparse(self.path)
        path = parsed.path.lstrip('/')

        if path == 'api/update-key':
            self._handle_update_key()
        elif path == 'api/update-keys':
            self._handle_update_keys()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """CORS preflight için OPTIONS handler."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_cors_headers(self):
        """CORS header'larını ekler."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json_response(self, data: dict, status: int = 200):
        """JSON yanıtı gönderir."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _handle_get_languages(self):
        """Dil listesini döndürür."""
        self._send_json_response({
            'success': True,
            'languages': EditableHandler.languages
        })

    def _handle_update_key(self):
        """Tek bir key'i günceller."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            key = data.get('key')
            translations = data.get('translations', {})
            module = data.get('module', 'Localizable')

            if not key or not translations:
                self._send_json_response({
                    'success': False,
                    'error': 'Key ve translations gerekli'
                }, 400)
                return

            # Callback ile güncelle
            if EditableHandler.update_callback:
                result = EditableHandler.update_callback(
                    key=key,
                    translations=translations,
                    module=module
                )
                self._send_json_response(result)
            else:
                # Doğrudan dosyaya yaz
                result = self._write_to_strings_files(key, translations, module)
                self._send_json_response(result)

        except json.JSONDecodeError:
            self._send_json_response({
                'success': False,
                'error': 'Geçersiz JSON'
            }, 400)
        except Exception as e:
            self._send_json_response({
                'success': False,
                'error': str(e)
            }, 500)

    def _handle_update_keys(self):
        """Birden fazla key'i toplu günceller."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            updates = data.get('updates', [])
            if not updates:
                self._send_json_response({
                    'success': False,
                    'error': 'Updates listesi gerekli'
                }, 400)
                return

            results = []
            for update in updates:
                key = update.get('key')
                translations = update.get('translations', {})
                module = update.get('module', 'Localizable')

                if key and translations:
                    if EditableHandler.update_callback:
                        result = EditableHandler.update_callback(
                            key=key,
                            translations=translations,
                            module=module
                        )
                    else:
                        result = self._write_to_strings_files(key, translations, module)
                    results.append({
                        'key': key,
                        'success': result.get('success', False),
                        'error': result.get('error')
                    })

            success_count = sum(1 for r in results if r['success'])
            self._send_json_response({
                'success': True,
                'total': len(results),
                'success_count': success_count,
                'failed_count': len(results) - success_count,
                'results': results
            })

        except json.JSONDecodeError:
            self._send_json_response({
                'success': False,
                'error': 'Geçersiz JSON'
            }, 400)
        except Exception as e:
            self._send_json_response({
                'success': False,
                'error': str(e)
            }, 500)

    def _write_to_strings_files(
        self,
        key: str,
        translations: Dict[str, str],
        module: str = 'Localizable'
    ) -> Dict[str, Any]:
        """
        Key'i .strings dosyalarına yazar.

        Args:
            key: Localization key
            translations: {lang_code: value} dict
            module: .strings dosya adı (uzantısız)

        Returns:
            İşlem sonucu dict
        """
        if not EditableHandler.localization_dir:
            return {'success': False, 'error': 'Localization dizini ayarlanmamış'}

        loc_dir = EditableHandler.localization_dir
        updated_langs = []
        errors = []

        for lang, value in translations.items():
            # Dil dizinini bul
            lang_dir = loc_dir / f"{lang}.lproj"
            if not lang_dir.exists():
                errors.append(f"{lang}: Dil dizini bulunamadı")
                continue

            # .strings dosyasını bul
            strings_file = lang_dir / f"{module}.strings"
            if not strings_file.exists():
                # Dosya yoksa oluştur
                strings_file.touch()

            try:
                # Dosyayı oku
                content = strings_file.read_text(encoding='utf-8')

                # Key zaten var mı kontrol et
                # Pattern: "key" = "value";
                pattern = rf'^"{re.escape(key)}"\s*=\s*"[^"]*";\s*$'
                if re.search(pattern, content, re.MULTILINE):
                    # Key'i güncelle
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    new_line = f'"{key}" = "{escaped_value}";'
                    content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
                else:
                    # Yeni key ekle
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    new_line = f'"{key}" = "{escaped_value}";\n'
                    content = content.rstrip() + '\n' + new_line

                # Dosyaya yaz
                strings_file.write_text(content, encoding='utf-8')
                updated_langs.append(lang)

            except Exception as e:
                errors.append(f"{lang}: {str(e)}")

        if updated_langs:
            return {
                'success': True,
                'updated_languages': updated_langs,
                'errors': errors if errors else None
            }
        else:
            return {
                'success': False,
                'error': 'Hiçbir dil güncellenemedi',
                'details': errors
            }

    def log_message(self, format, *args):
        """Log mesajlarını bastırır."""
        pass


# Backward compatibility aliases
SecureHandler = EditableHandler
QuietHandler = EditableHandler


def serve_report(
    report_path: Path,
    port: Optional[int] = None,
    open_browser: bool = True,
    blocking: bool = True,
    editable: bool = False,
    localization_dir: Optional[Path] = None,
    languages: Optional[list] = None
) -> Optional[socketserver.TCPServer]:
    """
    HTML raporu local server ile serve eder.

    Args:
        report_path: HTML dosyasının yolu
        port: Port numarası (None ise otomatik bulunur)
        open_browser: Tarayıcıda otomatik aç
        blocking: True ise server'ı durdurana kadar bekle
        editable: True ise düzenleme API'leri aktif olur
        localization_dir: Localization dosyalarının bulunduğu dizin
        languages: Desteklenen dil listesi

    Returns:
        Blocking=False ise server nesnesi, aksi halde None

    Raises:
        FileNotFoundError: Rapor dosyası bulunamazsa
    """
    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    # Port bul
    if port is None:
        port = find_free_port()

    # Handler ayarları
    directory = str(report_path.parent)
    filename = report_path.name

    # Editable mod için ayarlar
    if editable and localization_dir:
        EditableHandler.localization_dir = Path(localization_dir)
        EditableHandler.languages = languages or []

    handler = partial(EditableHandler, directory=directory, allowed_file=filename)

    # Server oluştur
    server = socketserver.TCPServer(("", port), handler)
    server.allow_reuse_address = True

    # URL
    url = f"http://localhost:{port}/{filename}"

    print(f"\n{Colors.success('✓')} Server başlatıldı: {Colors.info(url)}")
    if editable:
        print(f"{Colors.info('✏️')} Düzenleme modu aktif")

    # Tarayıcı aç
    if open_browser:
        webbrowser.open(url)
        print(f"{Colors.info('ℹ')} Tarayıcı açılıyor...")

    if blocking:
        print(f"{Colors.warning('⚠')} Durdurmak için Ctrl+C basın\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print(f"\n{Colors.info('ℹ')} Server durduruluyor...")
            server.shutdown()
        return None
    else:
        # Non-blocking mod - arka planda çalıştır
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server


class ReportServer:
    """
    HTML rapor server yöneticisi.

    Kullanım:
        server = ReportServer(report_path)
        server.start()
        # ... kullanıcı işlemlerini yap ...
        server.stop()

    Veya context manager ile:
        with ReportServer(report_path) as server:
            # Server çalışıyor
            input("Enter'a basın...")

    Düzenleme modlu kullanım:
        server = ReportServer(
            report_path,
            editable=True,
            localization_dir=Path('./Resources'),
            languages=['en', 'tr', 'de']
        )
    """

    def __init__(
        self,
        report_path: Path,
        port: Optional[int] = None,
        open_browser: bool = True,
        editable: bool = False,
        localization_dir: Optional[Path] = None,
        languages: Optional[list] = None
    ):
        """
        Server'ı başlatır.

        Args:
            report_path: HTML dosyasının yolu
            port: Port numarası (None ise otomatik)
            open_browser: Tarayıcıda otomatik aç
            editable: Düzenleme modu aktif mi
            localization_dir: Localization dosyalarının bulunduğu dizin
            languages: Desteklenen dil listesi
        """
        self.report_path = Path(report_path)
        self.port = port or find_free_port()
        self.open_browser = open_browser
        self.editable = editable
        self.localization_dir = Path(localization_dir) if localization_dir else None
        self.languages = languages or []
        self._server: Optional[socketserver.TCPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """Server URL'ini döndürür."""
        return f"http://localhost:{self.port}/{self.report_path.name}"

    @property
    def is_running(self) -> bool:
        """Server'ın çalışıp çalışmadığını döndürür."""
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        """
        Server'ı başlatır.

        Returns:
            Server URL'i
        """
        if self.is_running:
            return self.url

        if not self.report_path.exists():
            raise FileNotFoundError(f"Report not found: {self.report_path}")

        # Handler ve server
        directory = str(self.report_path.parent)
        filename = self.report_path.name

        # Editable mod için ayarlar
        if self.editable and self.localization_dir:
            EditableHandler.localization_dir = self.localization_dir
            EditableHandler.languages = self.languages

        handler = partial(EditableHandler, directory=directory, allowed_file=filename)
        self._server = socketserver.TCPServer(("", self.port), handler)
        self._server.allow_reuse_address = True

        # Thread'de başlat
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        print(f"\n{Colors.success('✓')} Server başlatıldı: {Colors.info(self.url)}")
        if self.editable:
            print(f"{Colors.info('✏️')} Düzenleme modu aktif")

        # Tarayıcı aç
        if self.open_browser:
            webbrowser.open(self.url)
            print(f"{Colors.info('ℹ')} Tarayıcı açılıyor...")

        return self.url

    def stop(self):
        """Server'ı durdurur."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
            print(f"{Colors.info('ℹ')} Server durduruldu")

    def __enter__(self) -> 'ReportServer':
        """Context manager giriş."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkış."""
        self.stop()

    def wait(self):
        """Kullanıcı Ctrl+C yapana kadar bekler."""
        print(f"{Colors.warning('⚠')} Durdurmak için Ctrl+C basın\n")
        try:
            while self.is_running:
                self._thread.join(timeout=0.5)
        except KeyboardInterrupt:
            print(f"\n{Colors.info('ℹ')} Server durduruluyor...")
            self.stop()
