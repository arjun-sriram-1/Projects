"""Memo export service integration tests for V2 Phase 12B."""

from pathlib import Path

from api.rag.exports import memo_service


def test_generate_memo_files_uses_grounded_builder_and_tmp_output_dir(tmp_path, monkeypatch):
    calls = []

    def fake_build_credit_memo(question):
        calls.append(question)
        return "Grounded memo from stored SQL/model outputs only."

    monkeypatch.setattr(memo_service, "build_credit_memo", fake_build_credit_memo)

    result = memo_service.generate_memo_files("Acme Fuel", output_dir=tmp_path)

    assert calls == ["Acme Fuel"]
    assert result["memo"] == "Grounded memo from stored SQL/model outputs only."
    assert result["source"] == "stored V2 credit memo service"
    assert Path(result["docx"]).exists()
    assert Path(result["pdf"]).exists()
    assert Path(result["docx"]).parent == tmp_path
    assert Path(result["pdf"]).parent == tmp_path
    assert Path(result["docx"]).name == "acme_fuel.docx"
    assert Path(result["pdf"]).name == "acme_fuel.pdf"


def test_generate_memo_files_accepts_explicit_filenames(tmp_path, monkeypatch):
    monkeypatch.setattr(memo_service, "build_credit_memo", lambda question: "Stored memo text")

    docx_path = tmp_path / "custom" / "memo-output.docx"
    pdf_path = tmp_path / "custom" / "memo-output.pdf"

    result = memo_service.generate_memo_files(
        "Question with / unsafe characters?",
        docx_filename=docx_path,
        pdf_filename=pdf_path,
    )

    assert result["docx"] == str(docx_path)
    assert result["pdf"] == str(pdf_path)
    assert docx_path.exists()
    assert pdf_path.exists()


def test_safe_stem_prevents_path_injection():
    assert memo_service._safe_stem("../Acme Fuel?") == "acme_fuel"
    assert memo_service._safe_stem("   ") == "credit_memo"


def test_memo_service_does_not_write_default_reports_during_tests(tmp_path, monkeypatch):
    monkeypatch.setattr(memo_service, "build_credit_memo", lambda question: "Stored memo text")

    result = memo_service.generate_memo_files("Temp Only", output_dir=tmp_path)

    assert Path(result["docx"]).parent == tmp_path
    assert Path(result["pdf"]).parent == tmp_path
    assert not Path("credit_memo.pdf").exists()
    assert not Path("credit_memo.docx").exists()
