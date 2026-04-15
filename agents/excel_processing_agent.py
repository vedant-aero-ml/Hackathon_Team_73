"""
Excel Processing Agent (Flow B)

Reads a vendor master Excel file, computes a Status column based on
GDPR and ECCN field presence, adds a Reason column, and returns
a summary alongside the processed file bytes.
"""
from __future__ import annotations

import io
from collections import Counter

import pandas as pd

from models.schemas import ExcelPipelineResult, VendorStatus


class ExcelProcessingAgent:
    """
    Processes vendor master Excel data:
      - ACTIVE   : GDPR present AND ECCN present
      - INACTIVE : GDPR missing AND ECCN missing
      - PENDING  : exactly one of GDPR / ECCN is missing
    Adds a 'Reason' column explaining the status for non-ACTIVE rows.
    """

    REQUIRED_COLUMNS: list[str] = [
        "Business Partner",
        "Name",
        "GDPR",
        "ECCN",
    ]

    def run(self, file_input) -> ExcelPipelineResult:
        df = self._read_and_validate(file_input)
        df = self._compute_status(df)
        return self._build_result(df)

    # ── Core processing steps ────────────────────────────────────────────────

    def _read_and_validate(self, file_input) -> pd.DataFrame:
        name = getattr(file_input, "name", "")
        if str(name).lower().endswith(".csv"):
            df = pd.read_csv(file_input)
        else:
            df = pd.read_excel(file_input, engine="openpyxl")
        # Normalize column headers (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]

        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Excel file is missing required column(s): {missing}. "
                f"Found columns: {list(df.columns)}"
            )
        return df

    def _is_missing(self, value) -> bool:
        """Return True if value represents a missing/blank entry."""
        if pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def _compute_status(self, df: pd.DataFrame) -> pd.DataFrame:
        statuses: list[str] = []
        reasons: list[str] = []

        for _, row in df.iterrows():
            gdpr_missing = self._is_missing(row.get("GDPR"))
            eccn_missing = self._is_missing(row.get("ECCN"))

            if not gdpr_missing and not eccn_missing:
                statuses.append(VendorStatus.ACTIVE.value)
                reasons.append("")
            elif gdpr_missing and eccn_missing:
                statuses.append(VendorStatus.INACTIVE.value)
                reasons.append("Both missing")
            elif gdpr_missing:
                statuses.append(VendorStatus.PENDING.value)
                reasons.append("Missing GDPR")
            else:
                statuses.append(VendorStatus.PENDING.value)
                reasons.append("Missing ECCN")

        df = df.copy()
        df["Status"] = statuses
        df["Reason"] = reasons
        return df

    def _build_result(self, df: pd.DataFrame) -> ExcelPipelineResult:
        # Serialize to in-memory xlsx
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        output_bytes = buffer.getvalue()

        # Summary counts
        status_counts = Counter(df["Status"].tolist())
        total_rows = len(df)

        # Reason breakdown (exclude empty reasons for ACTIVE rows)
        reason_counts: dict[str, int] = Counter(
            r for r in df["Reason"].tolist() if r
        )

        # Preview — first 50 rows, convert NaN to None for JSON safety
        preview_df = df.head(50).where(pd.notnull(df), other=None)
        preview_records = preview_df.to_dict(orient="records")

        return ExcelPipelineResult(
            output_bytes=output_bytes,
            total_rows=total_rows,
            active_count=status_counts.get(VendorStatus.ACTIVE.value, 0),
            inactive_count=status_counts.get(VendorStatus.INACTIVE.value, 0),
            pending_count=status_counts.get(VendorStatus.PENDING.value, 0),
            preview_records=preview_records,
            reason_summary=dict(reason_counts),
        )
