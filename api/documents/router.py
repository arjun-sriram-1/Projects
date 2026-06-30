"""
FastAPI routes for Phase 2: Financial document upload and extraction.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.documents.pdf_parser import PDFFinancialParser
from api.documents.service import list_counterparties
from api.db.models import (
    CounterpartyMaster,
    UploadedDocument,
    FinancialMetricsExtracted,
)
from api.documents.schemas import (
    CounterpartyCreate,
    CounterpartyResponse,
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentWithMetricsResponse,
    FinancialMetricsResponse,
)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Upload directory
UPLOAD_DIR = Path("data/uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/counterparties", response_model=CounterpartyResponse)
def create_counterparty(
    counterparty: CounterpartyCreate, db: Session = Depends(get_db)
):
    """Create or get a counterparty."""
    # Check if counterparty exists
    existing = db.query(CounterpartyMaster).filter_by(
        counterparty_name=counterparty.counterparty_name
    ).first()

    if existing:
        return existing

    # Create new counterparty
    new_counterparty = CounterpartyMaster(
        counterparty_name=counterparty.counterparty_name,
        counterparty_type=counterparty.counterparty_type,
        country=counterparty.country,
    )
    db.add(new_counterparty)
    db.commit()
    db.refresh(new_counterparty)
    return new_counterparty


@router.get("/counterparties", response_model=list[CounterpartyResponse])
def get_counterparties(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List/search counterparties for the analyst selector."""
    return list_counterparties(db, search=search, limit=limit)


@router.delete("/counterparties/{counterparty_id}")
def delete_counterparty(counterparty_id: int, db: Session = Depends(get_db)):
    """Delete a counterparty and all stored project data tied to it."""
    counterparty = db.query(CounterpartyMaster).filter_by(id=counterparty_id).first()
    if not counterparty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counterparty with ID {counterparty_id} not found",
        )

    docs = db.query(UploadedDocument).filter_by(counterparty_id=counterparty_id).all()
    deleted_files = 0
    upload_root = UPLOAD_DIR.resolve()
    for doc in docs:
        try:
            file_path = Path(doc.file_path).resolve()
            if file_path.exists() and upload_root in file_path.parents:
                file_path.unlink()
                deleted_files += 1
        except Exception:
            pass

    delete_tables = [
        "ai_credit_memos",
        "credit_recommendations",
        "loss_estimates",
        "trade_exposures",
        "pd_model_predictions",
        "historical_training_dataset",
        "financial_ratios",
        "financial_metrics_extracted",
        "uploaded_documents",
    ]
    deleted_rows: dict[str, int] = {}
    try:
        for table in delete_tables:
            exists = db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table}).scalar()
            if not exists:
                deleted_rows[table] = 0
                continue
            result = db.execute(
                text(f"DELETE FROM {table} WHERE counterparty_id = :counterparty_id"),
                {"counterparty_id": counterparty_id},
            )
            deleted_rows[table] = int(result.rowcount or 0)
        db.delete(counterparty)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete counterparty data: {exc}",
        ) from exc

    return {
        "message": "Counterparty and related stored data deleted.",
        "counterparty_id": counterparty_id,
        "deleted_files": deleted_files,
        "deleted_rows": deleted_rows,
    }


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    counterparty_id: int = None,
    counterparty_name: str = None,
    document_type: str = "annual_report",
    created_by: str = None,
    db: Session = Depends(get_db),
):
    """
    Upload a financial document (PDF).

    Either provide counterparty_id or counterparty_name.
    """
    # Validate file is PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    # Get or create counterparty
    if counterparty_id:
        counterparty = db.query(CounterpartyMaster).filter_by(id=counterparty_id).first()
        if not counterparty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Counterparty with ID {counterparty_id} not found",
            )
    elif counterparty_name:
        counterparty = db.query(CounterpartyMaster).filter_by(
            counterparty_name=counterparty_name
        ).first()
        if not counterparty:
            # Create new counterparty
            counterparty = CounterpartyMaster(counterparty_name=counterparty_name)
            db.add(counterparty)
            db.commit()
            db.refresh(counterparty)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either counterparty_id or counterparty_name is required",
        )

    # Save file
    safe_filename = Path(file.filename).name.replace(" ", "_")
    file_path = UPLOAD_DIR / f"{counterparty.id}_{int(datetime.utcnow().timestamp())}_{safe_filename}"
    file_content = await file.read()
    file_size_bytes = len(file_content)
    
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Create UploadedDocument record
    doc = UploadedDocument(
        counterparty_id=counterparty.id,
        filename=file.filename,
        file_path=str(file_path),
        document_type=document_type,
        file_size_bytes=file_size_bytes,
        extraction_status="pending",
        created_by=created_by,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Queue extraction task (would normally be async via Celery, RabbitMQ, etc.)
    # For now, extract synchronously
    try:
        extract_financial_document_task(doc.id, str(file_path), db)
    except Exception as e:
        doc.extraction_status = "failed"
        doc.extraction_error = str(e)
        db.commit()

    return DocumentUploadResponse(
        id=doc.id,
        counterparty_id=doc.counterparty_id,
        filename=doc.filename,
        file_path=doc.file_path,
        extraction_status=doc.extraction_status,
        uploaded_at=doc.uploaded_at,
        message="Document uploaded successfully.",
    )


@router.get("/status/{document_id}", response_model=DocumentWithMetricsResponse)
def get_document_status(document_id: int, db: Session = Depends(get_db)):
    """Get document status and extracted metrics."""
    doc = db.query(UploadedDocument).filter_by(id=document_id).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get extracted metrics
    metrics = db.query(FinancialMetricsExtracted).filter_by(
        uploaded_document_id=document_id
    ).first()

    return DocumentWithMetricsResponse(
        id=doc.id,
        counterparty_id=doc.counterparty_id,
        filename=doc.filename,
        extraction_status=doc.extraction_status,
        extraction_error=doc.extraction_error,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
        financial_metrics=FinancialMetricsResponse.from_orm(metrics) if metrics else None,
    )


@router.get("/counterparty/{counterparty_id}")
def get_counterparty_documents(counterparty_id: int, db: Session = Depends(get_db)):
    """Get all documents for a counterparty."""
    docs = db.query(UploadedDocument).filter_by(counterparty_id=counterparty_id).all()

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No documents found for counterparty {counterparty_id}",
        )

    return [
        DocumentStatusResponse.from_orm(doc) for doc in docs
    ]


def extract_financial_document_task(
    document_id: int,
    file_path: str,
    db: Session = Depends(get_db),
):
    """
    Extract financial metrics from document.
    In production, this would be an async task queue task.
    """
    doc = db.query(UploadedDocument).filter_by(id=document_id).first()

    if not doc:
        raise ValueError(f"Document {document_id} not found")

    try:
        # Update status to processing
        doc.extraction_status = "processing"
        db.commit()

        # Parse PDF
        parser = PDFFinancialParser()
        extracted_data = parser.parse_pdf(file_path)

        # Create FinancialMetricsExtracted record
        metrics = FinancialMetricsExtracted(
            uploaded_document_id=document_id,
            counterparty_id=doc.counterparty_id,
            fiscal_year=extracted_data.fiscal_year,
            currency=extracted_data.currency,
            extraction_confidence=extracted_data.extraction_confidence,
            missing_critical_fields=extracted_data.missing_critical_fields,
            original_text_references=extracted_data.original_text_references,
            extraction_warnings=extracted_data.extraction_warnings,
            source_document_id=document_id,
            # Income Statement
            revenue=extracted_data.revenue,
            cost_of_goods_sold=extracted_data.cost_of_goods_sold,
            operating_expenses=extracted_data.operating_expenses,
            ebitda=extracted_data.ebitda,
            ebit=extracted_data.ebit,
            interest_expense=extracted_data.interest_expense,
            net_income=extracted_data.net_income,
            # Balance Sheet Assets
            cash_and_equivalents=extracted_data.cash_and_equivalents,
            short_term_investments=extracted_data.short_term_investments,
            accounts_receivable=extracted_data.accounts_receivable,
            inventory=extracted_data.inventory,
            current_assets=extracted_data.current_assets,
            ppe_net=extracted_data.ppe_net,
            total_assets=extracted_data.total_assets,
            # Balance Sheet Liabilities & Equity
            accounts_payable=extracted_data.accounts_payable,
            short_term_debt=extracted_data.short_term_debt,
            current_liabilities=extracted_data.current_liabilities,
            long_term_debt=extracted_data.long_term_debt,
            total_debt=extracted_data.total_debt,
            total_liabilities=extracted_data.total_liabilities,
            shareholders_equity=extracted_data.shareholders_equity,
            retained_earnings=extracted_data.retained_earnings,
            # Cash Flow
            operating_cash_flow=extracted_data.operating_cash_flow,
            investing_cash_flow=extracted_data.investing_cash_flow,
            financing_cash_flow=extracted_data.financing_cash_flow,
            free_cash_flow=extracted_data.free_cash_flow,
        )
        db.add(metrics)

        # Update document status
        doc.extraction_status = "completed"
        doc.processed_at = datetime.utcnow()
        doc.extraction_error = None

        db.commit()

    except Exception as e:
        # Update document with error
        doc.extraction_status = "failed"
        doc.extraction_error = str(e)
        db.commit()
        raise


__all__ = ["router"]

