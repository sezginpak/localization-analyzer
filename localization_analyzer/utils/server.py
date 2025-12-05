"""Simple HTTP server for serving HTML reports."""

import http.server
import socketserver
import webbrowser
import threading
import socket
from pathlib import Path
from typing import Optional
from functools import partial

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


class SecureHandler(http.server.SimpleHTTPRequestHandler):
    """
    Güvenli HTTP request handler.

    - Sadece belirtilen dosyaya erişim izni verir (path traversal koruması)
    - Log mesajlarını bastırır
    """

    allowed_file: Optional[str] = None

    def __init__(self, *args, directory: str = None, allowed_file: str = None, **kwargs):
        self.directory = directory
        if allowed_file:
            SecureHandler.allowed_file = allowed_file
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        """GET isteklerini sadece izin verilen dosya için işler."""
        # Path traversal koruması: Sadece izin verilen dosyaya erişim
        requested_path = self.path.lstrip('/')

        # Query string varsa kaldır
        if '?' in requested_path:
            requested_path = requested_path.split('?')[0]

        # Sadece izin verilen dosyaya erişim
        if SecureHandler.allowed_file and requested_path != SecureHandler.allowed_file:
            self.send_error(403, "Forbidden: Access denied")
            return

        # Path traversal kontrolü (../ saldırıları)
        if '..' in requested_path or requested_path.startswith('/'):
            self.send_error(403, "Forbidden: Invalid path")
            return

        super().do_GET()

    def log_message(self, format, *args):
        """Log mesajlarını bastırır."""
        pass


# Backward compatibility alias
QuietHandler = SecureHandler


def serve_report(
    report_path: Path,
    port: Optional[int] = None,
    open_browser: bool = True,
    blocking: bool = True
) -> Optional[socketserver.TCPServer]:
    """
    HTML raporu local server ile serve eder.

    Args:
        report_path: HTML dosyasının yolu
        port: Port numarası (None ise otomatik bulunur)
        open_browser: Tarayıcıda otomatik aç
        blocking: True ise server'ı durdurana kadar bekle

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

    # Handler oluştur (sadece rapor dosyasına erişim izni ver)
    directory = str(report_path.parent)
    filename = report_path.name
    handler = partial(SecureHandler, directory=directory, allowed_file=filename)

    # Server oluştur
    server = socketserver.TCPServer(("", port), handler)
    server.allow_reuse_address = True

    # URL
    url = f"http://localhost:{port}/{filename}"

    print(f"\n{Colors.success('✓')} Server başlatıldı: {Colors.info(url)}")

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
    """

    def __init__(
        self,
        report_path: Path,
        port: Optional[int] = None,
        open_browser: bool = True
    ):
        """
        Server'ı başlatır.

        Args:
            report_path: HTML dosyasının yolu
            port: Port numarası (None ise otomatik)
            open_browser: Tarayıcıda otomatik aç
        """
        self.report_path = Path(report_path)
        self.port = port or find_free_port()
        self.open_browser = open_browser
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

        # Handler ve server (sadece rapor dosyasına erişim izni ver)
        directory = str(self.report_path.parent)
        filename = self.report_path.name
        handler = partial(SecureHandler, directory=directory, allowed_file=filename)
        self._server = socketserver.TCPServer(("", self.port), handler)
        self._server.allow_reuse_address = True

        # Thread'de başlat
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        print(f"\n{Colors.success('✓')} Server başlatıldı: {Colors.info(self.url)}")

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
