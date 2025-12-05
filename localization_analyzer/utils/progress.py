"""Progress indicator utilities with optional tqdm support."""

from typing import Iterator, TypeVar, Optional, Iterable, Callable
import sys

T = TypeVar('T')

# Try to import tqdm, but don't require it
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None


class ProgressBar:
    """
    Progress bar wrapper that uses tqdm if available, otherwise falls back to simple output.

    This provides a consistent interface for progress indicators regardless of
    whether tqdm is installed.

    Usage:
        # Simple iteration with progress
        for item in ProgressBar(items, desc="Processing"):
            process(item)

        # With total count
        for item in ProgressBar(items, desc="Processing", total=100):
            process(item)

        # Disable progress output
        for item in ProgressBar(items, desc="Processing", disable=True):
            process(item)
    """

    def __init__(
        self,
        iterable: Iterable[T],
        desc: Optional[str] = None,
        total: Optional[int] = None,
        disable: bool = False,
        unit: str = 'it',
        leave: bool = True,
        file: Optional[object] = None,
        miniters: int = 1,
    ):
        """
        Initialize progress bar.

        Args:
            iterable: Items to iterate over
            desc: Description prefix for the progress bar
            total: Total number of items (if not provided, will try len())
            disable: If True, don't show progress output
            unit: Unit of items (e.g., 'files', 'keys')
            leave: Whether to leave progress bar after completion
            file: File object for output (default: sys.stderr)
            miniters: Minimum iterations between updates
        """
        self.iterable = iterable
        self.desc = desc
        self.total = total
        self.disable = disable
        self.unit = unit
        self.leave = leave
        self.file = file or sys.stderr
        self.miniters = miniters

        # Try to get total from iterable
        if self.total is None:
            try:
                self.total = len(iterable)  # type: ignore
            except (TypeError, AttributeError):
                pass

        # Track progress
        self._current = 0
        self._last_print = 0

    def __iter__(self) -> Iterator[T]:
        """Iterate with progress indication."""
        if self.disable:
            yield from self.iterable
            return

        if TQDM_AVAILABLE and tqdm is not None:
            # Use tqdm
            yield from tqdm(
                self.iterable,
                desc=self.desc,
                total=self.total,
                unit=self.unit,
                leave=self.leave,
                file=self.file,
                miniters=self.miniters,
            )
        else:
            # Fallback to simple progress output
            yield from self._simple_progress()

    def _simple_progress(self) -> Iterator[T]:
        """Simple progress output without tqdm."""
        if self.desc:
            print(f"{self.desc}...", file=self.file, flush=True)

        for item in self.iterable:
            self._current += 1

            # Print progress every miniters items or at completion
            should_print = (
                self._current - self._last_print >= self.miniters or
                (self.total and self._current >= self.total)
            )

            if should_print and self.total:
                percent = (self._current / self.total) * 100
                # Update on same line
                print(
                    f"\r  {self._current}/{self.total} ({percent:.1f}%)",
                    end='',
                    file=self.file,
                    flush=True
                )
                self._last_print = self._current

            yield item

        # Print newline at end
        if self.total and self.leave:
            print(file=self.file)


def progress_bar(
    iterable: Iterable[T],
    desc: Optional[str] = None,
    total: Optional[int] = None,
    disable: bool = False,
    unit: str = 'it',
) -> Iterator[T]:
    """
    Convenience function for creating progress bars.

    Args:
        iterable: Items to iterate over
        desc: Description prefix
        total: Total number of items
        disable: If True, don't show progress
        unit: Unit of items

    Returns:
        Iterator with progress indication

    Example:
        for file in progress_bar(files, desc="Analyzing", unit="files"):
            analyze(file)
    """
    return iter(ProgressBar(
        iterable,
        desc=desc,
        total=total,
        disable=disable,
        unit=unit,
    ))


def spinner(
    message: str,
    done_message: Optional[str] = None,
) -> 'SpinnerContext':
    """
    Context manager for showing a spinner during long operations.

    Args:
        message: Message to show while spinning
        done_message: Message to show when done (optional)

    Returns:
        SpinnerContext manager

    Example:
        with spinner("Loading..."):
            load_data()
    """
    return SpinnerContext(message, done_message)


class SpinnerContext:
    """
    Context manager that shows a spinner or simple status message.

    Uses tqdm's spinner if available, otherwise shows simple messages.
    """

    def __init__(self, message: str, done_message: Optional[str] = None):
        """
        Initialize spinner context.

        Args:
            message: Message to show while spinning
            done_message: Message to show when done
        """
        self.message = message
        self.done_message = done_message or "Done"
        self._bar = None

    def __enter__(self) -> 'SpinnerContext':
        """Start the spinner."""
        if TQDM_AVAILABLE and tqdm is not None:
            self._bar = tqdm(
                total=0,
                desc=self.message,
                bar_format='{desc}',
                leave=False,
            )
        else:
            print(f"{self.message}...", end='', flush=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the spinner."""
        if self._bar is not None:
            self._bar.close()
            print(f"{self.message}... {self.done_message}")
        else:
            print(f" {self.done_message}")

    def update(self, message: str) -> None:
        """Update the spinner message."""
        if self._bar is not None:
            self._bar.set_description(message)
        # For simple mode, we don't update mid-operation


def is_tqdm_available() -> bool:
    """
    Check if tqdm is available.

    Returns:
        True if tqdm is installed, False otherwise
    """
    return TQDM_AVAILABLE
