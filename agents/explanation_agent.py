"""
Agent 7: Explanation Agent

Generates a human-readable compliance narrative and flattens the entire
agent chain into a single FinalPipelineResult dataclass.
No API calls — pure deterministic string assembly.
"""
from __future__ import annotations

from models.schemas import DecisionResult, FinalPipelineResult, RiskLevel


class ExplanationAgent:
    """
    Produces a multi-paragraph audit explanation and returns the flat
    FinalPipelineResult used by the Streamlit dashboard.
    """

    def run(self, decision_result: DecisionResult) -> FinalPipelineResult:
        agg = decision_result.aggregated
        nlp = agg.nlp_result
        anomaly = nlp.anomaly_result
        rule = anomaly.rule_result
        norm = rule.normalized

        human_explanation = self._build_explanation(decision_result)

        return FinalPipelineResult(
            vendor_id=norm.vendor_id,
            change_type=norm.change_type,
            old_value=norm.old_value,
            new_value=norm.new_value,
            request_source_email=norm.request_source_email,
            final_score=agg.final_score,
            risk_level=agg.risk_level,
            decision=decision_result.decision,
            flags=rule.flags,
            anomaly_reason=anomaly.anomaly_reason,
            nlp_explanation=nlp.explanation,
            nlp_risk_signals=nlp.risk_signals,
            human_explanation=human_explanation,
            rule_score=agg.rule_score,
            anomaly_score=agg.anomaly_score,
            context_score=agg.context_score,
        )

    # ── Private methods ──────────────────────────────────────────────────────

    def _build_explanation(self, dr: DecisionResult) -> str:
        agg = dr.aggregated
        nlp = agg.nlp_result
        anomaly = nlp.anomaly_result
        rule = anomaly.rule_result
        norm = rule.normalized

        ct = norm.change_type.value.replace("_", " ").title()
        flags_str = ", ".join(rule.flags) if rule.flags else "none"
        signals_str = (
            "; ".join(nlp.risk_signals)
            if nlp.risk_signals
            else "no specific signals identified"
        )

        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(
            agg.risk_level.value, ""
        )
        decision_verb = {
            "APPROVE": "has been APPROVED for processing",
            "REVIEW": "requires MANUAL REVIEW before processing",
            "ESCALATE": "has been ESCALATED to the fraud/compliance team",
        }.get(dr.decision.value, "requires action")

        paragraphs = [
            (
                f"COMPLIANCE AUDIT REPORT\n"
                f"{'=' * 50}\n"
                f"Vendor: {norm.vendor_id}  |  Change: {ct}  |  "
                f"Timestamp: {norm.timestamp}"
            ),
            (
                f"REQUEST DETAILS\n"
                f"The vendor requested a {ct} change from '{norm.old_value}' "
                f"to '{norm.new_value}'. The request originated from the email "
                f"address '{norm.request_source_email}' (domain: {norm.email_domain})."
            ),
            (
                f"RULE-BASED ANALYSIS  [Score: {rule.rule_score:.2f}/1.0]\n"
                f"Triggered rules: {flags_str}.\n"
                + self._prior_history_summary(norm.vendor_history)
            ),
            (
                f"ANOMALY DETECTION  [Score: {agg.anomaly_score:.2f}/1.0]\n"
                f"{anomaly.anomaly_reason}"
            ),
            (
                f"AI CONTEXTUAL ANALYSIS  [Score: {agg.context_score:.2f}/1.0]\n"
                f"Key signals: {signals_str}.\n"
                f"{nlp.explanation}"
            ),
            (
                f"FINAL ASSESSMENT\n"
                f"Composite Risk Score: {agg.final_score:.1f} / 100  "
                f"{risk_emoji} {agg.risk_level.value}\n"
                f"Decision: This change request {decision_verb}."
            ),
        ]
        return "\n\n".join(paragraphs)

    def _prior_history_summary(self, history: list[dict]) -> str:
        if not history:
            return "No prior change history on record for this vendor."
        total = len(history)
        rejected = sum(1 for e in history if e.get("approved") is False)
        high_risk = sum(1 for e in history if e.get("risk_level") == "HIGH")
        return (
            f"Vendor has {total} prior change event(s) on record: "
            f"{rejected} rejection(s), {high_risk} flagged as HIGH risk."
        )
