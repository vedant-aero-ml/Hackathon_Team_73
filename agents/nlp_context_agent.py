"""
Agent 4: NLP / Context Agent

Uses SAP AI SDK (gen_ai_hub) with an OpenAI-compatible chat endpoint to
analyze contextual signals in the vendor change request.
"""
from __future__ import annotations

import json
from typing import Any

from config.settings import MAX_TOKENS, MODEL_NAME
from models.schemas import AnomalyResult, NLPContextResult


class NLPAgentError(RuntimeError):
    """Raised when the LLM call fails and no fallback is possible."""


class NLPContextAgent:
    """
    Calls an OpenAI-compatible model via the SAP AI SDK (gen_ai_hub) to assess
    contextual fraud / impersonation signals in a vendor change request.
    Falls back to a neutral score on JSON parse failure.
    """

    SYSTEM_PROMPT: str = (
        "You are a vendor fraud and impersonation risk analyst for a large enterprise.\n"
        "You will receive structured data about a vendor master data change request.\n"
        "Analyze the request for signs of: social engineering, account takeover, "
        "payment diversion, impersonation, and unusual behavioral patterns.\n\n"
        "Respond ONLY with a valid JSON object — no markdown, no commentary — "
        "containing exactly these fields:\n"
        '  "context_score": a float between 0.0 (no risk) and 1.0 (highest risk),\n'
        '  "risk_signals":  a list of strings identifying specific risk patterns you found,\n'
        '  "explanation":   a 2–4 sentence narrative suitable for a compliance officer.\n\n'
        "Example:\n"
        '{"context_score": 0.85, "risk_signals": ["urgent payment request", '
        '"domain mismatch"], "explanation": "..."}'
    )

    def run(self, anomaly_result: AnomalyResult) -> NLPContextResult:
        user_message = self._build_user_message(anomaly_result)
        parsed = self._call_llm(user_message)

        return NLPContextResult(
            anomaly_result=anomaly_result,
            context_score=float(parsed.get("context_score", 0.5)),
            explanation=parsed.get("explanation", "No explanation available."),
            risk_signals=parsed.get("risk_signals", []),
        )

    # ── Private methods ──────────────────────────────────────────────────────

    def _build_user_message(self, anomaly_result: AnomalyResult) -> str:
        norm = anomaly_result.rule_result.normalized
        rule = anomaly_result.rule_result

        history = sorted(
            norm.vendor_history,
            key=lambda e: e.get("timestamp", ""),
            reverse=True,
        )[:5]
        history_lines = "\n".join(
            f"  {e.get('timestamp','?')} | {e.get('change_type','?'):15s} | "
            f"{'APPROVED' if e.get('approved') else 'REJECTED':8s} | "
            f"risk={e.get('risk_level','UNKNOWN')}"
            for e in history
        ) or "  (no prior history)"

        lines = [
            "=== VENDOR CHANGE REQUEST ===",
            f"Vendor ID:        {norm.vendor_id}",
            f"Change Type:      {norm.change_type.value}",
            f"Old Value:        {norm.old_value}",
            f"New Value:        {norm.new_value}",
            f"Source Email:     {norm.request_source_email}",
            f"Email Domain:     {norm.email_domain}",
            f"Timestamp:        {norm.timestamp}",
            "",
            "=== RULE FLAGS ===",
            f"Triggered Rules:  {', '.join(rule.flags) if rule.flags else 'none'}",
            f"Rule Score:       {rule.rule_score:.2f} / 1.0",
            "",
            "=== ANOMALY ANALYSIS ===",
            f"Anomaly Score:    {anomaly_result.anomaly_score:.2f} / 1.0",
            f"Anomaly Reason:   {anomaly_result.anomaly_reason}",
            "",
            "=== VENDOR CHANGE HISTORY (last 5 events) ===",
            history_lines,
        ]
        return "\n".join(lines)

    def _call_llm(self, user_message: str) -> dict[str, Any]:
        """
        Call the model via SAP AI SDK gen_ai_hub chat completions.
        The import is deferred to avoid triggering credential validation at module load.
        Falls back to a safe neutral dict on any error.
        """
        # Lazy import — only executed when the agent actually runs
        from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        try:
            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0,
            )
            text = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            return json.loads(text)

        except Exception as exc:
            # Any API or network error — return neutral fallback
            return {
                "context_score": 0.5,
                "risk_signals": [f"[LLM error: {exc}]"],
                "explanation": (
                    "The AI context analysis could not produce a structured result. "
                    "Manual review is recommended."
                ),
            }
