"""
SQLAlchemy ORM Models for Phase 2: Financial Document Extraction

Maps to database tables:
- counterparties_master
- uploaded_documents
- financial_metrics_extracted
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship, Mapped

from api.db.base import Base


class CounterpartyMaster(Base):
    """Master list of counterparties (fuel suppliers, traders, etc.)."""

    __tablename__ = "counterparties_master"
    __allow_unmapped__ = True  # Allow unmapped type hints for compatibility

    id = Column(Integer, primary_key=True, index=True)
    counterparty_name = Column(String(255), nullable=False, unique=True, index=True)
    counterparty_type = Column(String(50), nullable=True)  # e.g., "airline", "trader"
    country = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    uploaded_documents = relationship(
        "UploadedDocument", back_populates="counterparty"
    )
    financial_metrics = relationship(
        "FinancialMetricsExtracted", back_populates="counterparty"
    )

    def __repr__(self):
        return f"<CounterpartyMaster({self.counterparty_name}, {self.counterparty_type}, {self.country})>"


class UploadedDocument(Base):
    """Uploaded PDF financial documents."""

    __tablename__ = "uploaded_documents"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(
        Integer, ForeignKey("counterparties_master.id"), nullable=False, index=True
    )
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=True)  # e.g., "annual_report"
    file_size_bytes = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    extraction_status = Column(
        String(50), nullable=True, default="pending"
    )  # pending, processing, completed, failed
    extraction_error = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)  # user who uploaded
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (UniqueConstraint("counterparty_id", "filename"),)

    # Relationships
    counterparty = relationship(
        "CounterpartyMaster", back_populates="uploaded_documents"
    )
    financial_metrics = relationship(
        "FinancialMetricsExtracted",
        back_populates="uploaded_document",
        foreign_keys="FinancialMetricsExtracted.uploaded_document_id",
    )

    def __repr__(self):
        return f"<UploadedDocument({self.filename}, status={self.extraction_status})>"


class FinancialMetricsExtracted(Base):
    """Extracted financial metrics from uploaded documents."""

    __tablename__ = "financial_metrics_extracted"
    __allow_unmapped__ = True

    # Primary & Foreign Keys
    id = Column(Integer, primary_key=True, index=True)
    uploaded_document_id = Column(
        Integer, ForeignKey("uploaded_documents.id"), nullable=False, index=True
    )
    counterparty_id = Column(
        Integer, ForeignKey("counterparties_master.id"), nullable=False, index=True
    )

    # Metadata
    fiscal_year = Column(Integer, nullable=True, index=True)
    fiscal_period = Column(String(10), nullable=True)  # e.g., "Q1", "FY2022"

    # Income Statement (DECIMAL(20,2) = 18 digits + 2 decimals)
    revenue = Column(Numeric(20, 2), nullable=True)
    cost_of_goods_sold = Column(Numeric(20, 2), nullable=True)
    operating_expenses = Column(Numeric(20, 2), nullable=True)
    ebitda = Column(Numeric(20, 2), nullable=True)
    ebit = Column(Numeric(20, 2), nullable=True)
    interest_expense = Column(Numeric(20, 2), nullable=True)
    net_income = Column(Numeric(20, 2), nullable=True)

    # Balance Sheet - Assets
    cash_and_equivalents = Column(Numeric(20, 2), nullable=True)
    short_term_investments = Column(Numeric(20, 2), nullable=True)
    accounts_receivable = Column(Numeric(20, 2), nullable=True)
    inventory = Column(Numeric(20, 2), nullable=True)
    other_current_assets = Column(Numeric(20, 2), nullable=True)
    current_assets = Column(Numeric(20, 2), nullable=True)
    ppe_gross = Column(Numeric(20, 2), nullable=True)
    accumulated_depreciation = Column(Numeric(20, 2), nullable=True)
    ppe_net = Column(Numeric(20, 2), nullable=True)
    intangible_assets = Column(Numeric(20, 2), nullable=True)
    goodwill = Column(Numeric(20, 2), nullable=True)
    total_assets = Column(Numeric(20, 2), nullable=True)

    # Balance Sheet - Liabilities & Equity
    accounts_payable = Column(Numeric(20, 2), nullable=True)
    short_term_debt = Column(Numeric(20, 2), nullable=True)
    current_portion_long_term_debt = Column(Numeric(20, 2), nullable=True)
    other_current_liabilities = Column(Numeric(20, 2), nullable=True)
    current_liabilities = Column(Numeric(20, 2), nullable=True)
    long_term_debt = Column(Numeric(20, 2), nullable=True)
    total_debt = Column(Numeric(20, 2), nullable=True)
    other_long_term_liabilities = Column(Numeric(20, 2), nullable=True)
    total_liabilities = Column(Numeric(20, 2), nullable=True)
    shareholders_equity = Column(Numeric(20, 2), nullable=True)
    retained_earnings = Column(Numeric(20, 2), nullable=True)

    # Cash Flow
    operating_cash_flow = Column(Numeric(20, 2), nullable=True)
    investing_cash_flow = Column(Numeric(20, 2), nullable=True)
    financing_cash_flow = Column(Numeric(20, 2), nullable=True)
    free_cash_flow = Column(Numeric(20, 2), nullable=True)

    # Metadata
    currency = Column(String(3), nullable=True, default="USD")  # ISO 4217 code
    extraction_confidence = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0
    missing_critical_fields = Column(JSON, nullable=True)
    original_text_references = Column(JSON, nullable=True)
    extraction_warnings = Column(JSON, nullable=True)
    source_document_id = Column(
        Integer, ForeignKey("uploaded_documents.id"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint("uploaded_document_id", "fiscal_year"),
        Index("idx_financial_metrics_counterparty", "counterparty_id"),
        Index("idx_financial_metrics_doc", "uploaded_document_id"),
    )

    # Relationships
    uploaded_document = relationship(
        "UploadedDocument",
        back_populates="financial_metrics",
        foreign_keys=[uploaded_document_id],
    )
    counterparty = relationship(
        "CounterpartyMaster", back_populates="financial_metrics"
    )
    financial_ratios = relationship(
        "FinancialRatios",
        back_populates="financial_metrics",
        uselist=False,
        foreign_keys="FinancialRatios.financial_metrics_id",
    )

    def __repr__(self):
        return f"<FinancialMetricsExtracted(doc={self.uploaded_document_id}, year={self.fiscal_year})>"

    @property
    def period_type(self):
        refs = self.original_text_references if isinstance(self.original_text_references, dict) else {}
        return refs.get("period_type") or (
            "quarterly" if str(self.fiscal_period or "").upper() in {"Q1", "Q2", "Q3", "Q4"} else "annual"
        )

    @property
    def period_label(self):
        refs = self.original_text_references if isinstance(self.original_text_references, dict) else {}
        return refs.get("period_label") or self.fiscal_period

    @property
    def is_latest_snapshot(self):
        refs = self.original_text_references if isinstance(self.original_text_references, dict) else {}
        return refs.get("is_latest_snapshot")

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "uploaded_document_id": self.uploaded_document_id,
            "counterparty_id": self.counterparty_id,
            "fiscal_year": self.fiscal_year,
            "revenue": float(self.revenue) if self.revenue else None,
            "net_income": float(self.net_income) if self.net_income else None,
            "total_assets": float(self.total_assets) if self.total_assets else None,
            "total_liabilities": float(self.total_liabilities)
            if self.total_liabilities
            else None,
            "total_debt": float(self.total_debt) if self.total_debt else None,
            "shareholders_equity": float(self.shareholders_equity)
            if self.shareholders_equity
            else None,
            "currency": self.currency,
            "extraction_confidence": float(self.extraction_confidence)
            if self.extraction_confidence
            else None,
            "missing_critical_fields": self.missing_critical_fields,
            "original_text_references": self.original_text_references,
            "extraction_warnings": self.extraction_warnings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FinancialRatios(Base):
    """Financial ratios calculated from extracted financial statement data."""

    __tablename__ = "financial_ratios"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(
        Integer, ForeignKey("counterparties_master.id"), nullable=False, index=True
    )
    uploaded_document_id = Column(
        Integer, ForeignKey("uploaded_documents.id"), nullable=True, index=True
    )
    financial_metrics_id = Column(
        Integer,
        ForeignKey("financial_metrics_extracted.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    fiscal_year = Column(Integer, nullable=True, index=True)
    fiscal_period = Column(String(10), nullable=True)
    currency = Column(String(3), nullable=True)

    current_ratio = Column(Numeric(18, 6), nullable=True)
    quick_ratio = Column(Numeric(18, 6), nullable=True)
    cash_ratio = Column(Numeric(18, 6), nullable=True)
    working_capital = Column(Numeric(20, 2), nullable=True)
    debt_to_equity = Column(Numeric(18, 6), nullable=True)
    debt_to_ebitda = Column(Numeric(18, 6), nullable=True)
    liabilities_to_assets = Column(Numeric(18, 6), nullable=True)
    interest_coverage = Column(Numeric(18, 6), nullable=True)
    operating_margin = Column(Numeric(18, 6), nullable=True)
    net_margin = Column(Numeric(18, 6), nullable=True)
    return_on_assets = Column(Numeric(18, 6), nullable=True)
    return_on_equity = Column(Numeric(18, 6), nullable=True)

    formula_version = Column(String(50), nullable=False)
    calculation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    input_data_reference = Column(Text, nullable=True)
    missing_inputs = Column(JSON, nullable=True)
    calculation_warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    financial_metrics = relationship(
        "FinancialMetricsExtracted",
        back_populates="financial_ratios",
        foreign_keys=[financial_metrics_id],
    )

    def to_dict(self):
        """Convert ratio record to a JSON-friendly dictionary."""
        ratio_fields = [
            "current_ratio",
            "quick_ratio",
            "cash_ratio",
            "working_capital",
            "debt_to_equity",
            "debt_to_ebitda",
            "liabilities_to_assets",
            "interest_coverage",
            "operating_margin",
            "net_margin",
            "return_on_assets",
            "return_on_equity",
        ]
        data = {
            "id": self.id,
            "counterparty_id": self.counterparty_id,
            "uploaded_document_id": self.uploaded_document_id,
            "financial_metrics_id": self.financial_metrics_id,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "currency": self.currency,
            "formula_version": self.formula_version,
            "calculation_date": self.calculation_date.isoformat()
            if self.calculation_date
            else None,
            "input_data_reference": self.input_data_reference,
            "missing_inputs": self.missing_inputs,
            "calculation_warnings": self.calculation_warnings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        for field_name in ratio_fields:
            value = getattr(self, field_name)
            data[field_name] = float(value) if value is not None else None
        return data


# Export models
__all__ = [
    "CounterpartyMaster",
    "UploadedDocument",
    "FinancialMetricsExtracted",
    "FinancialRatios",
    "Base",
]


