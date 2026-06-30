from api.core.config import settings

from api.reporting.report_generator import (
    generate_report_data
)

from api.reporting.report_pdf import (
    create_risk_report_pdf
)


def run_report():

    report = generate_report_data()

    create_risk_report_pdf(

        report,

        str(settings.report_dir / "daily_risk_report.pdf")
    )

    print(
        "Report Generated"
    )


if __name__ == "__main__":

    run_report()
