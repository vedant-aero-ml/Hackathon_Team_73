"""
Flow B: Excel Vendor Status Pipeline

Single-agent orchestrator for Excel processing.
"""
from __future__ import annotations

from agents.excel_processing_agent import ExcelProcessingAgent
from models.schemas import ExcelPipelineResult


def run_excel_pipeline(file_input) -> ExcelPipelineResult:
    """
    Process an uploaded Excel file and compute vendor status classifications.

    Args:
        file_input: A file-like object (from st.file_uploader or open()).

    Returns:
        ExcelPipelineResult — summary metrics + processed file bytes.

    Raises:
        ValueError: if the file is missing required columns.
    """
    return ExcelProcessingAgent().run(file_input)
