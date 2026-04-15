"""
Input validation utilities for vendor change requests.
"""
from __future__ import annotations

from datetime import datetime


class ValidationError(ValueError):
    """Raised when a required field is missing or malformed."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


_REQUIRED_FIELDS = (
    "vendor_id",
    "change_type",
    "old_value",
    "new_value",
    "request_source_email",
    "timestamp",
)

_VALID_CHANGE_TYPES = {"bank_account", "email", "address", "name"}


def validate_vendor_change_input(raw: dict) -> None:
    """
    Validate a raw vendor change request dict.
    Raises ValidationError on the first failure encountered.
    """
    for field in _REQUIRED_FIELDS:
        if field not in raw:
            raise ValidationError(field, "required field is missing")
        value = raw[field]
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(field, "must be a non-empty string")

    change_type = raw["change_type"].strip().lower()
    if change_type not in _VALID_CHANGE_TYPES:
        raise ValidationError(
            "change_type",
            f"must be one of {sorted(_VALID_CHANGE_TYPES)}, got '{change_type}'",
        )

    email = raw["request_source_email"].strip()
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValidationError(
            "request_source_email",
            f"must be a valid email address, got '{email}'",
        )

    ts = raw["timestamp"].strip()
    try:
        datetime.fromisoformat(ts)
    except ValueError:
        raise ValidationError(
            "timestamp",
            f"must be ISO-8601 format (e.g. '2026-04-15T10:00:00'), got '{ts}'",
        )
