import pandas as pd

from api.db.session import engine


def get_all_companies():

    query = """
    SELECT company_name
    FROM counterparties_master
    """

    df = pd.read_sql(query, engine)

    return df["company_name"].dropna().tolist()


def extract_company(question):

    companies = get_all_companies()

    q = question.lower()

    for company in companies:

        if company.lower() in q:
            return company

    return None


import re

def extract_two_companies(question):

    companies = get_all_companies()

    q = question.lower()

    matches = []

    for company in companies:

        pattern = re.escape(company.lower())

        if re.search(pattern, q):
            matches.append(company)

    matches = list(dict.fromkeys(matches))

    if len(matches) >= 2:
        return matches[:2]

    return None


