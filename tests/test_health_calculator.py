"""Tests for HealthCalculator and HealthScore."""

import pytest
from localization_analyzer.core.health_calculator import HealthCalculator, HealthScore
from localization_analyzer.utils.colors import Colors


class TestHealthScore:
    """Test cases for HealthScore dataclass."""

    def test_create_health_score(self):
        """Should create HealthScore with all fields."""
        score = HealthScore(
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

        assert score.score == 85.0
        assert score.grade == 'B'
        assert score.localized_count == 100
        assert score.hardcoded_count == 15
        assert score.total_strings == 115
        assert score.localization_rate == 87.0
        assert score.missing_keys_count == 5
        assert score.dead_keys_count == 3
        assert score.duplicate_count == 2


class TestHealthCalculatorCalculate:
    """Test cases for HealthCalculator.calculate method."""

    def test_perfect_score(self):
        """100% localized with no issues should score 100."""
        result = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        assert result.score == 100.0
        assert result.grade == 'A+'
        assert result.localization_rate == 100.0

    def test_no_strings(self):
        """Empty project should return perfect score."""
        result = HealthCalculator.calculate(
            localized_count=0,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        assert result.score == 100.0
        assert result.grade == 'A+'
        assert result.total_strings == 0

    def test_all_hardcoded(self):
        """All hardcoded should score 0."""
        result = HealthCalculator.calculate(
            localized_count=0,
            hardcoded_count=100,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        assert result.score == 0.0
        assert result.grade == 'F'
        assert result.localization_rate == 0.0

    def test_mixed_strings(self):
        """Mixed localized/hardcoded should calculate rate correctly."""
        result = HealthCalculator.calculate(
            localized_count=80,
            hardcoded_count=20,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        assert result.localization_rate == 80.0
        assert result.total_strings == 100

    def test_missing_keys_penalty(self):
        """Missing keys should reduce score."""
        result_without = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        result_with = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=['key1', 'key2', 'key3'],
            dead_keys=[],
            duplicates={}
        )

        assert result_with.score < result_without.score
        assert result_with.missing_keys_count == 3

    def test_dead_keys_penalty(self):
        """Dead keys should reduce score."""
        result_without = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        result_with = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=['dead1', 'dead2'],
            duplicates={}
        )

        assert result_with.score < result_without.score
        assert result_with.dead_keys_count == 2

    def test_duplicates_penalty(self):
        """Duplicates should reduce score."""
        result_without = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={}
        )

        result_with = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[],
            dead_keys=[],
            duplicates={'dup1': ['loc1', 'loc2'], 'dup2': ['loc3', 'loc4']}
        )

        assert result_with.score < result_without.score
        assert result_with.duplicate_count == 2

    def test_max_penalty_cap(self):
        """Penalties should be capped at maximum."""
        # Many missing keys should not reduce score below reasonable level
        result = HealthCalculator.calculate(
            localized_count=100,
            hardcoded_count=0,
            missing_keys=[f'key{i}' for i in range(100)],  # 100 missing keys
            dead_keys=[],
            duplicates={}
        )

        # Score should not go below base - max penalties
        assert result.score >= 100 - HealthCalculator.MAX_PENALTY_MISSING

    def test_score_clamped_to_zero(self):
        """Score should never go below 0."""
        result = HealthCalculator.calculate(
            localized_count=0,
            hardcoded_count=100,
            missing_keys=[f'key{i}' for i in range(50)],
            dead_keys=[f'dead{i}' for i in range(100)],
            duplicates={f'dup{i}': [] for i in range(50)}
        )

        assert result.score >= 0

    def test_score_rounded(self):
        """Score should be rounded to 1 decimal place."""
        result = HealthCalculator.calculate(
            localized_count=87,
            hardcoded_count=13,
            missing_keys=['key1'],
            dead_keys=[],
            duplicates={}
        )

        # Score should have at most 1 decimal place
        assert result.score == round(result.score, 1)


class TestCalculateGrade:
    """Test cases for grade calculation."""

    def test_grade_a_plus(self):
        """Score >= 95 should be A+."""
        assert HealthCalculator._calculate_grade(95) == 'A+'
        assert HealthCalculator._calculate_grade(100) == 'A+'

    def test_grade_a(self):
        """Score >= 90 should be A."""
        assert HealthCalculator._calculate_grade(90) == 'A'
        assert HealthCalculator._calculate_grade(94.9) == 'A'

    def test_grade_b(self):
        """Score >= 80 should be B."""
        assert HealthCalculator._calculate_grade(80) == 'B'
        assert HealthCalculator._calculate_grade(89.9) == 'B'

    def test_grade_c(self):
        """Score >= 70 should be C."""
        assert HealthCalculator._calculate_grade(70) == 'C'
        assert HealthCalculator._calculate_grade(79.9) == 'C'

    def test_grade_d(self):
        """Score >= 60 should be D."""
        assert HealthCalculator._calculate_grade(60) == 'D'
        assert HealthCalculator._calculate_grade(69.9) == 'D'

    def test_grade_f(self):
        """Score < 60 should be F."""
        assert HealthCalculator._calculate_grade(59.9) == 'F'
        assert HealthCalculator._calculate_grade(0) == 'F'


class TestGetGradeColor:
    """Test cases for grade color mapping."""

    def test_a_grades_green(self):
        """A+ and A should be green."""
        assert HealthCalculator.get_grade_color('A+') == Colors.OKGREEN
        assert HealthCalculator.get_grade_color('A') == Colors.OKGREEN

    def test_b_grade_cyan(self):
        """B should be cyan."""
        assert HealthCalculator.get_grade_color('B') == Colors.OKCYAN

    def test_c_d_grades_warning(self):
        """C and D should be warning color."""
        assert HealthCalculator.get_grade_color('C') == Colors.WARNING
        assert HealthCalculator.get_grade_color('D') == Colors.WARNING

    def test_f_grade_fail(self):
        """F should be fail color."""
        assert HealthCalculator.get_grade_color('F') == Colors.FAIL

    def test_unknown_grade_default(self):
        """Unknown grade should return default."""
        result = HealthCalculator.get_grade_color('X')
        assert result == Colors.ENDC


class TestGetRecommendations:
    """Test cases for recommendations generation."""

    def test_no_issues(self):
        """Perfect project should have only positive message."""
        health = HealthScore(
            score=100, grade='A+', localized_count=100, hardcoded_count=0,
            total_strings=100, localization_rate=100.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert len(recs) == 1
        assert 'Excellent' in recs[0]

    def test_hardcoded_recommendation(self):
        """Should recommend fixing hardcoded strings."""
        health = HealthScore(
            score=80, grade='B', localized_count=80, hardcoded_count=20,
            total_strings=100, localization_rate=80.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('hardcoded' in r.lower() for r in recs)
        assert any('20' in r for r in recs)

    def test_missing_keys_recommendation(self):
        """Should recommend adding missing keys."""
        health = HealthScore(
            score=95, grade='A', localized_count=100, hardcoded_count=0,
            total_strings=100, localization_rate=100.0, missing_keys_count=5,
            dead_keys_count=0, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('missing' in r.lower() for r in recs)

    def test_dead_keys_recommendation(self):
        """Should recommend removing dead keys."""
        health = HealthScore(
            score=95, grade='A', localized_count=100, hardcoded_count=0,
            total_strings=100, localization_rate=100.0, missing_keys_count=0,
            dead_keys_count=10, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('unused' in r.lower() or 'dead' in r.lower() for r in recs)

    def test_duplicates_recommendation(self):
        """Should recommend consolidating duplicates."""
        health = HealthScore(
            score=95, grade='A', localized_count=100, hardcoded_count=0,
            total_strings=100, localization_rate=100.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=5
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('duplicate' in r.lower() for r in recs)

    def test_low_rate_warning(self):
        """Should warn about low localization rate."""
        health = HealthScore(
            score=50, grade='F', localized_count=50, hardcoded_count=50,
            total_strings=100, localization_rate=50.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('below 80%' in r for r in recs)

    def test_good_progress_message(self):
        """Should encourage when rate is between 80-95%."""
        health = HealthScore(
            score=90, grade='A', localized_count=90, hardcoded_count=10,
            total_strings=100, localization_rate=90.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )

        recs = HealthCalculator.get_recommendations(health)

        assert any('good progress' in r.lower() or 'A+' in r for r in recs)


class TestCompareScores:
    """Test cases for score comparison."""

    def test_improvement(self):
        """Should calculate positive changes for improvement."""
        before = HealthScore(
            score=70, grade='C', localized_count=70, hardcoded_count=30,
            total_strings=100, localization_rate=70.0, missing_keys_count=10,
            dead_keys_count=5, duplicate_count=3
        )
        after = HealthScore(
            score=90, grade='A', localized_count=90, hardcoded_count=10,
            total_strings=100, localization_rate=90.0, missing_keys_count=2,
            dead_keys_count=3, duplicate_count=1
        )

        changes = HealthCalculator.compare_scores(before, after)

        assert changes['score_change'] == 20
        assert changes['localization_rate_change'] == 20
        assert changes['hardcoded_change'] == -20  # Reduced
        assert changes['missing_keys_change'] == -8  # Reduced
        assert changes['dead_keys_change'] == -2  # Reduced

    def test_regression(self):
        """Should calculate negative changes for regression."""
        before = HealthScore(
            score=90, grade='A', localized_count=90, hardcoded_count=10,
            total_strings=100, localization_rate=90.0, missing_keys_count=0,
            dead_keys_count=0, duplicate_count=0
        )
        after = HealthScore(
            score=70, grade='C', localized_count=70, hardcoded_count=30,
            total_strings=100, localization_rate=70.0, missing_keys_count=5,
            dead_keys_count=10, duplicate_count=5
        )

        changes = HealthCalculator.compare_scores(before, after)

        assert changes['score_change'] == -20
        assert changes['hardcoded_change'] == 20  # Increased
        assert changes['missing_keys_change'] == 5  # Increased

    def test_no_change(self):
        """Should calculate zero changes when scores are same."""
        score = HealthScore(
            score=85, grade='B', localized_count=85, hardcoded_count=15,
            total_strings=100, localization_rate=85.0, missing_keys_count=2,
            dead_keys_count=3, duplicate_count=1
        )

        changes = HealthCalculator.compare_scores(score, score)

        assert changes['score_change'] == 0
        assert changes['localization_rate_change'] == 0
        assert changes['hardcoded_change'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
