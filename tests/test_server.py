"""Tests for server utilities."""

import pytest
import tempfile
import time
import socket
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from localization_analyzer.utils.server import (
    find_free_port,
    serve_report,
    ReportServer,
    QuietHandler,
    EditableHandler,
)


class TestFindFreePort:
    """Test cases for find_free_port function."""

    def test_returns_int(self):
        """Should return an integer."""
        port = find_free_port()
        assert isinstance(port, int)

    def test_port_in_range(self):
        """Should return port in specified range."""
        port = find_free_port(start=9000, end=9100)
        assert 9000 <= port < 9100

    def test_port_is_available(self):
        """Returned port should be available."""
        port = find_free_port()

        # Try to bind to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            # If we got here, the port was available

    def test_skips_occupied_ports(self):
        """Should skip occupied ports."""
        # Occupy a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            occupied_port = s.getsockname()[1]

            # Should find a different port
            port = find_free_port(start=occupied_port, end=occupied_port + 100)
            assert port != occupied_port

    def test_raises_when_no_port_available(self):
        """Should raise when no port available in range."""
        # Use an impossible range
        with pytest.raises(RuntimeError, match="No free port found"):
            find_free_port(start=1, end=2)  # Port 1 is reserved


class TestQuietHandler:
    """Test cases for QuietHandler."""

    def test_suppresses_logs(self, capsys):
        """Should not print log messages."""
        handler = MagicMock(spec=QuietHandler)
        handler.log_message = QuietHandler.log_message.__get__(handler, QuietHandler)

        # Call log_message
        handler.log_message("Test %s", "message")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestReportServer:
    """Test cases for ReportServer class."""

    def test_init(self):
        """Should initialize with report path."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            server = ReportServer(path)
            assert server.report_path == path
            assert server.open_browser is True
            assert server._server is None
        finally:
            path.unlink()

    def test_init_custom_port(self):
        """Should accept custom port."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            server = ReportServer(path, port=9999)
            assert server.port == 9999
        finally:
            path.unlink()

    def test_url_property(self):
        """Should return correct URL."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            server = ReportServer(path, port=8080)
            assert server.url == f"http://localhost:8080/{path.name}"
        finally:
            path.unlink()

    def test_is_running_initially_false(self):
        """Should report not running initially."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            server = ReportServer(path)
            assert server.is_running is False
        finally:
            path.unlink()

    def test_start_creates_server(self):
        """Should create server on start."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = ReportServer(path, open_browser=False)
                server.start()

                assert server.is_running is True
                assert server._server is not None

                server.stop()
        finally:
            path.unlink()

    def test_start_returns_url(self):
        """Should return URL on start."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = ReportServer(path, open_browser=False)
                url = server.start()

                assert 'http://localhost' in url
                assert path.name in url

                server.stop()
        finally:
            path.unlink()

    def test_start_opens_browser(self):
        """Should open browser when enabled."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open') as mock_open:
                server = ReportServer(path, open_browser=True)
                server.start()

                mock_open.assert_called_once()

                server.stop()
        finally:
            path.unlink()

    def test_start_raises_for_missing_file(self):
        """Should raise for missing report file."""
        server = ReportServer(Path('/nonexistent/report.html'))

        with pytest.raises(FileNotFoundError):
            server.start()

    def test_stop_stops_server(self):
        """Should stop server."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = ReportServer(path, open_browser=False)
                server.start()
                assert server.is_running is True

                server.stop()
                assert server.is_running is False
        finally:
            path.unlink()

    def test_context_manager(self):
        """Should work as context manager."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                with ReportServer(path, open_browser=False) as server:
                    assert server.is_running is True

                assert server.is_running is False
        finally:
            path.unlink()

    def test_multiple_start_calls(self):
        """Should handle multiple start calls."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = ReportServer(path, open_browser=False)
                url1 = server.start()
                url2 = server.start()  # Second call

                assert url1 == url2
                assert server.is_running is True

                server.stop()
        finally:
            path.unlink()


class TestServeReport:
    """Test cases for serve_report function."""

    def test_raises_for_missing_file(self):
        """Should raise for missing report file."""
        with pytest.raises(FileNotFoundError):
            serve_report(Path('/nonexistent/report.html'), blocking=False)

    def test_non_blocking_returns_server(self):
        """Should return server in non-blocking mode."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = serve_report(path, blocking=False, open_browser=False)

                assert server is not None

                # Clean up
                server.shutdown()
        finally:
            path.unlink()

    def test_opens_browser_by_default(self):
        """Should open browser by default."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open') as mock_open:
                server = serve_report(path, blocking=False, open_browser=True)

                mock_open.assert_called_once()

                server.shutdown()
        finally:
            path.unlink()

    def test_custom_port(self):
        """Should use custom port."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            port = find_free_port()

            with patch('webbrowser.open') as mock_open:
                server = serve_report(path, port=port, blocking=False, open_browser=True)

                # Check URL contains custom port
                call_args = mock_open.call_args[0][0]
                assert f":{port}/" in call_args

                server.shutdown()
        finally:
            path.unlink()


class TestEditableHandler:
    """Test cases for EditableHandler class."""

    def test_class_attributes(self):
        """Should have class attributes for editable mode."""
        assert hasattr(EditableHandler, 'allowed_file')
        assert hasattr(EditableHandler, 'update_callback')
        assert hasattr(EditableHandler, 'localization_dir')
        assert hasattr(EditableHandler, 'languages')

    def test_write_to_strings_files_no_dir(self):
        """Should return error when localization_dir is not set."""
        handler = MagicMock(spec=EditableHandler)
        handler._write_to_strings_files = EditableHandler._write_to_strings_files.__get__(handler, EditableHandler)

        # Ensure localization_dir is None
        EditableHandler.localization_dir = None

        result = handler._write_to_strings_files('test.key', {'en': 'Test'})
        assert result['success'] is False
        assert 'Localization dizini' in result['error']

    def test_write_to_strings_files_creates_new_key(self):
        """Should create new key in strings file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loc_dir = Path(tmp_dir)
            en_dir = loc_dir / 'en.lproj'
            en_dir.mkdir()

            strings_file = en_dir / 'Localizable.strings'
            strings_file.write_text('"existing.key" = "Existing";\n', encoding='utf-8')

            # Set up handler
            EditableHandler.localization_dir = loc_dir

            handler = MagicMock(spec=EditableHandler)
            handler._write_to_strings_files = EditableHandler._write_to_strings_files.__get__(handler, EditableHandler)

            result = handler._write_to_strings_files('new.key', {'en': 'New Value'}, 'Localizable')

            assert result['success'] is True
            assert 'en' in result['updated_languages']

            # Verify file content
            content = strings_file.read_text(encoding='utf-8')
            assert '"new.key" = "New Value";' in content
            assert '"existing.key" = "Existing";' in content

    def test_write_to_strings_files_updates_existing_key(self):
        """Should update existing key in strings file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loc_dir = Path(tmp_dir)
            en_dir = loc_dir / 'en.lproj'
            en_dir.mkdir()

            strings_file = en_dir / 'Localizable.strings'
            strings_file.write_text('"test.key" = "Old Value";\n', encoding='utf-8')

            EditableHandler.localization_dir = loc_dir

            handler = MagicMock(spec=EditableHandler)
            handler._write_to_strings_files = EditableHandler._write_to_strings_files.__get__(handler, EditableHandler)

            result = handler._write_to_strings_files('test.key', {'en': 'New Value'}, 'Localizable')

            assert result['success'] is True

            content = strings_file.read_text(encoding='utf-8')
            assert '"test.key" = "New Value";' in content
            assert 'Old Value' not in content


class TestReportServerEditable:
    """Test cases for ReportServer with editable mode."""

    def test_init_editable_mode(self):
        """Should initialize with editable mode parameters."""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html></html>")
            path = Path(f.name)

        try:
            server = ReportServer(
                path,
                editable=True,
                localization_dir=Path('/some/path'),
                languages=['en', 'tr', 'de']
            )
            assert server.editable is True
            assert server.localization_dir == Path('/some/path')
            assert server.languages == ['en', 'tr', 'de']
        finally:
            path.unlink()


class TestServeReportEditable:
    """Test cases for serve_report with editable mode."""

    def test_editable_mode_sets_handler_attributes(self):
        """Should set EditableHandler attributes in editable mode."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            loc_dir = Path(tmp_dir)
            en_dir = loc_dir / 'en.lproj'
            en_dir.mkdir()

            html_file = Path(tmp_dir) / 'report.html'
            html_file.write_text('<html></html>')

            try:
                with patch('webbrowser.open'):
                    server = serve_report(
                        html_file,
                        blocking=False,
                        open_browser=False,
                        editable=True,
                        localization_dir=loc_dir,
                        languages=['en', 'tr']
                    )

                    assert EditableHandler.localization_dir == loc_dir
                    assert EditableHandler.languages == ['en', 'tr']

                    server.shutdown()
            finally:
                pass


class TestServerIntegration:
    """Integration tests for server."""

    def test_serves_file_content(self):
        """Should serve HTML file content."""
        import urllib.request

        html_content = b"<html><body>Test Content</body></html>"

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(html_content)
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = serve_report(path, blocking=False, open_browser=False)
                port = server.server_address[1]

                # Wait for server to start
                time.sleep(0.1)

                # Fetch content
                url = f"http://localhost:{port}/{path.name}"
                with urllib.request.urlopen(url, timeout=5) as response:
                    content = response.read()
                    assert b"Test Content" in content

                server.shutdown()
        finally:
            path.unlink()

    def test_concurrent_requests(self):
        """Should handle concurrent requests."""
        import urllib.request

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b"<html><body>Test</body></html>")
            path = Path(f.name)

        try:
            with patch('webbrowser.open'):
                server = serve_report(path, blocking=False, open_browser=False)
                port = server.server_address[1]

                time.sleep(0.1)

                # Make multiple concurrent requests
                url = f"http://localhost:{port}/{path.name}"

                def fetch():
                    with urllib.request.urlopen(url, timeout=5) as response:
                        return response.read()

                threads = [threading.Thread(target=fetch) for _ in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=10)

                server.shutdown()
        finally:
            path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
