"""ANSI color codes for terminal output."""


class Colors:
    """ANSI color codes for beautiful terminal output."""

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def success(cls, text: str) -> str:
        """Return text in green color."""
        return f"{cls.OKGREEN}{text}{cls.ENDC}"

    @classmethod
    def error(cls, text: str) -> str:
        """Return text in red color."""
        return f"{cls.FAIL}{text}{cls.ENDC}"

    @classmethod
    def warning(cls, text: str) -> str:
        """Return text in yellow color."""
        return f"{cls.WARNING}{text}{cls.ENDC}"

    @classmethod
    def info(cls, text: str) -> str:
        """Return text in cyan color."""
        return f"{cls.OKCYAN}{text}{cls.ENDC}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Return text in bold."""
        return f"{cls.BOLD}{text}{cls.ENDC}"
