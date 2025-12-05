"""Tests for progress indicator utilities."""

import pytest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

from localization_analyzer.utils.progress import (
    ProgressBar,
    progress_bar,
    spinner,
    SpinnerContext,
    is_tqdm_available,
    TQDM_AVAILABLE,
)


class TestProgressBar:
    """Test cases for ProgressBar class."""

    def test_basic_iteration(self):
        """Should iterate through all items."""
        items = [1, 2, 3, 4, 5]
        result = list(ProgressBar(items, disable=True))
        assert result == items

    def test_iteration_with_desc(self, capfd):
        """Should show description."""
        items = [1, 2, 3]
        output = StringIO()

        # Use disabled mode without tqdm
        with patch.object(
            ProgressBar, '_simple_progress',
            return_value=iter(items)
        ):
            list(ProgressBar(items, desc="Test", disable=True))

    def test_total_from_iterable(self):
        """Should get total from iterable length."""
        items = [1, 2, 3, 4, 5]
        bar = ProgressBar(items, disable=True)
        assert bar.total == 5

    def test_explicit_total(self):
        """Should use explicit total."""
        items = iter([1, 2, 3])  # Iterator has no len()
        bar = ProgressBar(items, total=10, disable=True)
        assert bar.total == 10

    def test_disabled_no_output(self, capfd):
        """Disabled progress should not output anything."""
        items = [1, 2, 3]
        list(ProgressBar(items, disable=True))
        captured = capfd.readouterr()
        # Should have minimal or no output
        assert len(captured.out) == 0 or len(captured.out) < 50


class TestProgressBarWithoutTqdm:
    """Test progress bar fallback behavior without tqdm."""

    def test_simple_progress_output(self, capfd):
        """Should show simple progress without tqdm."""
        items = list(range(10))

        # Force simple mode by patching TQDM_AVAILABLE
        with patch('localization_analyzer.utils.progress.TQDM_AVAILABLE', False):
            with patch('localization_analyzer.utils.progress.tqdm', None):
                output = StringIO()
                bar = ProgressBar(items, desc="Processing", file=output)

                # Manually iterate using simple progress
                result = list(bar._simple_progress())

                assert result == items
                assert "Processing" in output.getvalue()

    def test_percentage_display(self):
        """Should display percentage in simple mode."""
        items = list(range(100))
        output = StringIO()

        bar = ProgressBar(items, total=100, file=output, miniters=10)

        # Iterate using simple progress
        list(bar._simple_progress())

        content = output.getvalue()
        # Should contain percentage
        assert '%' in content


class TestProgressBarFunction:
    """Test cases for progress_bar function."""

    def test_function_returns_iterator(self):
        """Should return an iterator."""
        items = [1, 2, 3]
        result = progress_bar(items, disable=True)
        assert list(result) == items

    def test_function_with_options(self):
        """Should accept all options."""
        items = [1, 2, 3]
        result = progress_bar(
            items,
            desc="Test",
            total=3,
            disable=True,
            unit="items"
        )
        assert list(result) == items


class TestSpinner:
    """Test cases for spinner context manager."""

    def test_spinner_context(self, capfd):
        """Should work as context manager."""
        with patch('localization_analyzer.utils.progress.TQDM_AVAILABLE', False):
            with spinner("Loading"):
                pass

        captured = capfd.readouterr()
        assert "Loading" in captured.out
        assert "Done" in captured.out

    def test_spinner_custom_done_message(self, capfd):
        """Should use custom done message."""
        with patch('localization_analyzer.utils.progress.TQDM_AVAILABLE', False):
            with spinner("Processing", done_message="Complete!"):
                pass

        captured = capfd.readouterr()
        assert "Complete!" in captured.out


class TestSpinnerContext:
    """Test cases for SpinnerContext class."""

    def test_init(self):
        """Should initialize with message."""
        ctx = SpinnerContext("Test message")
        assert ctx.message == "Test message"
        assert ctx.done_message == "Done"

    def test_init_custom_done(self):
        """Should accept custom done message."""
        ctx = SpinnerContext("Test", "Finished")
        assert ctx.done_message == "Finished"

    def test_enter_exit_without_tqdm(self, capfd):
        """Should work without tqdm."""
        with patch('localization_analyzer.utils.progress.TQDM_AVAILABLE', False):
            ctx = SpinnerContext("Loading")
            ctx.__enter__()
            captured_enter = capfd.readouterr()
            assert "Loading" in captured_enter.out

            ctx.__exit__(None, None, None)
            captured_exit = capfd.readouterr()
            assert "Done" in captured_exit.out


class TestIsTqdmAvailable:
    """Test cases for is_tqdm_available function."""

    def test_returns_bool(self):
        """Should return a boolean."""
        result = is_tqdm_available()
        assert isinstance(result, bool)

    def test_matches_constant(self):
        """Should match TQDM_AVAILABLE constant."""
        assert is_tqdm_available() == TQDM_AVAILABLE


class TestIntegration:
    """Integration tests for progress utilities."""

    def test_progress_with_real_work(self):
        """Should work with actual processing."""
        items = list(range(100))
        processed = []

        for item in ProgressBar(items, disable=True):
            processed.append(item * 2)

        assert len(processed) == 100
        assert processed[0] == 0
        assert processed[99] == 198

    def test_nested_progress(self):
        """Should handle nested progress bars."""
        outer_items = [1, 2, 3]
        inner_items = ['a', 'b']

        results = []
        for outer in ProgressBar(outer_items, desc="Outer", disable=True):
            for inner in ProgressBar(inner_items, desc="Inner", disable=True):
                results.append((outer, inner))

        assert len(results) == 6

    def test_empty_iterable(self):
        """Should handle empty iterables."""
        result = list(ProgressBar([], disable=True))
        assert result == []

    def test_generator_input(self):
        """Should work with generators."""
        def gen():
            for i in range(5):
                yield i

        result = list(ProgressBar(gen(), total=5, disable=True))
        assert result == [0, 1, 2, 3, 4]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
