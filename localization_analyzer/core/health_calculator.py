"""Localization health score calculator."""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class HealthScore:
    """Localization health score and metrics."""
    score: float  # 0-100
    grade: str  # A+, A, B, C, D, F
    localized_count: int
    hardcoded_count: int
    total_strings: int
    localization_rate: float  # percentage
    missing_keys_count: int
    dead_keys_count: int
    duplicate_count: int


class HealthCalculator:
    """Calculate localization health score and grade."""

    # Grade thresholds
    GRADE_THRESHOLDS = {
        'A+': 95,
        'A': 90,
        'B': 80,
        'C': 70,
        'D': 60,
        'F': 0,
    }

    # Penalty weights
    MISSING_KEY_PENALTY = 0.5  # per missing key
    DEAD_KEY_PENALTY = 0.1  # per dead key
    DUPLICATE_PENALTY = 0.2  # per duplicate

    MAX_PENALTY_MISSING = 10  # max percentage points
    MAX_PENALTY_DEAD = 5
    MAX_PENALTY_DUPLICATE = 5

    @classmethod
    def calculate(
        cls,
        localized_count: int,
        hardcoded_count: int,
        missing_keys: List[str],
        dead_keys: List[str],
        duplicates: Dict[str, List]
    ) -> HealthScore:
        """
        Calculate health score.

        Args:
            localized_count: Number of localized strings
            hardcoded_count: Number of hardcoded strings
            missing_keys: List of missing keys
            dead_keys: List of dead keys
            duplicates: Dictionary of duplicate strings

        Returns:
            HealthScore object
        """
        total_strings = localized_count + hardcoded_count

        if total_strings == 0:
            return HealthScore(
                score=100.0,
                grade='A+',
                localized_count=0,
                hardcoded_count=0,
                total_strings=0,
                localization_rate=100.0,
                missing_keys_count=0,
                dead_keys_count=0,
                duplicate_count=0,
            )

        # Base score: localization rate
        localization_rate = (localized_count / total_strings) * 100
        score = localization_rate

        # Apply penalties
        missing_penalty = min(
            len(missing_keys) * cls.MISSING_KEY_PENALTY,
            cls.MAX_PENALTY_MISSING
        )
        dead_penalty = min(
            len(dead_keys) * cls.DEAD_KEY_PENALTY,
            cls.MAX_PENALTY_DEAD
        )
        duplicate_penalty = min(
            len(duplicates) * cls.DUPLICATE_PENALTY,
            cls.MAX_PENALTY_DUPLICATE
        )

        score -= missing_penalty
        score -= dead_penalty
        score -= duplicate_penalty

        # Clamp score
        score = max(0, min(100, score))

        # Calculate grade
        grade = cls._calculate_grade(score)

        return HealthScore(
            score=round(score, 1),
            grade=grade,
            localized_count=localized_count,
            hardcoded_count=hardcoded_count,
            total_strings=total_strings,
            localization_rate=round(localization_rate, 1),
            missing_keys_count=len(missing_keys),
            dead_keys_count=len(dead_keys),
            duplicate_count=len(duplicates),
        )

    @classmethod
    def _calculate_grade(cls, score: float) -> str:
        """Convert score to letter grade."""
        for grade, threshold in cls.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'F'

    @classmethod
    def get_grade_color(cls, grade: str) -> str:
        """Get color code for grade."""
        from ..utils.colors import Colors

        grade_colors = {
            'A+': Colors.OKGREEN,
            'A': Colors.OKGREEN,
            'B': Colors.OKCYAN,
            'C': Colors.WARNING,
            'D': Colors.WARNING,
            'F': Colors.FAIL,
        }
        return grade_colors.get(grade, Colors.ENDC)

    @classmethod
    def get_recommendations(cls, health: HealthScore) -> List[str]:
        """
        Get improvement recommendations based on health score.

        Args:
            health: HealthScore object

        Returns:
            List of recommendations
        """
        recommendations = []

        # Hardcoded strings
        if health.hardcoded_count > 0:
            recommendations.append(
                f"🔧 Fix {health.hardcoded_count} hardcoded string(s) to improve localization rate"
            )

        # Missing keys
        if health.missing_keys_count > 0:
            recommendations.append(
                f"🔍 Add {health.missing_keys_count} missing key(s) to localization files"
            )

        # Dead keys
        if health.dead_keys_count > 0:
            recommendations.append(
                f"🧹 Remove {health.dead_keys_count} unused key(s) to reduce clutter"
            )

        # Duplicates
        if health.duplicate_count > 0:
            recommendations.append(
                f"♻️  Consolidate {health.duplicate_count} duplicate string(s) into shared keys"
            )

        # Localization rate specific advice
        if health.localization_rate < 80:
            recommendations.append(
                "⚠️  Localization rate is below 80% - prioritize fixing high-priority strings"
            )
        elif health.localization_rate < 95:
            recommendations.append(
                "💡 Good progress! Focus on remaining hardcoded strings for A+ rating"
            )
        else:
            recommendations.append(
                "✨ Excellent localization! Maintain this standard for new code"
            )

        return recommendations

    @classmethod
    def compare_scores(cls, before: HealthScore, after: HealthScore) -> Dict[str, float]:
        """
        Compare two health scores.

        Args:
            before: Previous health score
            after: Current health score

        Returns:
            Dictionary of changes
        """
        return {
            'score_change': after.score - before.score,
            'localization_rate_change': after.localization_rate - before.localization_rate,
            'hardcoded_change': after.hardcoded_count - before.hardcoded_count,
            'missing_keys_change': after.missing_keys_count - before.missing_keys_count,
            'dead_keys_change': after.dead_keys_count - before.dead_keys_count,
        }
