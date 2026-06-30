from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from api.core.config import settings


def _resolve_output_path(filename):
    output_path = Path(filename) if filename is not None else settings.report_dir / "credit_memo.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def export_pdf(memo_text, filename=None, title="Credit Committee Memo"):
    output_path = _resolve_output_path(filename)
    doc = SimpleDocTemplate(str(output_path))
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
        Paragraph(memo_text.replace("\n", "<br/>"), styles["BodyText"]),
    ]
    doc.build(story)
    return str(output_path)
