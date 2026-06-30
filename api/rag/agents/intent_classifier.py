def classify_query(query):

    query = query.lower()

    if "memo" in query:
        return "memo"

    if any(
        x in query
        for x in [
            "compare",
            "versus",
            " vs "
        ]
    ):
        return "compare"

    if any(
        x in query
        for x in [
            "committee",
            "approve",
            "approval",
            "reject",
            "credit decision",
            "extend credit"
        ]
    ):
        return "decision"

    if any(
        x in query
        for x in [
            "stress",
            "scenario",
            "fuel spike",
            "fuel crash",
            "fx crisis"
        ]
    ):
        return "stress"

    if any(
        x in query
        for x in [
            "portfolio",
            "var",
            "expected shortfall",
            "concentration"
        ]
    ):
        return "portfolio"

    return "counterparty"


