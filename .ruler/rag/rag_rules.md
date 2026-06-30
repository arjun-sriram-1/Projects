# RAG Rules

The AI layer may:

- explain risk outputs
- retrieve stored data
- summarize uploaded documents
- generate grounded credit memos
- answer Q&A using retrieved context

The AI layer must not:

- invent financial numbers
- create final credit limits
- override stored model outputs
- hide missing data

Numerical claims must come from:

- SQL database
- model output
- uploaded financial document
- market data table
- scenario result table
- credit recommendation table

If required data is unavailable, say the data is missing.

