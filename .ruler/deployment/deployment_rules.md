# Deployment Rules

Default deployment is local-first and student-project realistic.

Approved baseline:

- PostgreSQL via `docker-compose.yml`
- FastAPI backend
- Streamlit frontend
- `.env.example` as template

Rules:

- Do not commit `.env`.
- Do not require paid services by default.
- Keep local setup reproducible.
- Document any required external keys: EIA, FRED, Alpha Vantage, Ollama.
- Prefer simple Docker/local commands over complex infrastructure.

