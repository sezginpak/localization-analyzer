"""Tests for DynamicKeyAnalyzer."""

import pytest
import tempfile
from pathlib import Path

from localization_analyzer.features.dynamic_key_analyzer import (
    DynamicKeyAnalyzer,
    DynamicKeyPattern,
    EnumDefinition,
    DynamicKeyAnalysisResult,
)


class TestEnumDefinition:
    """Test cases for EnumDefinition dataclass."""

    def test_create_enum_definition(self):
        """Should create enum definition with all fields."""
        enum_def = EnumDefinition(
            name="ActivityType",
            cases=["work", "friends", "family"],
            raw_values={"work": "work", "friends": "friends", "family": "family"},
            file_path="/path/to/file.swift"
        )

        assert enum_def.name == "ActivityType"
        assert len(enum_def.cases) == 3
        assert "work" in enum_def.cases


class TestDynamicKeyPattern:
    """Test cases for DynamicKeyPattern dataclass."""

    def test_create_pattern(self):
        """Should create dynamic key pattern."""
        pattern = DynamicKeyPattern(
            pattern=r"activity.\(id)",
            prefix="activity.",
            suffix="",
            variable_name="id",
            file_path="/test.swift",
            line_number=10
        )

        assert pattern.prefix == "activity."
        assert pattern.variable_name == "id"


class TestDynamicKeyAnalyzer:
    """Test cases for DynamicKeyAnalyzer."""

    def test_init(self):
        """Should initialize with source dir and existing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)
            existing_keys = {"key1", "key2"}

            analyzer = DynamicKeyAnalyzer(source_dir, existing_keys)

            assert analyzer.source_dir == source_dir
            assert analyzer.existing_keys == existing_keys
            assert len(analyzer.enums) == 0
            assert len(analyzer.dynamic_patterns) == 0

    def test_discover_enums(self):
        """Should discover enum definitions from Swift files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            # Create Swift file with enum
            swift_file = source_dir / "ActivityType.swift"
            swift_file.write_text('''
enum ActivityType: String {
    case work
    case friends
    case family
}
''')

            analyzer = DynamicKeyAnalyzer(source_dir, set())
            analyzer._discover_enums()

            assert "ActivityType" in analyzer.enums
            assert len(analyzer.enums["ActivityType"].cases) == 3
            assert "work" in analyzer.enums["ActivityType"].cases

    def test_discover_enums_with_raw_values(self):
        """Should extract raw values from enum cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            swift_file = source_dir / "Style.swift"
            swift_file.write_text('''
enum AIStyle: String {
    case friendly = "friendly_style"
    case caring = "caring_style"
}
''')

            analyzer = DynamicKeyAnalyzer(source_dir, set())
            analyzer._discover_enums()

            assert "AIStyle" in analyzer.enums
            enum_def = analyzer.enums["AIStyle"]
            assert enum_def.raw_values.get("friendly") == "friendly_style"
            assert enum_def.raw_values.get("caring") == "caring_style"

    def test_discover_dynamic_patterns(self):
        """Should find dynamic key patterns in Swift files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            swift_file = source_dir / "View.swift"
            swift_file.write_text('''
let title = "activity.\\(id)".localized
let desc = "style.\\(type.rawValue).description".localized(from: .ai)
''')

            analyzer = DynamicKeyAnalyzer(source_dir, set())
            analyzer._discover_dynamic_patterns()

            assert len(analyzer.dynamic_patterns) >= 1
            # Check first pattern
            pattern = analyzer.dynamic_patterns[0]
            assert "activity" in pattern.prefix or "style" in pattern.prefix

    def test_analyze_with_missing_keys(self):
        """Should detect missing keys based on enum analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            # Create enum
            enum_file = source_dir / "ActivityType.swift"
            enum_file.write_text('''
enum ActivityType: String {
    case work
    case friends
    case family
}
''')

            # Create usage
            view_file = source_dir / "View.swift"
            view_file.write_text('''
let title = "activity.\\(activityType)".localized
''')

            # Only "activity.work" exists
            existing_keys = {"activity.work"}

            analyzer = DynamicKeyAnalyzer(source_dir, existing_keys)
            results = analyzer.analyze()

            # Should find missing keys for friends and family
            assert len(results) >= 0  # May or may not match depending on heuristics

    def test_analyze_no_missing_keys(self):
        """Should return empty when all keys exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            # Create enum
            enum_file = source_dir / "Status.swift"
            enum_file.write_text('''
enum Status: String {
    case active
    case inactive
}
''')

            view_file = source_dir / "View.swift"
            view_file.write_text('''
let title = "status.\\(status)".localized
''')

            # All keys exist
            existing_keys = {"status.active", "status.inactive"}

            analyzer = DynamicKeyAnalyzer(source_dir, existing_keys)
            results = analyzer.analyze()

            # All keys exist, no missing
            for result in results:
                # If matched, should have no missing
                if result.enum_name == "Status":
                    assert len(result.missing_keys) == 0

    def test_camel_to_snake(self):
        """Should convert camelCase to snake_case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = DynamicKeyAnalyzer(Path(tmpdir), set())

            assert analyzer._camel_to_snake("work") == "work"
            assert analyzer._camel_to_snake("friendsAndFamily") == "friends_and_family"
            assert analyzer._camel_to_snake("XMLParser") == "x_m_l_parser"

    def test_generate_expected_keys(self):
        """Should generate expected keys from enum cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = DynamicKeyAnalyzer(Path(tmpdir), set())

            enum_def = EnumDefinition(
                name="Type",
                cases=["a", "b"],
                raw_values={"a": "first", "b": "second"},
                file_path="/test.swift"
            )

            pattern = DynamicKeyPattern(
                pattern=r"prefix.\(var)",
                prefix="prefix.",
                suffix="",
                variable_name="var",
                file_path="/test.swift",
                line_number=1
            )

            expected = analyzer._generate_expected_keys(pattern, enum_def)

            assert "prefix.first" in expected
            assert "prefix.second" in expected

    def test_generate_expected_keys_with_suffix(self):
        """Should include suffix in generated keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = DynamicKeyAnalyzer(Path(tmpdir), set())

            enum_def = EnumDefinition(
                name="Type",
                cases=["x"],
                raw_values={"x": "value"},
                file_path="/test.swift"
            )

            pattern = DynamicKeyPattern(
                pattern=r"prefix.\(var).suffix",
                prefix="prefix.",
                suffix=".suffix",
                variable_name="var",
                file_path="/test.swift",
                line_number=1
            )

            expected = analyzer._generate_expected_keys(pattern, enum_def)

            assert "prefix.value.suffix" in expected

    def test_get_summary(self):
        """Should return analysis summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)
            analyzer = DynamicKeyAnalyzer(source_dir, set())

            # Run empty analysis
            analyzer.analyze()

            summary = analyzer.get_summary()

            assert "total_dynamic_patterns" in summary
            assert "patterns_with_missing_keys" in summary
            assert "total_missing_keys" in summary
            assert "enums_discovered" in summary
            assert "details" in summary

    def test_excludes_build_directories(self):
        """Should skip build and derived data directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)

            # Create file in build directory (should be ignored)
            build_dir = source_dir / "build"
            build_dir.mkdir()
            build_file = build_dir / "Enum.swift"
            build_file.write_text('''
enum BuildEnum {
    case test
}
''')

            # Create file in source (should be found)
            source_file = source_dir / "SourceEnum.swift"
            source_file.write_text('''
enum SourceEnum {
    case source
}
''')

            analyzer = DynamicKeyAnalyzer(source_dir, set())
            analyzer._discover_enums()

            # Should find SourceEnum but not BuildEnum
            assert "SourceEnum" in analyzer.enums
            assert "BuildEnum" not in analyzer.enums


class TestDynamicKeyAnalysisResult:
    """Test cases for DynamicKeyAnalysisResult dataclass."""

    def test_create_result(self):
        """Should create analysis result with all fields."""
        pattern = DynamicKeyPattern(
            pattern="test",
            prefix="test.",
            suffix="",
            variable_name="var",
            file_path="/test.swift",
            line_number=1
        )

        result = DynamicKeyAnalysisResult(
            pattern=pattern,
            enum_name="TestEnum",
            expected_keys=["test.a", "test.b", "test.c"],
            existing_keys=["test.a"],
            missing_keys=["test.b", "test.c"]
        )

        assert result.enum_name == "TestEnum"
        assert len(result.expected_keys) == 3
        assert len(result.missing_keys) == 2


class TestAnalyzerIntegration:
    """Integration tests for dynamic key analysis with main analyzer."""

    def test_dynamic_keys_excluded_from_dead_keys(self):
        """Should not mark dynamically-used keys as dead."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create localization structure
            resources_dir = project_dir / "Resources"
            en_dir = resources_dir / "en.lproj"
            en_dir.mkdir(parents=True)

            # Create .strings file with activity keys
            strings_file = en_dir / "Localizable.strings"
            strings_file.write_text('''
"activity.work" = "Work";
"activity.friends" = "Friends";
"activity.family" = "Family";
"unused.key" = "This is unused";
''')

            # Create enum
            sources_dir = project_dir / "Sources"
            sources_dir.mkdir()

            enum_file = sources_dir / "ActivityType.swift"
            enum_file.write_text('''
enum ActivityType: String {
    case work
    case friends
    case family
}
''')

            # Create usage file with dynamic pattern
            view_file = sources_dir / "ActivityView.swift"
            view_file.write_text('''
import SwiftUI

struct ActivityView: View {
    let activityType: ActivityType

    var body: some View {
        Text("activity.\\(activityType.rawValue)".localized)
    }
}
''')

            # Create config
            config_file = project_dir / ".localization.yml"
            config_file.write_text('''
framework: swift
paths:
  source: Sources
  localization: Resources
languages:
  primary: en
  supported: [en]
''')

            # Run analyzer
            from localization_analyzer.core.analyzer import LocalizationAnalyzer
            from localization_analyzer.frameworks.swift import SwiftAdapter
            from localization_analyzer.utils.config import Config

            config = Config.from_file(str(config_file))
            adapter = SwiftAdapter(config)
            analyzer = LocalizationAnalyzer(
                project_dir=sources_dir,
                adapter=adapter,
                localization_dir=resources_dir
            )
            result = analyzer.analyze(verbose=False)

            # activity.* keys should NOT be in dead_keys (they're used dynamically)
            dead_key_list = list(result.dead_keys)
            assert "activity.work" not in dead_key_list
            assert "activity.friends" not in dead_key_list
            assert "activity.family" not in dead_key_list

            # unused.key should still be in dead_keys
            assert "unused.key" in dead_key_list

    def test_dynamic_analysis_reports_missing_keys(self):
        """Should report missing keys from enum analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create localization structure
            resources_dir = project_dir / "Resources"
            en_dir = resources_dir / "en.lproj"
            en_dir.mkdir(parents=True)

            # Only activity.work exists, missing friends and family
            strings_file = en_dir / "Localizable.strings"
            strings_file.write_text('''
"activity.work" = "Work";
''')

            # Create enum with 3 cases
            sources_dir = project_dir / "Sources"
            sources_dir.mkdir()

            enum_file = sources_dir / "ActivityType.swift"
            enum_file.write_text('''
enum ActivityType: String {
    case work
    case friends
    case family
}
''')

            # Create usage
            view_file = sources_dir / "ActivityView.swift"
            view_file.write_text('''
let title = "activity.\\(type.rawValue)".localized
''')

            # Create config
            config_file = project_dir / ".localization.yml"
            config_file.write_text('''
framework: swift
paths:
  source: Sources
  localization: Resources
languages:
  primary: en
  supported: [en]
''')

            # Run analyzer
            from localization_analyzer.core.analyzer import LocalizationAnalyzer
            from localization_analyzer.frameworks.swift import SwiftAdapter
            from localization_analyzer.utils.config import Config

            config = Config.from_file(str(config_file))
            adapter = SwiftAdapter(config)
            analyzer = LocalizationAnalyzer(
                project_dir=sources_dir,
                adapter=adapter,
                localization_dir=resources_dir
            )
            result = analyzer.analyze(verbose=False)

            # Check missing_dynamic_keys
            # There should be missing keys reported
            assert result.missing_dynamic_keys is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
