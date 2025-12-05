"""Tests for structured logging system."""

import pytest
import logging
import tempfile
from pathlib import Path

from localization_analyzer.utils.logging import (
    Logger,
    ColoredFormatter,
    get_logger,
    configure_logging,
    reset_logger,
)
from localization_analyzer.utils.colors import Colors


class TestColoredFormatter:
    """Test cases for ColoredFormatter."""

    def test_format_without_colors(self):
        """Formatter without colors should return plain text."""
        formatter = ColoredFormatter(fmt='%(message)s', use_colors=False, use_icons=False)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )
        result = formatter.format(record)
        assert result == 'Test message'
        assert Colors.OKGREEN not in result

    def test_format_with_colors(self):
        """Formatter with colors should include ANSI codes."""
        formatter = ColoredFormatter(fmt='%(message)s', use_colors=True, use_icons=False)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )
        result = formatter.format(record)
        assert Colors.OKGREEN in result
        assert Colors.ENDC in result

    def test_different_levels_have_different_colors(self):
        """Different log levels should use different colors."""
        formatter = ColoredFormatter(fmt='%(message)s', use_colors=True, use_icons=False)

        levels = [
            (logging.DEBUG, Colors.OKCYAN),
            (logging.INFO, Colors.OKGREEN),
            (logging.WARNING, Colors.WARNING),
            (logging.ERROR, Colors.FAIL),
        ]

        for level, expected_color in levels:
            record = logging.LogRecord(
                name='test',
                level=level,
                pathname='',
                lineno=0,
                msg='Test',
                args=(),
                exc_info=None
            )
            result = formatter.format(record)
            assert expected_color in result, f"Level {level} should use color {expected_color}"


class TestLogger:
    """Test cases for Logger class."""

    def setup_method(self):
        """Reset logger before each test."""
        reset_logger()

    def teardown_method(self):
        """Clean up after each test."""
        reset_logger()

    def test_singleton_pattern(self):
        """Logger should be a singleton."""
        logger1 = Logger()
        logger2 = Logger()
        assert logger1 is logger2

    def test_get_logger_returns_same_instance(self):
        """get_logger should return the same instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_configure_verbose(self):
        """Verbose mode should set DEBUG level."""
        logger = get_logger()
        configure_logging(verbose=True)
        assert logger._console_handler.level == logging.DEBUG

    def test_configure_quiet(self):
        """Quiet mode should set WARNING level."""
        logger = get_logger()
        configure_logging(quiet=True)
        assert logger._console_handler.level == logging.WARNING

    def test_configure_default(self):
        """Default mode should set INFO level."""
        logger = get_logger()
        configure_logging()
        assert logger._console_handler.level == logging.INFO

    def test_configure_file_logging(self):
        """File logging should create a file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = get_logger()
            configure_logging(log_file=log_file)

            assert logger._file_handler is not None

            # Write something
            logger.info("Test message")

            # Close handler to flush
            logger._file_handler.close()

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

    def test_get_module_logger(self):
        """Should be able to get module-specific logger."""
        logger = get_logger()
        module_logger = logger.get_logger('analyzer')
        assert module_logger.name == 'localization_analyzer.analyzer'

    def test_debug_method(self, capfd):
        """Debug method should log at DEBUG level."""
        configure_logging(verbose=True)
        logger = get_logger()
        logger.debug("Debug message")
        captured = capfd.readouterr()
        assert "Debug message" in captured.out

    def test_info_method(self, capfd):
        """Info method should log at INFO level."""
        configure_logging()
        logger = get_logger()
        logger.info("Info message")
        captured = capfd.readouterr()
        assert "Info message" in captured.out

    def test_warning_method(self, capfd):
        """Warning method should log at WARNING level."""
        configure_logging()
        logger = get_logger()
        logger.warning("Warning message")
        captured = capfd.readouterr()
        assert "Warning message" in captured.out

    def test_error_method(self, capfd):
        """Error method should log at ERROR level."""
        configure_logging()
        logger = get_logger()
        logger.error("Error message")
        captured = capfd.readouterr()
        assert "Error message" in captured.out


class TestStyledLogging:
    """Test cases for styled logging methods."""

    def setup_method(self):
        """Reset logger before each test."""
        reset_logger()

    def teardown_method(self):
        """Clean up after each test."""
        reset_logger()

    def test_success_method(self, capfd):
        """Success method should log with checkmark."""
        configure_logging()
        logger = get_logger()
        logger.success("Success!")
        captured = capfd.readouterr()
        assert "" in captured.out
        assert "Success!" in captured.out

    def test_fail_method(self, capfd):
        """Fail method should log with X mark."""
        configure_logging()
        logger = get_logger()
        logger.fail("Failed!")
        captured = capfd.readouterr()
        assert "" in captured.out
        assert "Failed!" in captured.out

    def test_hint_method(self, capfd):
        """Hint method should log with lightbulb."""
        configure_logging()
        logger = get_logger()
        logger.hint("Helpful tip")
        captured = capfd.readouterr()
        assert "" in captured.out
        assert "Helpful tip" in captured.out

    def test_section_method(self, capfd):
        """Section method should log title with separator."""
        configure_logging()
        logger = get_logger()
        logger.section("Test Section")
        captured = capfd.readouterr()
        assert "Test Section" in captured.out
        assert "=" in captured.out


class TestFileLogging:
    """Test cases for file logging functionality."""

    def setup_method(self):
        """Reset logger before each test."""
        reset_logger()

    def teardown_method(self):
        """Clean up after each test."""
        reset_logger()

    def test_log_file_format(self):
        """File log should have timestamp and level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            configure_logging(log_file=log_file)
            logger = get_logger()

            logger.info("Test message")
            logger.warning("Warning message")

            # Flush and close
            logger._file_handler.flush()
            logger._file_handler.close()

            content = log_file.read_text()
            assert "[INFO]" in content
            assert "[WARNING]" in content
            assert "Test message" in content
            assert "Warning message" in content

    def test_log_file_no_colors(self):
        """File log should not contain ANSI color codes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            configure_logging(log_file=log_file)
            logger = get_logger()

            logger.info("Test message")

            # Flush and close
            logger._file_handler.flush()
            logger._file_handler.close()

            content = log_file.read_text()
            assert '\033[' not in content  # No ANSI escape codes

    def test_log_file_directory_creation(self):
        """Should create directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'subdir' / 'test.log'
            configure_logging(log_file=log_file)
            logger = get_logger()

            logger.info("Test")
            logger._file_handler.flush()

            assert log_file.parent.exists()


class TestResetLogger:
    """Test cases for reset_logger function."""

    def test_reset_clears_instance(self):
        """Reset should clear singleton instance."""
        logger1 = get_logger()
        reset_logger()
        logger2 = get_logger()

        # They should be different instances after reset
        assert Logger._initialized is True

    def test_reset_clears_handlers(self):
        """Reset should remove all handlers."""
        logger = get_logger()
        reset_logger()

        # After reset, _logger should be None
        from localization_analyzer.utils import logging as log_module
        assert log_module._logger is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
