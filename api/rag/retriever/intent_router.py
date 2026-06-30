def detect_intent(question):

    question = question.lower()

    if any(word in question for word in [

        "high risk",
        "counterparty",
        "risk segment",
        "compare",
        "anomaly"

    ]):

        return "counterparty"

    if any(word in question for word in [

        "fuel crisis",
        "fx crisis",
        "stress",
        "scenario"

    ]):

        return "stress"

    if any(word in question for word in [

        "var",
        "expected shortfall",
        "portfolio loss",
        "monte carlo"

    ]):

        return "montecarlo"

    if any(word in question for word in [

        "credit policy",
        "tenor",
        "letter of credit",
        "security",
        "collateral"

    ]):

        return "policy"

    if any(word in question for word in [

        "extend credit",
        "approve",
        "credit decision"

    ]):

        return "credit_decision"

    return "general"

