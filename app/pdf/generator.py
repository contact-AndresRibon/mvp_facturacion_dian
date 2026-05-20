from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.enums import DocumentStatus


class PDFGenerator:
    @staticmethod
    def _format_money(value: Decimal | str) -> str:
        return f"${Decimal(str(value)):,.2f}"

    @staticmethod
    def generate_document_pdf(
        *,
        doc_type_label: str,
        document_number: str,
        status: DocumentStatus,
        issue_date: str,
        tenant_name: str,
        tenant_nit: str,
        customer_name: str,
        customer_doc: str,
        lines: list[dict[str, Any]],
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
        notes: str | None = None,
        reference: str | None = None,
    ) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"<b>{tenant_name}</b>", styles["Title"]))
        story.append(Paragraph(f"NIT: {tenant_nit}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>{doc_type_label}</b> No. {document_number}", styles["Heading2"]))
        story.append(Paragraph(f"Fecha: {issue_date} | Estado: {status.value}", styles["Normal"]))

        if reference:
            story.append(Paragraph(f"Referencia: {reference}", styles["Normal"]))

        if status == DocumentStatus.DRAFT:
            story.append(
                Paragraph(
                    "<font color='red'><b>Documento borrador - No valido ante DIAN (MVP)</b></font>",
                    styles["Normal"],
                )
            )

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("<b>Cliente</b>", styles["Heading3"]))
        story.append(Paragraph(f"{customer_name} ({customer_doc})", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        table_data = [["Descripcion", "Cant.", "Precio", "IVA%", "Total"]]
        for line in lines:
            table_data.append(
                [
                    str(line["description"])[:40],
                    str(line["quantity"]),
                    PDFGenerator._format_money(line["unit_price"]),
                    f"{line['tax_rate']}%",
                    PDFGenerator._format_money(line["line_total"]),
                ]
            )

        table = Table(table_data, colWidths=[2.5 * inch, 0.6 * inch, 1 * inch, 0.6 * inch, 1 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Subtotal: {PDFGenerator._format_money(subtotal)}", styles["Normal"]))
        story.append(Paragraph(f"IVA: {PDFGenerator._format_money(tax_total)}", styles["Normal"]))
        story.append(Paragraph(f"<b>Total: {PDFGenerator._format_money(total)}</b>", styles["Normal"]))

        if notes:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(f"Notas: {notes}", styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()
