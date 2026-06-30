from pathlib import Path

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)


def create_risk_report_pdf(
    report_data,
    output_file
):

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path)
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "Fuel Trade Credit Risk Report",
            styles["Title"]
        )
    )

    story.append(
        Spacer(1,12)
    )

    story.append(

        Paragraph(

            f"Total Exposure: "
            f"${report_data['total_exposure']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"Expected Loss: "
            f"${report_data['total_expected_loss']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"Average PD: "
            f"{report_data['avg_pd']*100:.2f}%",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"Average LGD: "
            f"{report_data['avg_lgd']*100:.2f}%",

            styles["BodyText"]
        )
    )

    story.append(
        Spacer(1,20)
    )

    story.append(
        Paragraph(
            "Portfolio Risk Metrics",
            styles["Heading2"]
        )
    )

    story.append(

        Paragraph(

            f"VaR 95: "
            f"${report_data['var95']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"VaR 99: "
            f"${report_data['var99']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"Expected Shortfall 95: "
            f"${report_data['es95']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(

        Paragraph(

            f"Expected Shortfall 99: "
            f"${report_data['es99']:,.0f}",

            styles["BodyText"]
        )
    )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Top Risk Contributors",
            styles["Heading2"]
        )
    )

    for _, row in report_data[
        "top_risk"
    ].iterrows():

        story.append(

            Paragraph(

                f"{row['company_name']} | "
                f"Expected Loss: "
                f"${row['expected_loss']:,.0f}",

                styles["BodyText"]
            )
        )

    doc.build(story)


