"""
Agent 5: Risk Aggregation Agent

Combines rule_score, anomaly_score, and context_score into a single
final_score (0–100) and determines the risk_level bucket.
"""
from __future__ import annotations

from config.settings import (
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    WEIGHT_ANOMALY,
    WEIGHT_NLP,
    WEIGHT_RULE,
)
from models.schemas import AggregatedRisk, NLPContextResult, RiskLevel


class RiskAggregationAgent:
    """
    Weighted linear combination of three sub-scores → final_score 0–100.
    """

    def __init__(
        self,
        weight_rule: float = WEIGHT_RULE,
        weight_anomaly: float = WEIGHT_ANOMALY,
        weight_nlp: float = WEIGHT_NLP,
    ) -> None:
        self._w_rule = weight_rule
        self._w_anomaly = weight_anomaly
        self._w_nlp = weight_nlp

    def run(self, nlp_result: NLPContextResult) -> AggregatedRisk:
        rule_score = nlp_result.anomaly_result.rule_result.rule_score
        anomaly_score = nlp_result.anomaly_result.anomaly_score
        context_score = nlp_result.context_score

        raw = (
            rule_score * self._w_rule
            + anomaly_score * self._w_anomaly
            + context_score * self._w_nlp
        )
        final_score = round(min(100.0, max(0.0, raw * 100)), 2)

        if final_score >= THRESHOLD_HIGH:
            risk_level = RiskLevel.HIGH
        elif final_score >= THRESHOLD_MEDIUM:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return AggregatedRisk(
            nlp_result=nlp_result,
            rule_score=rule_score,
            anomaly_score=anomaly_score,
            context_score=context_score,
            final_score=final_score,
            risk_level=risk_level,
        )
