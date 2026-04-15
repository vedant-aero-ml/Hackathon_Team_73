"""
In-memory mock vendor history store.

Each entry represents one past change event for a vendor:
  event_id    : str
  vendor_id   : str
  change_type : str   (ChangeType value)
  old_value   : str
  new_value   : str
  timestamp   : str   (ISO-8601 date, YYYY-MM-DD)
  approved    : bool
  risk_level  : str | None
"""
from __future__ import annotations

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Static history entries
# ---------------------------------------------------------------------------
_STATIC_HISTORY: dict[str, list[dict]] = {
    # V001 — suspicious: 2 HIGH risk events, 2 rejections
    "V001": [
        {
            "event_id": "E001",
            "vendor_id": "V001",
            "change_type": "email",
            "old_value": "billing@acmecorp.com",
            "new_value": "acme.billing@gmail.com",
            "timestamp": "2025-12-10",
            "approved": False,
            "risk_level": "HIGH",
        },
        {
            "event_id": "E002",
            "vendor_id": "V001",
            "change_type": "bank_account",
            "old_value": "DE89370400440532013000",
            "new_value": "GB29NWBK60161331926819",
            "timestamp": "2026-01-15",
            "approved": True,
            "risk_level": "MEDIUM",
        },
        {
            "event_id": "E003",
            "vendor_id": "V001",
            "change_type": "address",
            "old_value": "123 Main St, Berlin",
            "new_value": "456 Oak Ave, Hamburg",
            "timestamp": "2026-02-20",
            "approved": True,
            "risk_level": "LOW",
        },
        {
            "event_id": "E004",
            "vendor_id": "V001",
            "change_type": "bank_account",
            "old_value": "GB29NWBK60161331926819",
            "new_value": "FR7630006000011234567890189",
            "timestamp": "2026-03-01",
            "approved": False,
            "risk_level": "HIGH",
        },
        {
            "event_id": "E005",
            "vendor_id": "V001",
            "change_type": "email",
            "old_value": "acme.billing@gmail.com",
            "new_value": "finance@acmecorp.com",
            "timestamp": "2026-03-20",
            "approved": True,
            "risk_level": "LOW",
        },
    ],
    # V002 — moderate risk: one HIGH rejection
    "V002": [
        {
            "event_id": "E006",
            "vendor_id": "V002",
            "change_type": "name",
            "old_value": "GlobalTech Ltd",
            "new_value": "GlobalTech International Ltd",
            "timestamp": "2025-11-05",
            "approved": True,
            "risk_level": "LOW",
        },
        {
            "event_id": "E007",
            "vendor_id": "V002",
            "change_type": "bank_account",
            "old_value": "US1234567890",
            "new_value": "CN9876543210",
            "timestamp": "2026-03-30",
            "approved": False,
            "risk_level": "HIGH",
        },
    ],
    # V003 — clean: single approved address change
    "V003": [
        {
            "event_id": "E008",
            "vendor_id": "V003",
            "change_type": "address",
            "old_value": "10 Rue de Rivoli, Paris",
            "new_value": "22 Avenue Montaigne, Paris",
            "timestamp": "2025-06-01",
            "approved": True,
            "risk_level": "LOW",
        },
    ],
    # V999 — new vendor: no history
    "V999": [],
}

# V004 — high-frequency changer: 6 bank_account changes in March 2026
_v004_base = date(2026, 3, 1)
_V004_ENTRIES = [
    {
        "event_id": f"E{9 + i:03d}",
        "vendor_id": "V004",
        "change_type": "bank_account",
        "old_value": f"ACC{i:04d}",
        "new_value": f"ACC{i + 1:04d}",
        "timestamp": (_v004_base + timedelta(days=i)).isoformat(),
        "approved": i % 2 == 0,
        "risk_level": "HIGH",
    }
    for i in range(6)
]

VENDOR_HISTORY: dict[str, list[dict]] = {
    **_STATIC_HISTORY,
    "V004": _V004_ENTRIES,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_vendor_history(vendor_id: str) -> list[dict]:
    """Return full change history for a vendor; empty list for unknown vendors."""
    return VENDOR_HISTORY.get(vendor_id, [])


def get_recent_change_count(vendor_id: str, window_days: int = 90) -> int:
    """Count changes within the last *window_days* days relative to today."""
    cutoff = date.today() - timedelta(days=window_days)
    history = get_vendor_history(vendor_id)
    count = 0
    for evt in history:
        try:
            if date.fromisoformat(evt["timestamp"]) >= cutoff:
                count += 1
        except (ValueError, KeyError):
            pass
    return count


def get_all_vendor_ids() -> list[str]:
    """Return all known vendor IDs (for population-level anomaly analysis)."""
    return list(VENDOR_HISTORY.keys())
