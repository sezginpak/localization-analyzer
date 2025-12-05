"""Structured logging system for localization analyzer."""

import logging
import sys
from typing import Optional
from pathlib import Path
from .colors import Colors


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to console output.

    Uses ANSI colors for different log levels while keeping
    file output clean without color codes.
    """

    # Log level to color mapping
    LEVEL_COLORS = {
        logging.DEBUG: Colors.OKCYAN,
        logging.INFO: Colors.OKGREEN,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.FAIL,
        logging.CRITICAL: Colors.FAIL + Colors.BOLD,
    }

    # Log level to emoji mapping
    LEVEL_ICONS = {
        logging.DEBUG: '',
        logging.INFO: '',
        logging.WARNING: '',
        logging.ERROR: '',
        logging.CRITICAL: '',
    }

    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True, use_icons: bool = True):
        """
        Initialize the formatter.

        Args:
            fmt: Format string for log messages
            use_colors: Whether to use ANSI colors
            use_icons: Whether to use emoji icons
        """
        super().__init__(fmt)
        self.use_colors = use_colors
        self.use_icons = use_icons

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if enabled."""
        # Get the original formatted message
        message = super().format(record)

        if self.use_colors:
            color = self.LEVEL_COLORS.get(record.levelno, '')
            message = f"{color}{message}{Colors.ENDC}"

        if self.use_icons:
            icon = self.LEVEL_ICONS.get(record.levelno, '')
            if icon:
                message = f"{icon} {message}"

        return message


class Logger:
    """
    Main logger class for localization analyzer.

    Provides structured logging with support for:
    - Console output with colors
    - File output (optional)
    - Different verbosity levels
    - Module-specific loggers
    """

    _instance: Optional['Logger'] = None
    _initialized: bool = False

    def __new__(cls) -> 'Logger':
        """Singleton pattern to ensure single logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger (only once due to singleton)."""
        if Logger._initialized:
            return

        self._logger = logging.getLogger('localization_analyzer')
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = []  # Clear any existing handlers

        # Default console handler
        self._console_handler = self._create_console_handler()
        self._logger.addHandler(self._console_handler)

        self._file_handler: Optional[logging.FileHandler] = None

        Logger._initialized = True

    def _create_console_handler(
        self,
        level: int = logging.INFO,
        use_colors: bool = True
    ) -> logging.StreamHandler:
        """
        Create a console handler with optional colors.

        Args:
            level: Minimum log level for console output
            use_colors: Whether to use ANSI colors

        Returns:
            Configured StreamHandler
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = ColoredFormatter(
            fmt='%(message)s',
            use_colors=use_colors,
            use_icons=False
        )
        handler.setFormatter(formatter)

        return handler

    def _create_file_handler(
        self,
        file_path: Path,
        level: int = logging.DEBUG
    ) -> logging.FileHandler:
        """
        Create a file handler for logging to file.

        Args:
            file_path: Path to log file
            level: Minimum log level for file output

        Returns:
            Configured FileHandler
        """
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(file_path, encoding='utf-8')
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        return handler

    def configure(
        self,
        verbose: bool = False,
        quiet: bool = False,
        log_file: Optional[Path] = None,
        use_colors: bool = True
    ) -> None:
        """
        Configure the logger settings.

        Args:
            verbose: Enable verbose (DEBUG) console output
            quiet: Enable quiet mode (WARNING+ only)
            log_file: Optional file path for logging
            use_colors: Whether to use colors in console
        """
        # Determine console log level
        if quiet:
            console_level = logging.WARNING
        elif verbose:
            console_level = logging.DEBUG
        else:
            console_level = logging.INFO

        # Reconfigure console handler
        self._logger.removeHandler(self._console_handler)
        self._console_handler = self._create_console_handler(
            level=console_level,
            use_colors=use_colors
        )
        self._logger.addHandler(self._console_handler)

        # Configure file handler if requested
        if log_file:
            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
            self._file_handler = self._create_file_handler(log_file)
            self._logger.addHandler(self._file_handler)

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Optional module name for hierarchical logging

        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f'localization_analyzer.{name}')
        return self._logger

    # Convenience methods for direct logging
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message."""
        self._logger.critical(msg, *args, **kwargs)

    # Styled logging methods (convenience wrappers)
    def success(self, msg: str) -> None:
        """Log success message (green)."""
        self._logger.info(f"{Colors.success('')} {msg}")

    def fail(self, msg: str) -> None:
        """Log failure message (red)."""
        self._logger.error(f"{Colors.error('')} {msg}")

    def hint(self, msg: str) -> None:
        """Log hint/tip message (cyan)."""
        self._logger.info(f"{Colors.info('')} {msg}")

    def section(self, title: str, char: str = '=', width: int = 70) -> None:
        """Log a section header."""
        self._logger.info(f"\n{Colors.bold(title)}")
        self._logger.info(char * width)

    def progress(self, current: int, total: int, message: str = '') -> None:
        """Log progress update."""
        percentage = (current / total * 100) if total > 0 else 0
        bar_width = 30
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = '' * filled + '' * (bar_width - filled)
        self._logger.info(f"\r[{bar}] {percentage:.1f}% {message}", extra={'end': ''})


# Global logger instance
_logger: Optional[Logger] = None


def get_logger(name: Optional[str] = None) -> Logger:
    """
    Get the global logger instance.

    Args:
        name: Optional module name for hierarchical logging

    Returns:
        Logger instance
    """
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def configure_logging(
    verbose: bool = False,
    quiet: bool = False,
    log_file: Optional[Path] = None,
    use_colors: bool = True
) -> None:
    """
    Configure the global logger.

    Args:
        verbose: Enable verbose (DEBUG) console output
        quiet: Enable quiet mode (WARNING+ only)
        log_file: Optional file path for logging
        use_colors: Whether to use colors in console
    """
    logger = get_logger()
    logger.configure(
        verbose=verbose,
        quiet=quiet,
        log_file=log_file,
        use_colors=use_colors
    )


def reset_logger() -> None:
    """Reset the global logger (mainly for testing)."""
    global _logger
    if _logger is not None:
        # Remove all handlers
        for handler in _logger._logger.handlers[:]:
            handler.close()
            _logger._logger.removeHandler(handler)
    _logger = None
    Logger._instance = None
    Logger._initialized = False
