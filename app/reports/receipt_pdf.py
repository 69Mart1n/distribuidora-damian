from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.database.models import Receipt, Settings
from app.utils.money import format_money

GREEN = colors.HexColor("#34533C")
OLIVE = colors.HexColor("#9AA56A")
GOLD = colors.HexColor("#C2A963")
INK = colors.HexColor("#1B241F")
MUTED = colors.HexColor("#68736C")
LINE = colors.HexColor("#D8DFDA")
SOFT = colors.HexColor("#F4F6F4")
ASSETS = Path(__file__).resolve().parents[2] / "assets" / "logo"

PAYMENT_LABELS = {"paid": "PAGADA", "partial": "PAGO PARCIAL", "pending": "PENDIENTE"}
METHOD_LABELS = {
    "cash": "Efectivo",
    "transfer": "Transferencia",
    "account": "Cuenta",
    "mixed": "Mixto",
}


def _register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\segoeui.ttf")
    bold = Path(r"C:\Windows\Fonts\segoeuib.ttf")
    if regular.exists() and bold.exists():
        if "SegoeUI" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("SegoeUI", regular))
            pdfmetrics.registerFont(TTFont("SegoeUI-Bold", bold))
        return "SegoeUI", "SegoeUI-Bold"
    return "Helvetica", "Helvetica-Bold"


def build_receipt_pdf(receipt: Receipt, output_dir: Path, settings: Settings) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{receipt.receipt_code}.pdf"
    regular_font, bold_font = _register_fonts()
    styles = getSampleStyleSheet()
    business_style = ParagraphStyle(
        "Business",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=17,
        leading=21,
        textColor=INK,
        alignment=TA_LEFT,
    )
    document_style = ParagraphStyle(
        "Document",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=17,
        leading=22,
        textColor=GREEN,
        alignment=TA_RIGHT,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=9,
        leading=13,
        textColor=INK,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8.5,
        leading=11,
        textColor=INK,
    )
    total_style = ParagraphStyle(
        "Total",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=17,
        leading=20,
        textColor=INK,
        alignment=TA_RIGHT,
    )
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=receipt.receipt_code,
        author=settings.business_name,
    )

    configured_logo = Path(settings.business_logo_path) if settings.business_logo_path else None
    logo_path = (
        configured_logo
        if configured_logo and configured_logo.exists()
        else (ASSETS / "distribuidora_damian.png")
    )
    logo: object
    if logo_path.exists():
        logo = Image(str(logo_path), width=50 * mm, height=38 * mm, kind="proportional")
    else:
        logo = Paragraph(escape(settings.business_name), business_style)
    document_status = (
        "CANCELADA"
        if receipt.status == "cancelled"
        else PAYMENT_LABELS.get(receipt.payment_status, receipt.payment_status.upper())
    )
    header = Table(
        [[logo, Paragraph(f"BOLETA<br/>{escape(receipt.receipt_code)}", document_style)]],
        colWidths=[116 * mm, 46 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 2, GREEN),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    contact_parts = [
        value
        for value in [settings.business_address, settings.business_phone, settings.business_email]
        if value
    ]
    contact = " · ".join(escape(value) for value in contact_parts)
    contact_style = ParagraphStyle(
        "Contact",
        parent=meta_style,
        textColor=MUTED,
        fontSize=8.5,
        alignment=TA_LEFT,
    )
    customer_detail = escape(receipt.customer_name_snapshot)
    if receipt.customer_phone_snapshot:
        customer_detail += f"<br/>{escape(receipt.customer_phone_snapshot)}"
    if receipt.customer_address_snapshot:
        customer_detail += f"<br/>{escape(receipt.customer_address_snapshot)}"
    info = Table(
        [
            [
                Paragraph(f"<b>Cliente</b><br/>{customer_detail}", meta_style),
                Paragraph(
                    f"<b>Fecha</b><br/>{receipt.issued_at.strftime('%d/%m/%Y · %H:%M')}",
                    meta_style,
                ),
                Paragraph(
                    f"<b>Estado</b><br/><font color='#34533C'><b>{document_status}</b></font>",
                    meta_style,
                ),
            ]
        ],
        colWidths=[82 * mm, 43 * mm, 37 * mm],
    )
    info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    rows: list[list[object]] = [["Producto", "Presentación", "Cantidad", "Precio", "Subtotal"]]
    for item in receipt.items:
        rows.append(
            [
                Paragraph(escape(item.product_name_snapshot), cell_style),
                Paragraph(escape(item.presentation_snapshot or ""), cell_style),
                str(int(item.quantity)),
                format_money(item.unit_price),
                format_money(item.line_total),
            ]
        )
    detail = Table(rows, colWidths=[68 * mm, 36 * mm, 18 * mm, 20 * mm, 20 * mm], repeatRows=1)
    detail.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    payment_text = (
        f"<b>Medio de pago:</b> {METHOD_LABELS.get(receipt.payment_method, receipt.payment_method)}"
        f"<br/><b>Abonado:</b> {format_money(receipt.amount_paid)}"
        f"<br/><b>Saldo:</b> {format_money(receipt.pending_amount)}"
    )
    total_box = Table(
        [
            [
                Paragraph(payment_text, meta_style),
                Paragraph("TOTAL", meta_style),
                Paragraph(format_money(receipt.total), total_style),
            ]
        ],
        colWidths=[90 * mm, 27 * mm, 45 * mm],
    )
    total_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
                ("ALIGN", (1, 0), (-1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    footer_style = ParagraphStyle(
        "Footer", parent=meta_style, fontSize=8.5, textColor=MUTED, alignment=TA_LEFT
    )
    story: list[object] = [header]
    if contact:
        story.extend([Spacer(1, 4), Paragraph(contact, contact_style)])
    story.extend(
        [Spacer(1, 10), info, Spacer(1, 14), detail, Spacer(1, 12), KeepTogether(total_box)]
    )
    if receipt.notes:
        story.extend(
            [
                Spacer(1, 12),
                Paragraph(f"<b>Observaciones</b><br/>{escape(receipt.notes)}", meta_style),
            ]
        )
    if receipt.status == "cancelled" and receipt.cancellation_reason:
        story.extend(
            [
                Spacer(1, 10),
                Paragraph(
                    f"<b>Boleta cancelada:</b> {escape(receipt.cancellation_reason)}", meta_style
                ),
            ]
        )
    story.extend([Spacer(1, 18), Paragraph("Gracias por su compra.", footer_style)])

    def page_footer(canvas, document_template):  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 9 * mm, settings.business_name)
        canvas.drawRightString(194 * mm, 9 * mm, f"Página {document_template.page}")
        canvas.setStrokeColor(GOLD)
        canvas.line(16 * mm, 12 * mm, 194 * mm, 12 * mm)
        canvas.restoreState()

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return path
