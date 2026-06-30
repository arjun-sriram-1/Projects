from api.rag.exports.pdf_exporter import (
    export_pdf
)


def create_credit_memo_pdf(
    memo_text,
    output_file
):

    return export_pdf(
        memo_text,
        filename=output_file,
        title="Credit Committee Memo"
    )


