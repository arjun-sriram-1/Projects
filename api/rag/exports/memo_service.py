"""Credit memo export service.

This service exports memo text generated from stored V2 credit-decision outputs.
It does not calculate credit decisions and does not require permanent file writes;
callers may pass an explicit output directory or filenames.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from api.core.config import settings
from api.rag.exports.docx_exporter import export_docx
from api.rag.exports.memo_generator import build_credit_memo
from api.rag.exports.pdf_exporter import export_pdf


def _safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
    return cleaned.lower() or "credit_memo"


def _output_paths(
    label: str,
    output_dir: Optional[str | Path] = None,
    docx_filename: Optional[str | Path] = None,
    pdf_filename: Optional[str | Path] = None,
) -> tuple[Path, Path]:
    base_dir = Path(output_dir) if output_dir is not None else settings.report_dir
    base_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(label)

    docx_path = Path(docx_filename) if docx_filename is not None else base_dir / f"{stem}.docx"
    pdf_path = Path(pdf_filename) if pdf_filename is not None else base_dir / f"{stem}.pdf"
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    return docx_path, pdf_path


def generate_memo_files(
    question: str,
    output_dir: Optional[str | Path] = None,
    docx_filename: Optional[str | Path] = None,
    pdf_filename: Optional[str | Path] = None,
):
    """Generate memo text and export DOCX/PDF files.

    The memo text comes from the grounded V2 memo builder. Tests and callers can
    pass temp paths to avoid permanent generated report files.
    """
    memo = build_credit_memo(question)
    docx_path, pdf_path = _output_paths(
        question,
        output_dir=output_dir,
        docx_filename=docx_filename,
        pdf_filename=pdf_filename,
    )

    docx_file = export_docx(memo, filename=docx_path)
    pdf_file = export_pdf(memo, filename=pdf_path)

    return {
        "memo": memo,
        "docx": docx_file,
        "pdf": pdf_file,
        "source": "stored V2 credit memo service",
    }
