"""Tests for HTMLReporter."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from localization_analyzer.reports.html_reporter import HTMLReporter
from localization_analyzer.core.analyzer import AnalysisResult
from localization_analyzer.core.health_calculator import HealthScore


class MockItem:
    """Mock hardcoded string item."""
    def __init__(self, text="Test text", file="test.swift", line=10, priority=8):
        self.text = text
        self.file = file
        self.line = line
        self.component = "Label"
        self.category = "UI"
        self.priority = priority
        self.suggested_key = "testKey"


class MockAdapter:
    """Mock framework adapter."""
    pass


@pytest.fixture
def mock_result():
    """Create mock analysis result."""
    health = HealthScore(
        score=85.0,
        grade='B',
        localized_count=100,
        hardcoded_count=15,
        total_strings=115,
        localization_rate=87.0,
        missing_keys_count=5,
        dead_keys_count=3,
        duplicate_count=2
    )

    result = MagicMock(spec=AnalysisResult)
    result.health = health
    result.hardcoded_strings = [
        MockItem("Hello World", "View.swift", 10, 9),
        MockItem("Save", "Button.swift", 20, 8),
    ]
    result.missing_keys = {
        'save.button': ['View.swift', 'Other.swift'],
        'cancel.button': ['Dialog.swift']
    }
    result.dead_keys = {'old.key', 'unused.key'}
    result.duplicates = {
        'Duplicate Text': [MockItem("Duplicate Text", "A.swift", 1), MockItem("Duplicate Text", "B.swift", 2)]
    }
    result.component_stats = {'Label': 10, 'Button': 5}
    result.file_stats = {'View.swift': 8, 'Other.swift': 3}

    return result


@pytest.fixture
def mock_file_manager():
    """Create mock file manager."""
    manager = MagicMock()
    manager.get_language_stats.return_value = {
        'en': {'total_keys': 100, 'missing_keys': 0, 'completion_percent': 100.0},
        'tr': {'total_keys': 95, 'missing_keys': 5, 'completion_percent': 95.0},
        'de': {'total_keys': 80, 'missing_keys': 20, 'completion_percent': 80.0},
    }
    manager.key_modules = {'save.button': 'Common', 'cancel.button': 'Dialog'}
    return manager


@pytest.fixture
def mock_adapter():
    """Create mock adapter."""
    return MockAdapter()


class TestHTMLReporterGenerate:
    """Test cases for HTMLReporter.generate method."""

    def test_generates_html_file(self, mock_result, mock_file_manager, mock_adapter):
        """Should generate HTML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            result_path = HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            assert result_path == output_path
            assert output_path.exists()

    def test_default_output_path(self, mock_result, mock_file_manager, mock_adapter):
        """Should use default path if not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                result_path = HTMLReporter.generate(
                    result=mock_result,
                    file_manager=mock_file_manager,
                    adapter=mock_adapter
                )

                assert result_path.name == 'localization_report.html'
                assert result_path.exists()
            finally:
                os.chdir(original_cwd)

    def test_creates_parent_directories(self, mock_result, mock_file_manager, mock_adapter):
        """Should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'nested' / 'dir' / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            assert output_path.exists()

    def test_custom_title(self, mock_result, mock_file_manager, mock_adapter):
        """Should use custom title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path,
                title="Custom Report Title"
            )

            content = output_path.read_text()
            assert "Custom Report Title" in content


class TestHTMLContent:
    """Test cases for HTML content generation."""

    def test_contains_health_score(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain health score data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert '"score": 85.0' in content
            assert '"grade": "B"' in content

    def test_contains_languages_data(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain languages data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert '"en"' in content
            assert '"tr"' in content
            assert '"de"' in content

    def test_contains_hardcoded_strings(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain hardcoded strings data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert 'Hello World' in content
            assert 'View.swift' in content

    def test_contains_missing_keys(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain missing keys data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert 'save.button' in content
            assert 'cancel.button' in content

    def test_contains_dead_keys(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain dead keys data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            # Dead keys should be in JSON data
            assert 'old.key' in content or 'unused.key' in content

    def test_contains_duplicates(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain duplicates data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert 'Duplicate Text' in content


class TestHTMLStructure:
    """Test cases for HTML structure."""

    def test_valid_html_structure(self, mock_result, mock_file_manager, mock_adapter):
        """Should generate valid HTML structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert '<!DOCTYPE html>' in content
            assert '<html' in content
            assert '</html>' in content
            assert '<head>' in content
            assert '</head>' in content
            assert '<body>' in content
            assert '</body>' in content

    def test_contains_css(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain CSS styles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert '<style>' in content
            assert '</style>' in content
            # Check for dark mode support
            assert 'data-theme="dark"' in content

    def test_contains_javascript(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain JavaScript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            assert '<script>' in content
            assert '</script>' in content
            assert 'reportData' in content

    def test_contains_interactive_elements(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain interactive elements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            # Search inputs
            assert 'hardcodedSearch' in content
            assert 'missingSearch' in content
            # Theme toggle
            assert 'themeToggle' in content
            # Export button
            assert 'exportJSON' in content


class TestPrepareReportData:
    """Test cases for _prepare_report_data method."""

    def test_returns_dict(self, mock_result, mock_file_manager, mock_adapter):
        """Should return dictionary."""
        data = HTMLReporter._prepare_report_data(
            mock_result, mock_file_manager, mock_adapter
        )

        assert isinstance(data, dict)

    def test_contains_metadata(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain metadata."""
        data = HTMLReporter._prepare_report_data(
            mock_result, mock_file_manager, mock_adapter
        )

        assert 'metadata' in data
        assert 'generated_at' in data['metadata']
        assert 'framework' in data['metadata']

    def test_contains_health(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain health data."""
        data = HTMLReporter._prepare_report_data(
            mock_result, mock_file_manager, mock_adapter
        )

        assert 'health' in data
        assert data['health']['score'] == 85.0
        assert data['health']['grade'] == 'B'

    def test_contains_all_sections(self, mock_result, mock_file_manager, mock_adapter):
        """Should contain all data sections."""
        data = HTMLReporter._prepare_report_data(
            mock_result, mock_file_manager, mock_adapter
        )

        expected_keys = [
            'metadata', 'health', 'languages', 'hardcoded_strings',
            'missing_keys', 'dead_keys', 'duplicates',
            'component_stats', 'file_stats', 'recommendations'
        ]

        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


class TestSpecialCharacters:
    """Test cases for special character handling."""

    def test_escapes_html_in_text(self, mock_result, mock_file_manager, mock_adapter):
        """Should escape HTML characters in text."""
        mock_result.hardcoded_strings = [
            MockItem("<script>alert('xss')</script>", "test.swift", 1, 9)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            # Raw script tag should not appear in HTML
            # It should be escaped in the JSON data
            assert "<script>alert" not in content.split('const reportData')[0]

    def test_handles_unicode(self, mock_result, mock_file_manager, mock_adapter):
        """Should handle unicode characters."""
        mock_result.hardcoded_strings = [
            MockItem("Türkçe karakter: ğüşıöç", "test.swift", 1, 9),
            MockItem("Emoji: 🎉🚀", "test.swift", 2, 8),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=mock_result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            content = output_path.read_text()
            # Check that unicode is preserved in JSON
            assert 'ğüşıöç' in content
            # Emojis should be in the content


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_results(self, mock_file_manager, mock_adapter):
        """Should handle empty results."""
        health = HealthScore(
            score=100.0, grade='A+', localized_count=0, hardcoded_count=0,
            total_strings=0, localization_rate=100.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )

        result = MagicMock(spec=AnalysisResult)
        result.health = health
        result.hardcoded_strings = []
        result.missing_keys = {}
        result.dead_keys = set()
        result.duplicates = {}
        result.component_stats = {}
        result.file_stats = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            assert output_path.exists()
            content = output_path.read_text()
            assert '"score": 100.0' in content

    def test_large_dataset(self, mock_file_manager, mock_adapter):
        """Should handle large datasets."""
        health = HealthScore(
            score=50.0, grade='F', localized_count=500, hardcoded_count=500,
            total_strings=1000, localization_rate=50.0, missing_keys_count=100,
            dead_keys_count=200, duplicate_count=50
        )

        result = MagicMock(spec=AnalysisResult)
        result.health = health
        result.hardcoded_strings = [MockItem(f"Text {i}", f"file{i}.swift", i, 5) for i in range(500)]
        result.missing_keys = {f"key{i}": [f"file{i}.swift"] for i in range(100)}
        result.dead_keys = {f"dead{i}" for i in range(200)}
        result.duplicates = {}
        result.component_stats = {}
        result.file_stats = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.html'

            HTMLReporter.generate(
                result=result,
                file_manager=mock_file_manager,
                adapter=mock_adapter,
                output_path=output_path
            )

            assert output_path.exists()
            # File should be reasonable size (less than 5MB for 500 items)
            assert output_path.stat().st_size < 5 * 1024 * 1024


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
