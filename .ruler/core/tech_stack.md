# Tech Stack

Derived from V1 `requirements.txt`, `.env.example`, and `docker-compose.yml`.

Backend:

- FastAPI, Uvicorn, Pydantic
- SQLAlchemy, psycopg2-binary, PostgreSQL
- python-dotenv for environment loading

Quant/data:

- pandas, numpy, scipy
- scikit-learn, xgboost, joblib
- yfinance for market data
- pdfplumber, pytesseract, Pillow for document extraction

RAG/AI:

- faiss-cpu
- sentence-transformers
- langchain, langchain-community, langchain-ollama
- Ollama URL and model settings from env

Frontend/reporting:

- Streamlit, streamlit-option-menu, Plotly
- reportlab, python-docx

Testing:

- pytest

Dependency rule:

- Prefer existing dependencies before adding new ones.
- Do not add obscure packages for simple tasks.
- New dependencies require a short documented reason.

