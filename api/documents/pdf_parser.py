"""
PDF Financial Data Extraction Module

Business purpose:
Extract structured financial statement metrics from uploaded annual reports so the
credit workflow can calculate ratios, PD, LGD/EAD context, expected loss, and a
traceable trade credit recommendation.

Inputs:
PDF annual reports or financial statements containing text and/or tables.

Outputs:
ExtractedFinancialData with normalized values, extraction confidence, missing
critical field warnings, and short source text references for auditability.

Assumptions and limitations:
This parser uses deterministic table/text matching, not an LLM. It is suitable
for clean digital PDFs and student-project demos. Scanned documents may need OCR
support later, and ambiguous line items are flagged through missing fields rather
than silently invented.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pdfplumber

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional OCR dependency
    pytesseract = None


def _extract_page_text_with_ocr(page, warnings: List[str]) -> str:
    """Extract digital text first, then OCR only when a page has no text."""
    digital_text = page.extract_text() or ""
    if digital_text.strip():
        return digital_text
    if pytesseract is None:
        warnings.append("Page had no digital text and pytesseract is not installed; OCR skipped.")
        return ""
    try:
        image = page.to_image(resolution=200).original
        ocr_text = pytesseract.image_to_string(image) or ""
        if not ocr_text.strip():
            warnings.append("OCR ran but extracted no text from a scanned/blank page.")
        return ocr_text
    except Exception as exc:  # pragma: no cover - OCR environment dependent
        warnings.append(f"OCR fallback failed: {exc}")
        return ""


@dataclass
class ExtractedFinancialData:
    """Container for extracted financial metrics from a PDF."""

    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    currency: Optional[str] = None

    revenue: Optional[float] = None
    cost_of_goods_sold: Optional[float] = None
    operating_expenses: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    interest_expense: Optional[float] = None
    net_income: Optional[float] = None

    cash_and_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    other_current_assets: Optional[float] = None
    current_assets: Optional[float] = None
    ppe_gross: Optional[float] = None
    accumulated_depreciation: Optional[float] = None
    ppe_net: Optional[float] = None
    intangible_assets: Optional[float] = None
    goodwill: Optional[float] = None
    total_assets: Optional[float] = None

    accounts_payable: Optional[float] = None
    short_term_debt: Optional[float] = None
    current_portion_long_term_debt: Optional[float] = None
    other_current_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_debt: Optional[float] = None
    other_long_term_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    retained_earnings: Optional[float] = None

    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None

    extraction_confidence: Optional[float] = None
    missing_critical_fields: List[str] = field(default_factory=list)
    original_text_references: Dict[str, str] = field(default_factory=dict)
    extraction_warnings: List[str] = field(default_factory=list)

    CRITICAL_FIELDS = (
        "revenue",
        "ebitda",
        "ebit",
        "net_income",
        "cash_and_equivalents",
        "total_assets",
        "current_assets",
        "total_liabilities",
        "current_liabilities",
        "total_debt",
        "shareholders_equity",
        "interest_expense",
        "operating_cash_flow",
        "accounts_receivable",
        "accounts_payable",
        "inventory",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {key: value for key, value in asdict(self).items() if value is not None}

    def confidence_score(self) -> float:
        """Calculate extraction confidence against critical financial fields only."""
        extracted_fields = sum(1 for name in self.CRITICAL_FIELDS if getattr(self, name) is not None)
        return extracted_fields / len(self.CRITICAL_FIELDS)

    def finalize_quality_flags(self) -> None:
        """Set confidence, missing field list, and warnings after extraction."""
        self.missing_critical_fields = [name for name in self.CRITICAL_FIELDS if getattr(self, name) is None]
        self.extraction_confidence = round(self.confidence_score(), 2)
        if self.missing_critical_fields:
            self.extraction_warnings.append(
                "Missing critical financial fields: " + ", ".join(self.missing_critical_fields)
            )


class PDFFinancialParser:
    """Parse financial data from annual report PDFs."""

    def __init__(self):
        self.patterns = self._build_patterns()

    @staticmethod
    def _build_patterns() -> Dict[str, re.Pattern]:
        return {
            "revenue": re.compile(r"(revenue\s*from\s*operations|total\s*revenue|net\s*revenues?|sales|operating\s*revenues?)", re.IGNORECASE),
            "cost_of_goods_sold": re.compile(r"(cost\s*of\s*goods?\s*sold|cost\s*of\s*revenue|cost\s*of\s*sales)", re.IGNORECASE),
            "operating_expenses": re.compile(r"(operating\s*expenses?|sg&a|selling.*general.*admin)", re.IGNORECASE),
            "ebitda": re.compile(r"(\bebitda\b|\bebitdar\b|operating\s*income.*depreciation)", re.IGNORECASE),
            "ebit": re.compile(r"(\bebit\b|operating\s*income|operating\s*profit)", re.IGNORECASE),
            "interest_expense": re.compile(r"(interest\s*expense|interest\s*paid|finance\s*costs)", re.IGNORECASE),
            "net_income": re.compile(r"(net\s*income|net\s*profit|net\s*loss|profit\s*for\s*the\s*year)", re.IGNORECASE),
            "cash_and_equivalents": re.compile(r"(cash\s*and\s*equivalents|cash\s*and\s*cash\s*equivalents)", re.IGNORECASE),
            "short_term_investments": re.compile(r"(short\s*term\s*investments|marketable\s*securities)", re.IGNORECASE),
            "accounts_receivable": re.compile(r"(accounts\s*receivable|trade\s*receivables)", re.IGNORECASE),
            "inventory": re.compile(r"(inventory|inventories)", re.IGNORECASE),
            "current_assets": re.compile(r"(total\s*current\s*assets|current\s*assets)", re.IGNORECASE),
            "ppe_gross": re.compile(r"(property.*plant.*equipment.*gross|gross\s*ppe)", re.IGNORECASE),
            "ppe_net": re.compile(r"(net\s*ppe|property.*plant.*equipment.*net)", re.IGNORECASE),
            "total_assets": re.compile(r"(total\s*assets|total\s*balance\s*sheet\s*assets)", re.IGNORECASE),
            "accounts_payable": re.compile(r"(accounts\s*payable|trade\s*payables)", re.IGNORECASE),
            "short_term_debt": re.compile(r"(short\s*term\s*debt|current\s*portion\s*debt|current\s*borrowings)", re.IGNORECASE),
            "current_liabilities": re.compile(r"(total\s*current\s*liabilities|current\s*liabilities)", re.IGNORECASE),
            "long_term_debt": re.compile(r"(long\s*term\s*debt|long\s*term\s*borrowings|senior\s*debt)", re.IGNORECASE),
            "total_debt": re.compile(r"(total\s*debt|borrowings\s*total|total\s*borrowings)", re.IGNORECASE),
            "total_liabilities": re.compile(r"(total\s*liabilities|total\s*liabilities\s*and\s*equity)", re.IGNORECASE),
            "shareholders_equity": re.compile(r"(shareholders?.*equity|total.*equity|stockholders.*equity)", re.IGNORECASE),
            "retained_earnings": re.compile(r"(retained\s*earnings)", re.IGNORECASE),
            "operating_cash_flow": re.compile(r"(cash\s*from\s*operations|operating\s*activities)", re.IGNORECASE),
            "investing_cash_flow": re.compile(r"(cash\s*from\s*investing|investing\s*activities)", re.IGNORECASE),
            "financing_cash_flow": re.compile(r"(cash\s*from\s*financing|financing\s*activities)", re.IGNORECASE),
            "free_cash_flow": re.compile(r"(free\s*cash\s*flow|fcf)", re.IGNORECASE),
        }

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """Parse a number from text, handling compact K/M/B suffixes."""
        if not text or not isinstance(text, str):
            return None
        raw = text.strip()
        negative = raw.startswith("(") and raw.endswith(")")
        cleaned = (
            raw.replace("$", "")
            .replace("€", "")
            .replace("£", "")
            .replace("¥", "")
            .replace("₹", "")
            .replace("USD", "")
            .replace("INR", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace("(", "")
            .replace(")", "")
            .strip()
        )
        match = re.search(r"([-]?\d[\d,\.]*)([MmBbKk]?)", cleaned)
        if not match:
            return None
        num_str, multiplier = match.groups()
        try:
            num = float(num_str.replace(",", ""))
        except ValueError:
            return None
        if multiplier.upper() == "M":
            num *= 1_000_000
        elif multiplier.upper() == "B":
            num *= 1_000_000_000
        elif multiplier.upper() == "K":
            num *= 1_000
        return -num if negative else num

    @staticmethod
    def _statement_number_tokens(line: str) -> list[str]:
        return re.findall(r"\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\(?-?\d+(?:\.\d+)?\)?", line)

    @classmethod
    def _statement_values(cls, line: str, unit_multiplier: float = 1.0) -> list[float]:
        values: list[float] = []
        for token in cls._statement_number_tokens(line):
            if "," not in token:
                continue
            parsed = cls._parse_number(token)
            if parsed is not None:
                values.append(parsed * unit_multiplier)
        return values

    @classmethod
    def _first_statement_value(cls, line: str, unit_multiplier: float = 1.0) -> Optional[float]:
        values = cls._statement_values(line, unit_multiplier)
        return values[0] if values else None

    @staticmethod
    def _add_if_present(target: ExtractedFinancialData, field_name: str, value: Optional[float], reference: str) -> None:
        if value is not None and hasattr(target, field_name):
            setattr(target, field_name, value)
            target.original_text_references[field_name] = reference.strip()[:300]

    @staticmethod
    def _is_generic_field_candidate(field_name: str, text: str) -> bool:
        """Keep generic fallback extraction from grabbing cash-flow or total lines."""
        lower = re.sub(r"\s+", " ", text.lower()).strip()
        movement_line = re.search(r"\b(increase|decrease|changes?\s+in|net increase|net decrease)\b", lower)
        narrative_line = re.search(r"\b(increased|decreased|change|margin|pts|basis points)\b", lower)
        percent_only_line = "%" in lower and not re.search(r"\d{1,3}(?:,\d{3})+", lower)
        if field_name in {"ebit", "ebitda"} and (narrative_line or percent_only_line):
            return False
        if field_name in {"cash_and_equivalents", "accounts_receivable"} and movement_line:
            return False
        if field_name == "cash_and_equivalents" and "cash flows" in lower:
            return False
        if field_name == "shareholders_equity" and "liabilities" in lower:
            return False
        if field_name == "total_liabilities" and "equity and liabilities" in lower:
            return False
        return True

    def extract_unit_multiplier(self, text: str) -> float:
        lowered = text.lower()
        if re.search(r"rupees\s+in\s+millions|inr\s+in\s+millions|rs\.?\s+in\s+millions", lowered):
            return 1_000_000.0
        if re.search(r"rupees\s+in\s+crores|inr\s+in\s+crores|rs\.?\s+in\s+crores", lowered):
            return 10_000_000.0
        if re.search(r"\$\s*in\s+millions|usd\s+in\s+millions|dollars\s+in\s+millions", lowered):
            return 1_000_000.0
        return 1.0

    def extract_statement_metrics(self, text: str, unit_multiplier: float = 1.0) -> ExtractedFinancialData:
        """Extract statement values using section context so note numbers are ignored."""
        data = ExtractedFinancialData()
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n") if line.strip()]

        section = ""
        current_borrowings: Optional[float] = None
        current_lease_liabilities: Optional[float] = None
        non_current_lease_liabilities: Optional[float] = None
        non_current_liabilities: Optional[float] = None
        finance_costs: Optional[float] = None
        depreciation: Optional[float] = None
        profit_before_tax: Optional[float] = None
        trade_payables_parts: list[float] = []

        for line in lines:
            lower = line.lower()
            value = self._first_statement_value(line, unit_multiplier)

            if lower.startswith("non-current assets"):
                section = "non_current_assets"
            elif lower.startswith("current assets"):
                section = "current_assets"
            elif lower.startswith("equity and liabilities") or lower.startswith("equity"):
                section = "equity"
            elif lower.startswith("non-current liabilities"):
                section = "non_current_liabilities"
            elif lower.startswith("current liabilities"):
                section = "current_liabilities"
            elif "cash flows from operating activities" in lower:
                section = "cash_flow_operating"
            elif "cash flows from investing activities" in lower:
                section = "cash_flow_investing"
            elif "cash flows from financing activities" in lower:
                section = "cash_flow_financing"

            if re.match(r"^revenue from operations\b", lower):
                self._add_if_present(data, "revenue", value, line)
            elif re.match(r"^total income\b", lower) and data.revenue is None:
                self._add_if_present(data, "revenue", value, line)
            elif re.match(r"^finance costs\b", lower):
                finance_costs = value
                self._add_if_present(data, "interest_expense", value, line)
            elif re.match(r"^depreciation and amortisation expense\b", lower):
                depreciation = value
            elif lower.startswith("profit") and re.search(r"\bbefore tax(?:ation)?\b", lower):
                profit_before_tax = value
            elif re.match(r"^profit (?:/ \(loss\) )?(?:for the year|after tax)\b", lower):
                self._add_if_present(data, "net_income", value, line)
            elif re.match(r"^(?:a\. )?inventories\b", lower):
                self._add_if_present(data, "inventory", value, line)
            elif "trade receivables" in lower and section == "current_assets" and not re.search(r"\b(increase|decrease|changes?\s+in)\b", lower):
                self._add_if_present(data, "accounts_receivable", value, line)
            elif "cash and cash equivalents" in lower and section == "current_assets" and "bank balances other than" not in lower:
                self._add_if_present(data, "cash_and_equivalents", value, line)
            elif re.match(r"^total current assets\b", lower):
                self._add_if_present(data, "current_assets", value, line)
            elif re.match(r"^(?:a\. )?property, plant and equipment\b", lower):
                self._add_if_present(data, "ppe_net", value, line)
            elif re.match(r"^total assets\b", lower):
                self._add_if_present(data, "total_assets", value, line)
            elif re.match(r"^total equity\b", lower) and "liabilities" not in lower:
                self._add_if_present(data, "shareholders_equity", value, line)
            elif re.match(r"^total non-current liabilities\b", lower):
                non_current_liabilities = value
            elif re.match(r"^total current liabilities\b", lower):
                self._add_if_present(data, "current_liabilities", value, line)
            elif "lease liabilities" in lower:
                if section == "current_liabilities":
                    current_lease_liabilities = value
                elif section == "non_current_liabilities":
                    non_current_lease_liabilities = value
            elif re.match(r"^(?:\(i\) )?borrowings\b", lower):
                if section in {"current_liabilities", "non_current_liabilities"}:
                    current_borrowings = value
            elif "total outstanding dues of micro enterprises" in lower or "total outstanding dues of creditors other than" in lower:
                if value is not None:
                    trade_payables_parts.append(value)
            elif re.match(r"^net cash generated from operating activities\b", lower):
                self._add_if_present(data, "operating_cash_flow", value, line)
            elif re.match(r"^net cash used in investing activities\b", lower):
                self._add_if_present(data, "investing_cash_flow", value, line)
            elif re.match(r"^net cash used in financing activities\b", lower):
                self._add_if_present(data, "financing_cash_flow", value, line)

        if profit_before_tax is not None and finance_costs is not None:
            ebit = profit_before_tax + finance_costs
            self._add_if_present(data, "ebit", ebit, "Derived from profit before tax plus finance costs.")
            if depreciation is not None:
                self._add_if_present(data, "ebitda", ebit + depreciation, "Derived from EBIT plus depreciation and amortisation expense.")
        if data.ebit is None:
            profit_candidates = [
                self._first_statement_value(line, unit_multiplier)
                for line in lines
                if line.lower().startswith("profit") and re.search(r"\bbefore tax(?:ation)?\b", line.lower())
            ]
            finance_candidates = [
                self._first_statement_value(line, unit_multiplier)
                for line in lines
                if re.match(r"^finance costs\b", line.lower())
            ]
            depreciation_candidates = [
                self._first_statement_value(line, unit_multiplier)
                for line in lines
                if re.match(r"^depreciation and amortisation expense\b", line.lower())
            ]
            profit_value = next((value for value in profit_candidates if value is not None), None)
            finance_value = next((value for value in finance_candidates if value is not None), None)
            depreciation_value = next((value for value in depreciation_candidates if value is not None), None)
            if profit_value is not None and finance_value is not None:
                ebit = profit_value + finance_value
                self._add_if_present(data, "ebit", ebit, "Derived from profit before tax plus finance costs.")
                if depreciation_value is not None:
                    self._add_if_present(data, "ebitda", ebit + depreciation_value, "Derived from EBIT plus depreciation and amortisation expense.")
        if data.accounts_payable is None and trade_payables_parts:
            self._add_if_present(data, "accounts_payable", sum(trade_payables_parts), "Derived from trade payable components.")
        if data.total_liabilities is None:
            if non_current_liabilities is not None and data.current_liabilities is not None:
                self._add_if_present(data, "total_liabilities", non_current_liabilities + data.current_liabilities, "Derived from total non-current liabilities plus total current liabilities.")
            elif data.total_assets is not None and data.shareholders_equity is not None:
                self._add_if_present(data, "total_liabilities", data.total_assets - data.shareholders_equity, "Derived from total assets minus total equity.")
        debt_parts = [value for value in (current_borrowings, current_lease_liabilities, non_current_lease_liabilities) if value is not None]
        if debt_parts:
            self._add_if_present(data, "short_term_debt", (current_borrowings or 0.0) + (current_lease_liabilities or 0.0), "Derived from current borrowings plus current lease liabilities.")
            if non_current_lease_liabilities is not None:
                self._add_if_present(data, "long_term_debt", non_current_lease_liabilities, "Non-current lease liabilities treated as long-term debt proxy.")
            self._add_if_present(data, "total_debt", sum(debt_parts), "Derived from borrowings and lease liabilities.")
        if data.operating_cash_flow is not None and data.investing_cash_flow is not None:
            self._add_if_present(data, "free_cash_flow", data.operating_cash_flow + data.investing_cash_flow, "Derived from operating plus investing cash flow.")

        return data

    def extract_text_metrics(self, text: str, unit_multiplier: float = 1.0) -> ExtractedFinancialData:
        data = ExtractedFinancialData()
        lines = text.split("\n")
        for field_name, pattern in self.patterns.items():
            for index, line in enumerate(lines):
                if not pattern.search(line) or not self._is_generic_field_candidate(field_name, line):
                    continue
                value_found = False
                for offset in range(index, min(index + 3, len(lines))):
                    if not self._is_generic_field_candidate(field_name, lines[offset]):
                        continue
                    for num_str in re.findall(r"[\d,\.]+[MmBbKk]?", lines[offset]):
                        parsed = self._parse_number(num_str)
                        if parsed is not None:
                            setattr(data, field_name, parsed * unit_multiplier)
                            data.original_text_references[field_name] = lines[offset].strip()[:300]
                            value_found = True
                            break
                    if value_found:
                        break
                break
        return data

    def extract_table_metrics(self, tables: list, unit_multiplier: float = 1.0) -> ExtractedFinancialData:
        data = ExtractedFinancialData()
        for table in tables:
            df = pd.DataFrame(table)
            for _, row in df.iterrows():
                row_text = " ".join([str(cell).strip() for cell in row if cell])
                for field_name, pattern in self.patterns.items():
                    if not pattern.search(row_text) or not self._is_generic_field_candidate(field_name, row_text):
                        continue
                    parsed = self._first_statement_value(row_text, unit_multiplier)
                    if parsed is not None:
                        setattr(data, field_name, parsed)
                        data.original_text_references[field_name] = row_text[:300]
                        break
        return data

    def extract_fiscal_year(self, text: str) -> Optional[int]:
        patterns = [
            r"fiscal\s*year\s*ended?.*?(\d{4})",
            r"for\s*the\s*(?:year|period)\s*ended?.*?(\d{4})",
            r"year\s*ended?.*?(\d{4})",
            r"(\d{4})\s*annual\s*report",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1990 <= year <= 2030:
                    return year
        return None

    def extract_currency(self, text: str) -> Optional[str]:
        currency_patterns = {
            "INR": r"\bINR\b|\bRs\.?\b|Rupees|₹|\bD\s*million",
            "USD": r"\$|\bUSD\b|U\.S\. dollar",
            "EUR": r"€|\bEUR\b|Euro",
            "GBP": r"£|\bGBP\b|British pound",
            "JPY": r"¥|\bJPY\b|Japanese yen",
        }
        for currency, pattern in currency_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return currency
        return "USD"

    def parse_pdf(self, file_path: str) -> ExtractedFinancialData:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        data = ExtractedFinancialData()
        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                all_tables = []
                for page in pdf.pages:
                    full_text += _extract_page_text_with_ocr(page, data.extraction_warnings) + "\n"
                    all_tables.extend(page.extract_tables() or [])

            data.fiscal_year = self.extract_fiscal_year(full_text)
            data.currency = self.extract_currency(full_text)
            unit_multiplier = self.extract_unit_multiplier(full_text)
            statement_data = self.extract_statement_metrics(full_text, unit_multiplier)
            table_data = self.extract_table_metrics(all_tables, unit_multiplier)
            text_data = self.extract_text_metrics(full_text, unit_multiplier)

            skip_fields = {
                "CRITICAL_FIELDS",
                "missing_critical_fields",
                "original_text_references",
                "extraction_warnings",
                "extraction_confidence",
            }
            for field_name in data.__dataclass_fields__:
                if field_name in skip_fields:
                    continue
                for source in (statement_data, table_data, text_data):
                    value = getattr(source, field_name)
                    if value is not None:
                        setattr(data, field_name, value)
                        if field_name in source.original_text_references:
                            data.original_text_references[field_name] = source.original_text_references[field_name]
                        break

            if data.total_liabilities is None and data.total_assets is not None and data.shareholders_equity is not None:
                data.total_liabilities = data.total_assets - data.shareholders_equity
                data.original_text_references["total_liabilities"] = "Derived from total assets minus total equity."
            if data.total_debt is None:
                debt_parts = [data.short_term_debt, data.current_portion_long_term_debt, data.long_term_debt]
                if any(value is not None for value in debt_parts):
                    data.total_debt = sum(value or 0.0 for value in debt_parts)
                    data.original_text_references["total_debt"] = "Derived from extracted short-term, current portion, and long-term debt."
        except Exception as exc:
            data.extraction_warnings.append(f"Error parsing {file_path}: {exc}")

        data.finalize_quality_flags()
        return data


__all__ = ["PDFFinancialParser", "ExtractedFinancialData"]
