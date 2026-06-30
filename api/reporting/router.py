"""Reporting/export API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from api.core.config import settings
from api.rag.exports.memo_service import generate_memo_files
from api.reporting.report_generator import generate_report_data
from api.reporting.model_validation import build_model_validation_report
from api.reporting.report_pdf import create_risk_report_pdf
from api.reporting.schemas import MemoExportRequest, MemoExportResponse, ModelValidationRequest, ModelValidationResponse, RiskReportExportResponse

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])


def _safe_report_stem(company_name: Optional[str]) -> str:
    if not company_name:
        return "portfolio_risk_report"
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in company_name.strip())
    return (safe.strip("._") or "portfolio_risk_report").lower() + "_risk_report"


@router.post("/memo/export", response_model=MemoExportResponse)
def export_credit_memo(request: MemoExportRequest):
    """Export grounded memo text to DOCX/PDF files."""
    return generate_memo_files(
        request.question,
        output_dir=request.output_dir,
        docx_filename=request.docx_filename,
        pdf_filename=request.pdf_filename,
    )


@router.get("/risk-report/export", response_model=RiskReportExportResponse)
def export_risk_report(company_name: Optional[str] = None, output_file: Optional[str] = None):
    """Export portfolio/company risk report PDF from stored model outputs."""
    report_data = generate_report_data(company_name=company_name)
    report_file = Path(output_file) if output_file else settings.report_dir / f"{_safe_report_stem(company_name)}.pdf"
    create_risk_report_pdf(report_data, report_file)

    return RiskReportExportResponse(
        report_file=str(report_file),
        company_name=company_name,
        total_exposure=float(report_data["total_exposure"]),
        total_expected_loss=float(report_data["total_expected_loss"]),
        avg_pd=float(report_data["avg_pd"]),
        avg_lgd=float(report_data["avg_lgd"]),
        source="stored V2 reporting data",
    )
@router.post("/model-validation/report", response_model=ModelValidationResponse)
def create_model_validation_report(request: ModelValidationRequest):
    """Build a formal model validation report from supplied benchmark arrays."""
    report = build_model_validation_report(**request.model_dump())
    return ModelValidationResponse(**report.to_dict())

