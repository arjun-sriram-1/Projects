import json


def create_metadata(**kwargs):
    return kwargs


def format_currency(value):

    if value is None:
        return "N/A"

    try:
        return f"${float(value):,.2f}"

    except:
        return "N/A"


def format_percentage(value):

    if value is None:
        return "N/A"

    try:
        return f"{float(value) * 100:.2f}%"

    except:
        return "N/A"

import ast


def format_anomaly(value):

    try:

        if isinstance(value, dict):

            anomaly = value

        else:

            anomaly = ast.literal_eval(
                str(value)
            )

        return f"""
Status: {anomaly.get('status')}

Flag: {anomaly.get('flag')}

Score: {round(anomaly.get('score'),4)}
"""

    except:

        return str(value)

