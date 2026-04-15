"""
Agent 2: Rule-Based Risk Agent

Static, deterministic rule engine — no ML, no API calls.
Checks email domain type, change field sensitivity, and prior risk history.
"""
from __future__ import annotations

from config.settings import FREE_EMAIL_DOMAINS
from models.schemas import ChangeType, NormalizedVendorChange, RuleBasedResult

# Contribution of each rule to the cumulative rule_score
_RULE_CONTRIBUTIONS: dict[str, float] = {
    "FREE_EMAIL_DOMAIN": 0.30,
    "SENSITIVE_FIELD_HIGH": 0.70,   # bank_account
    "SENSITIVE_FIELD_MED": 0.40,    # email
    "SENSITIVE_FIELD_LOW": 0.10,    # address / name
    "PRIOR_HIGH_RISK": 0.20,
    "PRIOR_REJECTED": 0.15,
    "DOMAIN_MISMATCH": 0.25,
}


class RuleBasedRiskAgent:
    """
    Applies a fixed set of compliance rules to a normalized change request.
    Produces a list of triggered flag names and a composite rule_score in [0, 1].
    """

    def __init__(self, free_email_domains: set[str] | None = None) -> None:
        self._free_domains = free_email_domains if free_email_domains is not None else FREE_EMAIL_DOMAINS

    def run(self, normalized: NormalizedVendorChange) -> RuleBasedResult:
        flags: list[str] = []
        score: float = 0.0

        # R1 — Free/personal email domain
        if normalized.email_domain in self._free_domains:
            flags.append("FREE_EMAIL_DOMAIN")
            score += _RULE_CONTRIBUTIONS["FREE_EMAIL_DOMAIN"]

        # R2/R3/R4 — Sensitive field classification
        ct = normalized.change_type
        if ct == ChangeType.BANK_ACCOUNT:
            flags.append("SENSITIVE_FIELD_HIGH")
            score += _RULE_CONTRIBUTIONS["SENSITIVE_FIELD_HIGH"]
        elif ct == ChangeType.EMAIL:
            flags.append("SENSITIVE_FIELD_MED")
            score += _RULE_CONTRIBUTIONS["SENSITIVE_FIELD_MED"]
        else:
            flags.append("SENSITIVE_FIELD_LOW")
            score += _RULE_CONTRIBUTIONS["SENSITIVE_FIELD_LOW"]

        history = normalized.vendor_history

        # R5 — Prior HIGH risk verdict in history
        if self._has_prior_high_risk(history):
            flags.append("PRIOR_HIGH_RISK")
            score += _RULE_CONTRIBUTIONS["PRIOR_HIGH_RISK"]

        # R6 — Prior rejected change in history
        if self._has_prior_rejection(history):
            flags.append("PRIOR_REJECTED")
            score += _RULE_CONTRIBUTIONS["PRIOR_REJECTED"]

        # R7 — Domain mismatch: vendor previously used corporate domain,
        #       current request comes from a free domain
        if self._has_domain_mismatch(normalized):
            flags.append("DOMAIN_MISMATCH")
            score += _RULE_CONTRIBUTIONS["DOMAIN_MISMATCH"]

        return RuleBasedResult(
            normalized=normalized,
            flags=flags,
            rule_score=min(1.0, score),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _has_prior_high_risk(self, history: list[dict]) -> bool:
        return any(evt.get("risk_level") == "HIGH" for evt in history)

    def _has_prior_rejection(self, history: list[dict]) -> bool:
        return any(evt.get("approved") is False for evt in history)

    def _has_domain_mismatch(self, normalized: NormalizedVendorChange) -> bool:
        """
        Return True if the request email is from a free domain but the vendor's
        most recent email change in history used a non-free domain.
        """
        if normalized.email_domain not in self._free_domains:
            return False  # current domain is corporate — no mismatch

        # Look for any prior email value that was corporate
        for evt in normalized.vendor_history:
            for field in ("old_value", "new_value"):
                val = evt.get(field, "")
                if "@" in val:
                    domain = val.split("@")[-1].lower()
                    if domain and domain not in self._free_domains:
                        return True
        return False
