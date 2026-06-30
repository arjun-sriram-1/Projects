"""Approved plain-text policy document migration tests for V2 Phase 11D Option B."""

from pathlib import Path


POLICY_DIR = Path("data/rag_documents/policy")
APPROVED_POLICY_FILES = {
    "credit_tenor_policy.txt",
    "high_risk_policy.txt",
    "low_risk_policy.txt",
    "medium_risk_policy.txt",
    "security_policy.txt",
}


def test_approved_policy_text_documents_exist_only_as_plain_text():
    assert POLICY_DIR.exists()
    files = {path.name for path in POLICY_DIR.iterdir() if path.is_file()}

    assert files == APPROVED_POLICY_FILES
    assert all((POLICY_DIR / name).suffix == ".txt" for name in files)


def test_policy_documents_are_readable_and_nonempty():
    for filename in APPROVED_POLICY_FILES:
        text = (POLICY_DIR / filename).read_text(encoding="utf-8").strip()
        assert text
        assert "CREDIT_RISK_PROJECT_V1" not in text

    tenor_policy = (POLICY_DIR / "credit_tenor_policy.txt").read_text(encoding="utf-8")
    security_policy = (POLICY_DIR / "security_policy.txt").read_text(encoding="utf-8")

    assert "High Risk" in tenor_policy
    assert "Credit Committee" in tenor_policy
    assert "Letter of Credit" in security_policy
    assert "Bank Guarantee" in security_policy


def test_policy_doc_migration_did_not_copy_vector_artifacts():
    forbidden_suffixes = {".faiss", ".pkl"}
    copied_artifacts = [
        path for path in Path("data/rag_documents").rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]

    assert copied_artifacts == []
    assert not Path("data/rag_documents/data").exists()
