import pandas as pd
from sqlalchemy import text

from api.rag.llm.ollama_client import (
    generate_response
)
from api.rag.utils.company_extractor import (
    extract_two_companies
)

from api.db.session import engine


def compare_companies(company1, company2):

    query = text("""
    SELECT
        c.company_name,
        m.pd,
        m.lgd,
        m.expected_loss,
        m.risk_segment
    FROM counterparties_master c
    JOIN model_predictions m
    ON c.counterparty_id=m.counterparty_id
    WHERE company_name IN
    (:company1, :company2)
    """)

    df = pd.read_sql(
        query,
        engine,
        params={
            "company1": company1,
            "company2": company2
        }
    )

    prompt = f"""
Compare these counterparties.

{df.to_string()}

Compare:

1. Credit Quality

2. PD

3. LGD

4. Expected Loss

5. Recommendation
"""

    return generate_response(prompt)


