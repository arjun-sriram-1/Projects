# Data Rules

Prefer real/free/proxy data before synthetic data.

Accepted sources:

- Yahoo Finance / yfinance
- FRED
- EIA
- World Bank or IMF public data
- company annual reports
- public investor presentations
- exchange filings
- public airline/shipping operational data

Synthetic data:

- allowed for sample/demo or training fallback only
- must be clearly labeled
- must include `data_source`
- must document assumptions and label-generation logic

Storage:

- raw inputs: `data/raw/`
- uploaded documents: `data/uploads/`
- processed data: `data/processed/`
- saved model artifacts: `data/models/`
- vector indexes and metadata: `data/vector_store/`
- generated reports: `data/reports/`

