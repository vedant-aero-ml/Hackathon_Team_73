"""
Agent 3: Anomaly Detection Agent

Uses statistical frequency analysis (z-score or absolute threshold) to detect
vendors with abnormally high change activity relative to the population.
"""
from __future__ import annotations

import math

from config.settings import (
    ANOMALY_ABSOLUTE_THRESHOLD,
    ANOMALY_HISTORY_WINDOW_DAYS,
    ANOMALY_ZSCORE_THRESHOLD,
)
from data.mock_vendor_history import get_all_vendor_ids, get_recent_change_count
from models.schemas import AnomalyResult, RuleBasedResult


class AnomalyDetectionAgent:
    """
    Computes an anomaly_score in [0, 1] based on how unusual the vendor's
    recent change frequency is compared to the known vendor population.
    """

    def __init__(
        self,
        window_days: int = ANOMALY_HISTORY_WINDOW_DAYS,
        zscore_threshold: float = ANOMALY_ZSCORE_THRESHOLD,
        absolute_threshold: int = ANOMALY_ABSOLUTE_THRESHOLD,
    ) -> None:
        self._window_days = window_days
        self._zscore_threshold = zscore_threshold
        self._absolute_threshold = absolute_threshold

    def run(self, rule_result: RuleBasedResult) -> AnomalyResult:
        vendor_id = rule_result.normalized.vendor_id
        target_count = get_recent_change_count(vendor_id, self._window_days)
        population_counts = self._build_population_counts()

        if len(population_counts) >= 3:
            score, reason = self._zscore_detection(
                vendor_id, target_count, population_counts
            )
        else:
            score, reason = self._absolute_detection(vendor_id, target_count)

        return AnomalyResult(
            rule_result=rule_result,
            anomaly_score=score,
            anomaly_reason=reason,
        )

    # ── Detection methods ────────────────────────────────────────────────────

    def _zscore_detection(
        self,
        vendor_id: str,
        target_count: int,
        population_counts: list[int],
    ) -> tuple[float, str]:
        mean = sum(population_counts) / len(population_counts)
        variance = sum((x - mean) ** 2 for x in population_counts) / len(population_counts)
        std = math.sqrt(variance)

        if std == 0:
            # All vendors changed the same number of times — fall back to absolute
            return self._absolute_detection(vendor_id, target_count)

        z = (target_count - mean) / std
        if z <= 0:
            score = 0.0
            reason = (
                f"{vendor_id} had {target_count} change(s) in last "
                f"{self._window_days} days (z-score={z:.2f}, below population mean)"
            )
        else:
            score = min(1.0, z / self._zscore_threshold)
            reason = (
                f"{vendor_id} had {target_count} change(s) in last "
                f"{self._window_days} days "
                f"(z-score={z:.2f}, threshold={self._zscore_threshold})"
            )
        return score, reason

    def _absolute_detection(
        self, vendor_id: str, target_count: int
    ) -> tuple[float, str]:
        score = min(1.0, target_count / max(self._absolute_threshold, 1))
        reason = (
            f"{vendor_id} had {target_count} change(s) in last "
            f"{self._window_days} days "
            f"(threshold={self._absolute_threshold})"
        )
        return score, reason

    # ── Population helper ────────────────────────────────────────────────────

    def _build_population_counts(self) -> list[int]:
        """Collect recent change counts for all known vendors."""
        return [
            get_recent_change_count(vid, self._window_days)
            for vid in get_all_vendor_ids()
        ]
