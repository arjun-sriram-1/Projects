"""Application configuration for V2.

Business purpose:
Centralize environment variables and project paths so migrated modules do not
hardcode old V1 locations such as `models/ml/*.pkl` or `rag/data/*.faiss`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


def _database_url() -> str:
    """Return a SQLAlchemy database URL, rebuilding it from components when safer."""
    raw_url = os.getenv("DB_URL", "")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")
    port = os.getenv("POSTGRES_PORT", "5432")
    host = os.getenv("POSTGRES_HOST", "localhost")

    if user and password and database:
        if raw_url:
            try:
                parsed = make_url(raw_url)
                if parsed.password == password:
                    return raw_url
            except Exception:
                pass
        return (
            URL.create(
                "postgresql+psycopg2",
                username=user,
                password=password,
                host=host,
                port=int(port),
                database=database,
            )
            .render_as_string(hide_password=False)
        )
    return raw_url


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from `.env` with V2-safe default paths."""

    app_env: str = os.getenv("APP_ENV", "development")
    app_debug: bool = os.getenv("APP_DEBUG", "False").lower() in {"1", "true", "yes"}
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "")

    database_url: str = _database_url()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    data_dir: Path = PROJECT_ROOT / "data"
    raw_data_dir: Path = data_dir / "raw"
    upload_dir: Path = data_dir / "uploads"
    processed_data_dir: Path = data_dir / "processed"
    model_artifact_dir: Path = data_dir / "models"
    vector_store_dir: Path = data_dir / "vector_store"
    report_dir: Path = data_dir / "reports"

    embeddings_model_name: str = os.getenv(
        "EMBEDDINGS_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )
    vector_store_path: Path = Path(
        os.getenv("VECTOR_STORE_PATH", str(vector_store_dir / "faiss_index"))
    )
    faiss_index_path: Path = Path(
        os.getenv("FAISS_INDEX_PATH", str(vector_store_dir / "faiss.index"))
    )
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    copilot_use_llm: bool = os.getenv("COPILOT_USE_LLM", "False").lower() in {
        "1",
        "true",
        "yes",
    }

    eia_api_key: str = os.getenv("EIA_API_KEY", "")
    fred_api_key: str = os.getenv("FRED_API_KEY", "")
    alphavantage_api_key: str = os.getenv("ALPHAVANTAGE_API_KEY", "")

    def require_database_url(self) -> str:
        """Return DB URL or raise a clear setup error."""
        if not self.database_url:
            raise RuntimeError("DB_URL is not set. Add it to V2 .env before DB use.")
        return self.database_url


settings = Settings()


__all__ = ["PROJECT_ROOT", "ENV_PATH", "Settings", "settings"]
