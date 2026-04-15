"""
All data structures (dataclasses + enums) for inter-agent payloads.
Imported by every layer; no circular dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class ChangeType(str, Enum):
    BANK_ACCOUNT = "bank_account"
    EMAIL = "email"
    ADDRESS = "address"
    NAME = "name"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"


class VendorStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


# ── Flow A: Raw Input (TypedDict-compatible plain dict) ───────────────────────
# Fields: vendor_id, change_type, old_value, new_value,
#         request_source_email, timestamp (ISO-8601 string)


# ── Flow A: Agent 1 Output ────────────────────────────────────────────────────

@dataclass
class NormalizedVendorChange:
    vendor_id: str
    change_type: ChangeType
    old_value: str
    new_value: str
    request_source_email: str
    email_domain: str               # extracted from request_source_email
    timestamp: str
    vendor_history: list[dict]      # from mock store; may be empty


# ── Flow A: Agent 2 Output ────────────────────────────────────────────────────

@dataclass
class RuleBasedResult:
    normalized: NormalizedVendorChange
    flags: list[str]                # e.g. ["FREE_EMAIL_DOMAIN", "SENSITIVE_FIELD_HIGH"]
    rule_score: float               # 0.0 – 1.0


# ── Flow A: Agent 3 Output ────────────────────────────────────────────────────

@dataclass
class AnomalyResult:
    rule_result: RuleBasedResult
    anomaly_score: float            # 0.0 – 1.0
    anomaly_reason: str             # human-readable description


# ── Flow A: Agent 4 Output ────────────────────────────────────────────────────

@dataclass
class NLPContextResult:
    anomaly_result: AnomalyResult
    context_score: float            # 0.0 – 1.0
    explanation: str                # Claude's reasoning summary
    risk_signals: list[str] = field(default_factory=list)


# ── Flow A: Agent 5 Output ────────────────────────────────────────────────────

@dataclass
class AggregatedRisk:
    nlp_result: NLPContextResult
    rule_score: float
    anomaly_score: float
    context_score: float
    final_score: float              # 0 – 100
    risk_level: RiskLevel


# ── Flow A: Agent 6 Output ────────────────────────────────────────────────────

@dataclass
class DecisionResult:
    aggregated: AggregatedRisk
    decision: Decision


# ── Flow A: Final Pipeline Output (flat, UI-ready) ───────────────────────────

@dataclass
class FinalPipelineResult:
    vendor_id: str
    change_type: ChangeType
    old_value: str
    new_value: str
    request_source_email: str
    final_score: float
    risk_level: RiskLevel
    decision: Decision
    flags: list[str]
    anomaly_reason: str
    nlp_explanation: str
    nlp_risk_signals: list[str]
    human_explanation: str
    rule_score: float
    anomaly_score: float
    context_score: float


# ── Flow B: Excel Pipeline Output ────────────────────────────────────────────

@dataclass
class ExcelPipelineResult:
    output_bytes: bytes                         # in-memory xlsx for download
    total_rows: int
    active_count: int
    inactive_count: int
    pending_count: int
    preview_records: list[dict]                 # first 50 rows as list-of-dicts
    reason_summary: dict[str, int]              # {"Missing GDPR": 4, ...}
