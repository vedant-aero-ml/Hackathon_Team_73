"""
Central configuration for the Vendor Master Governance system.
All tunables live here — never hard-coded inside agents.
"""

# ── SAP AI SDK / OpenAI model ─────────────────────────────────────────────────
MODEL_NAME: str = "gpt-4o-mini"   # passed as model_name to gen_ai_hub chat
MAX_TOKENS: int = 1_000

# ── Risk Score Weights (must sum to 1.0) ─────────────────────────────────────
WEIGHT_RULE: float = 0.35
WEIGHT_ANOMALY: float = 0.30
WEIGHT_NLP: float = 0.35

# ── Decision Thresholds (final_score is 0–100) ────────────────────────────────
THRESHOLD_HIGH: float = 70.0
THRESHOLD_MEDIUM: float = 40.0

# ── Free / Personal Email Domains ─────────────────────────────────────────────
FREE_EMAIL_DOMAINS: set = {
    "gmail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "hotmail.com",
    "hotmail.co.uk",
    "gmx.com",
    "gmx.net",
    "gmx.de",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "me.com",
    "protonmail.com",
    "proton.me",
    "mail.com",
    "yandex.com",
    "yandex.ru",
    "web.de",
    "freenet.de",
    "t-online.de",
}

# ── Anomaly Detection Parameters ─────────────────────────────────────────────
ANOMALY_HISTORY_WINDOW_DAYS: int = 90
ANOMALY_ZSCORE_THRESHOLD: float = 2.0
ANOMALY_ABSOLUTE_THRESHOLD: int = 3  # flag if > 3 changes in window
