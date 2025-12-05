"""Tests for LocalizationAnalyzer core functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from localization_analyzer.core.analyzer import (
    LocalizationAnalyzer,
    AnalysisResult,
    DYNAMIC_KEY_PATTERNS,
)
from localization_analyzer.frameworks.swift import SwiftAdapter
from localization_analyzer.frameworks.base import HardcodedString, LocalizedUsage


class TestAnalysisResult:
    """Test cases for AnalysisResult dataclass."""

    def test_default_values(self):
        """AnalysisResult should have sensible defaults."""
        health = MagicMock()
        result = AnalysisResult(health=health)

        assert result.health == health
        assert result.hardcoded_strings == []
        assert result.localized_usages == []
        assert result.used_keys == set()
        assert result.dead_keys == set()
        assert result.missing_keys == {}
        assert result.dynamic_keys == {}
        assert result.duplicates == {}

    def test_with_data(self):
        """AnalysisResult should store provided data."""
        health = MagicMock()
        hardcoded = [MagicMock()]
        used_keys = {'key1', 'key2'}
        missing_keys = {'missing': ['file.swift']}

        result = AnalysisResult(
            health=health,
            hardcoded_strings=hardcoded,
            used_keys=used_keys,
            missing_keys=missing_keys
        )

        assert result.hardcoded_strings == hardcoded
        assert result.used_keys == used_keys
        assert result.missing_keys == missing_keys


class TestDynamicKeyPatterns:
    """Test cases for dynamic key pattern detection."""

    def test_swift_interpolation_pattern(self):
        """Should detect Swift string interpolation."""
        import re
        pattern = DYNAMIC_KEY_PATTERNS[0]  # \\\(
        assert re.search(pattern, r'activity.\(id)')
        assert not re.search(pattern, 'activity.work')

    def test_javascript_template_pattern(self):
        """Should detect JavaScript template literals."""
        import re
        pattern = DYNAMIC_KEY_PATTERNS[1]  # \$\{
        assert re.search(pattern, 'user.${userId}')
        assert not re.search(pattern, 'user.name')

    def test_positional_placeholder_pattern(self):
        """Should detect positional placeholders."""
        import re
        pattern = DYNAMIC_KEY_PATTERNS[3]  # \{[0-9]+\}
        assert re.search(pattern, 'item.{0}.title')
        assert not re.search(pattern, 'item.title')

    def test_format_specifier_pattern(self):
        """Should detect format specifiers."""
        import re
        pattern = DYNAMIC_KEY_PATTERNS[5]  # %[@dsfg]
        assert re.search(pattern, 'Hello %@')
        assert re.search(pattern, 'Count: %d')
        assert not re.search(pattern, 'Hello World')


class TestLocalizationAnalyzer:
    """Test cases for LocalizationAnalyzer class."""

    def create_test_project(self, tmpdir):
        """Create a minimal test project structure."""
        project_dir = Path(tmpdir)

        # Create source file
        source_dir = project_dir / 'Sources'
        source_dir.mkdir()

        swift_file = source_dir / 'Test.swift'
        swift_file.write_text('''
import UIKit

class TestView: UIView {
    let label = UILabel()

    func setup() {
        // Localized string
        label.text = String(localized: "test.label")

        // Hardcoded string (should be detected)
        let title = "Hello World"
    }
}
''')

        # Create localization files
        resources_dir = project_dir / 'Resources'
        en_lproj = resources_dir / 'en.lproj'
        en_lproj.mkdir(parents=True)

        strings_file = en_lproj / 'Localizable.strings'
        strings_file.write_text('''
"test.label" = "Test Label";
"unused.key" = "This key is not used";
''')

        return project_dir

    def test_init(self):
        """Analyzer should initialize with required parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()

            analyzer = LocalizationAnalyzer(
                project_dir=project_dir,
                adapter=adapter
            )

            assert analyzer.project_dir == project_dir
            assert analyzer.adapter == adapter
            assert analyzer.use_threads is True

    def test_init_without_threads(self):
        """Analyzer should respect use_threads=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()

            analyzer = LocalizationAnalyzer(
                project_dir=project_dir,
                adapter=adapter,
                use_threads=False
            )

            assert analyzer.use_threads is False

    def test_is_dynamic_key_true(self):
        """Should detect dynamic keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            assert analyzer._is_dynamic_key(r'activity.\(id)') is True
            assert analyzer._is_dynamic_key('user.${userId}') is True
            assert analyzer._is_dynamic_key('item.{0}.title') is True

    def test_is_dynamic_key_false(self):
        """Should not flag static keys as dynamic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            assert analyzer._is_dynamic_key('activity.work') is False
            assert analyzer._is_dynamic_key('user.name') is False
            assert analyzer._is_dynamic_key('simple.key') is False

    def test_find_source_files(self):
        """Should find Swift source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            analyzer._find_source_files(verbose=False)

            assert len(analyzer.source_files) >= 1
            assert any(f.suffix == '.swift' for f in analyzer.source_files)

    def test_analyze_returns_result(self):
        """Analyze should return AnalysisResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            result = analyzer.analyze(verbose=False)

            assert isinstance(result, AnalysisResult)
            assert result.health is not None
            assert hasattr(result.health, 'score')

    def test_analyze_finds_hardcoded_strings(self):
        """Analyze should find hardcoded strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            result = analyzer.analyze(verbose=False)

            # Should find "Hello World" as hardcoded
            hardcoded_texts = [h.text for h in result.hardcoded_strings]
            assert any('Hello' in text for text in hardcoded_texts)

    def test_analyze_finds_used_keys(self):
        """Analyze should track used localization keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            result = analyzer.analyze(verbose=False)

            assert 'test.label' in result.used_keys

    def test_analyze_finds_dead_keys(self):
        """Analyze should find unused keys in strings files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            result = analyzer.analyze(verbose=False)

            assert 'unused.key' in result.dead_keys

    def test_analyze_single_threaded(self):
        """Analyze should work in single-threaded mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(
                project_dir, adapter, use_threads=False
            )

            result = analyzer.analyze(verbose=False)

            assert isinstance(result, AnalysisResult)

    def test_analyze_file_with_encoding_error(self):
        """Should handle files with encoding errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_dir.mkdir(exist_ok=True)

            # Create a file with invalid UTF-8
            bad_file = project_dir / 'bad.swift'
            bad_file.write_bytes(b'\xff\xfe Invalid UTF-8')

            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Should not raise
            analyzer._analyze_file(bad_file)


class TestHasBasePatternKeys:
    """Test cases for _has_base_pattern_keys method."""

    def test_simple_interpolation(self):
        """Should find base pattern for simple interpolation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Mock file_manager with existing keys
            analyzer.file_manager.keys = {
                'activity.work': {'en': 'Work'},
                'activity.friends': {'en': 'Friends'},
            }

            assert analyzer._has_base_pattern_keys(r'activity.\(id)') is True

    def test_middle_interpolation(self):
        """Should find base pattern for middle interpolation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Mock file_manager with existing keys
            analyzer.file_manager.keys = {
                'style.friendly.description': {'en': 'Friendly style'},
                'style.formal.description': {'en': 'Formal style'},
            }

            assert analyzer._has_base_pattern_keys(r'style.\(rawValue).description') is True

    def test_no_matching_pattern(self):
        """Should return False when no matching keys exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Mock file_manager with unrelated keys
            analyzer.file_manager.keys = {
                'other.key': {'en': 'Other'},
            }

            assert analyzer._has_base_pattern_keys(r'activity.\(id)') is False

    def test_static_key_returns_false(self):
        """Should return False for static keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            assert analyzer._has_base_pattern_keys('static.key') is False


class TestFindDeadKeys:
    """Test cases for _find_dead_keys method."""

    def test_finds_unused_keys(self):
        """Should find keys in strings but not in code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Mock data
            analyzer.file_manager.keys = {
                'used.key': {'en': 'Used'},
                'dead.key': {'en': 'Dead'},
            }
            analyzer.used_keys = {'used.key'}

            analyzer._find_dead_keys(verbose=False)

            assert 'dead.key' in analyzer.dead_keys
            assert 'used.key' not in analyzer.dead_keys


class TestAnalyzeDuplicates:
    """Test cases for _analyze_duplicates method."""

    def test_finds_duplicates(self):
        """Should find strings that appear multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            adapter = SwiftAdapter()
            analyzer = LocalizationAnalyzer(project_dir, adapter)

            # Mock duplicates (same text in multiple locations)
            hardcoded1 = HardcodedString(
                file='file1.swift', line=10, text='Duplicate',
                component='Label', category='UI', priority=5,
                suggested_key='duplicate'
            )
            hardcoded2 = HardcodedString(
                file='file2.swift', line=20, text='Duplicate',
                component='Label', category='UI', priority=5,
                suggested_key='duplicate'
            )

            analyzer.duplicates = {
                'Duplicate': [hardcoded1, hardcoded2],
                'Single': [hardcoded1],  # Only one occurrence
            }

            analyzer._analyze_duplicates(verbose=False)

            # Should keep duplicates (2+ occurrences)
            assert 'Duplicate' in analyzer.duplicates
            # Should remove singles
            assert 'Single' not in analyzer.duplicates


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
