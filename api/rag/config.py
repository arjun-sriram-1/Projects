import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


load_dotenv()

DB_URL = os.getenv("DB_URL")

if not DB_URL:
    raise RuntimeError(
        "DB_URL is not set. Add it to .env before using RAG ingestion."
    )

url = make_url(DB_URL)

DB_CONFIG = {
    "host": url.host,
    "port": url.port or 5432,
    "database": url.database,
    "user": url.username,
    "password": url.password
}


