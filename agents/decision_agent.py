"""
Agent 6: Decision Agent

Maps risk_level → a clear governance decision.
Kept as a class to allow future business-rule overrides.
"""
from __future__ import annotations

from models.schemas import AggregatedRisk, Decision, DecisionResult, RiskLevel


class DecisionAgent:
    """Pure mapping from RiskLevel to Decision."""

    _DECISION_MAP: dict[RiskLevel, Decision] = {
        RiskLevel.LOW: Decision.APPROVE,
        RiskLevel.MEDIUM: Decision.REVIEW,
        RiskLevel.HIGH: Decision.ESCALATE,
    }

    def run(self, aggregated: AggregatedRisk) -> DecisionResult:
        decision = self._DECISION_MAP[aggregated.risk_level]
        return DecisionResult(aggregated=aggregated, decision=decision)
