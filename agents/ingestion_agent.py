"""
Agent 1: Ingestion Agent

Normalizes raw vendor change request input, extracts the email domain,
and attaches vendor history from the in-memory mock store.
"""
from __future__ import annotations

from data.mock_vendor_history import get_vendor_history
from models.schemas import ChangeType, NormalizedVendorChange
from utils.validators import validate_vendor_change_input


class IngestionAgent:
    """
    Validates and normalizes a raw vendor change request dict.
    Raises ValidationError (from utils.validators) on invalid input.
    """

    def run(self, raw_input: dict) -> NormalizedVendorChange:
        validate_vendor_change_input(raw_input)

        vendor_id = raw_input["vendor_id"].strip()
        change_type = ChangeType(raw_input["change_type"].strip().lower())
        old_value = raw_input["old_value"].strip()
        new_value = raw_input["new_value"].strip()
        email = raw_input["request_source_email"].strip().lower()
        timestamp = raw_input["timestamp"].strip()

        email_domain = self._extract_email_domain(email)
        vendor_history = get_vendor_history(vendor_id)

        return NormalizedVendorChange(
            vendor_id=vendor_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            request_source_email=email,
            email_domain=email_domain,
            timestamp=timestamp,
            vendor_history=vendor_history,
        )

    def _extract_email_domain(self, email: str) -> str:
        """Return the domain portion of an email address; 'unknown' if malformed."""
        try:
            return email.split("@")[1].lower()
        except (IndexError, AttributeError):
            return "unknown"
