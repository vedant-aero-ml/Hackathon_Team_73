"""
Flow A: Vendor Change Risk Pipeline

Orchestrates agents 1–7 sequentially.
Each agent receives the previous agent's output dataclass.
"""
from __future__ import annotations

from agents.anomaly_detection_agent import AnomalyDetectionAgent
from agents.decision_agent import DecisionAgent
from agents.explanation_agent import ExplanationAgent
from agents.ingestion_agent import IngestionAgent
from agents.nlp_context_agent import NLPContextAgent
from agents.risk_aggregation_agent import RiskAggregationAgent
from agents.rule_based_risk_agent import RuleBasedRiskAgent
from models.schemas import FinalPipelineResult


def run_vendor_risk_pipeline(raw_input: dict) -> FinalPipelineResult:
    """
    Execute the full vendor change risk evaluation pipeline.

    Args:
        raw_input: Dict with keys vendor_id, change_type, old_value,
                   new_value, request_source_email, timestamp.

    Returns:
        FinalPipelineResult — flat, UI-ready result.

    Raises:
        ValidationError: if raw_input is missing/malformed.
        NLPAgentError:   if the Claude API call fails.
    """
    normalized = IngestionAgent().run(raw_input)
    rule_result = RuleBasedRiskAgent().run(normalized)
    anomaly_result = AnomalyDetectionAgent().run(rule_result)
    nlp_result = NLPContextAgent().run(anomaly_result)
    aggregated = RiskAggregationAgent().run(nlp_result)
    decision = DecisionAgent().run(aggregated)
    final = ExplanationAgent().run(decision)
    return final
