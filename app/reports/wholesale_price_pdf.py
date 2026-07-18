from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reports.receipt_pdf import GOLD, GREEN, INK, LINE, MUTED, SOFT, _register_fonts
from app.services.product_service import ProductSummary
from app.utils.money import format_money

LOGO = Path(__file__).resolve().parents[2] / "assets" / "logo" / "distribuidora_damian.png"


def build_wholesale_price_pdf(products: list[ProductSummary], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "Lista_Precios_Mayorista.pdf"
    regular_font, bold_font = _register_fonts()
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "Supplier",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=13,
        leading=16,
        textColor=GREEN,
        spaceBefore=8,
        spaceAfter=5,
    )
    cell = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontName=regular_font, fontSize=8.5, leading=11
    )
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=16 * mm,
        title="Lista de precios mayorista",
        author="Distribuidora Damián",
    )
    logo = Image(str(LOGO), width=42 * mm, height=32 * mm, kind="proportional")
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=18,
        leading=22,
        textColor=INK,
        alignment=2,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=9,
        leading=13,
        textColor=MUTED,
        alignment=2,
    )
    header = Table(
        [
            [
                logo,
                Paragraph(
                    "LISTA DE PRECIOS MAYORISTA"
                    f"<br/><font size='9' color='#68736C'>{datetime.now():%d/%m/%Y}</font>",
                    title_style,
                ),
            ]
        ],
        colWidths=[70 * mm, 112 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 2, GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story: list[object] = [
        header,
        Spacer(1, 5),
        Paragraph("Precios expresados en pesos uruguayos, por unidad.", meta_style),
        Spacer(1, 8),
    ]
    grouped: dict[str, list[ProductSummary]] = defaultdict(list)
    for product in products:
        grouped[product.supplier].append(product)
    for supplier in sorted(grouped):
        story.append(Paragraph(escape(supplier), heading))
        rows: list[list[object]] = [["Código", "Producto", "Presentación", "Precio"]]
        for product in grouped[supplier]:
            rows.append(
                [
                    product.code,
                    Paragraph(escape(product.name), cell),
                    Paragraph(escape(product.presentation), cell),
                    format_money(product.wholesale_price),
                ]
            )
        table = Table(rows, colWidths=[22 * mm, 88 * mm, 42 * mm, 30 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), bold_font),
                    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                    ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([table, Spacer(1, 5)])

    def page_footer(canvas, document_template):  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 9 * mm, "Distribuidora Damián")
        canvas.drawRightString(196 * mm, 9 * mm, f"Página {document_template.page}")
        canvas.setStrokeColor(GOLD)
        canvas.line(14 * mm, 12 * mm, 196 * mm, 12 * mm)
        canvas.restoreState()

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return path
