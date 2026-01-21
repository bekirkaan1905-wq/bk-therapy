from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import os
import textwrap


def euro(amount: float) -> str:
    """Format: 1.234,56 €"""
    s = f"{amount:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def _safe_float(x, default=0.0) -> float:
    """Zahlen robust lesen (auch '1,5')."""
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return float(default)


def _draw_table_header(c: canvas.Canvas, table_left: float, table_right: float, y: float) -> float:
    """Tabellenkopf + Linie zeichnen, neues y zurückgeben."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(table_left, y, table_right, y)

    y -= 7 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left, y, "Leistung")
    c.drawRightString(table_right - 60 * mm, y, "Menge")
    c.drawRightString(table_right - 30 * mm, y, "Einzelpreis")
    c.drawRightString(table_right, y, "Betrag")

    y -= 4 * mm
    c.setLineWidth(0.5)
    c.line(table_left, y, table_right, y)

    y -= 7 * mm
    c.setFont("Helvetica", 10)
    return y


def generate_invoice_pdf(
    output_pdf_path: str,
    logo_path: str | None,
    issuer: dict,
    client: dict,
    invoice: dict,
    items: list,
    payment: dict,
):
    """
    Erwartete Struktur (kurz):
      issuer: {"name":..., "address_lines":[...], "phone":..., "email":..., "tax_number":...}
      client: {"name":..., "address_lines":[...]}
      invoice: {"title":..., "number":..., "date":"TT.MM.JJJJ", "service_date":"TT.MM.JJJJ",
                "show_vat_note": True/False}
      items: [{"description":..., "qty":..., "unit_price":...}, ...]
      payment: {"due_days":14, "account_holder":..., "iban":..., "bic":...}
    """
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    table_left = margin_x
    table_right = width - margin_x
    right_x = width - margin_x

    # Logo größer als vorher
    LOGO_W = 55 * mm
    LOGO_H = 30 * mm

    # Start-Y
    y_top = height - 20 * mm

    # Logo oben links (optional)
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                margin_x,
                y_top - LOGO_H,          # oben links
                width=LOGO_W,
                height=LOGO_H,
                mask="auto",
                preserveAspectRatio=True,
                anchor="sw",
            )
        except Exception:
            pass

    # Aussteller (rechts oben)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right_x, y_top, issuer.get("name", ""))

    c.setFont("Helvetica", 10)
    yy = y_top - 5 * mm
    for line in issuer.get("address_lines", []) or []:
        c.drawRightString(right_x, yy, str(line))
        yy -= 4 * mm

    if issuer.get("phone"):
        c.drawRightString(right_x, yy, f"Tel: {issuer.get('phone')}")
        yy -= 4 * mm
    if issuer.get("email"):
        c.drawRightString(right_x, yy, str(issuer.get("email")))
        yy -= 4 * mm
    if issuer.get("tax_number"):
        c.drawRightString(right_x, yy, f"St-Nr.: {issuer.get('tax_number')}")
        yy -= 4 * mm

    # Genug Abstand nach dem Kopfbereich (wegen größerem Logo)
    y = y_top - 48 * mm

    # Titel + Rechnungsdaten
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, invoice.get("title", "Rechnung"))

    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Rechnungsnummer: {invoice.get('number','')}")
    y -= 5 * mm
    c.drawString(margin_x, y, f"Rechnungsdatum: {invoice.get('date','')}")
    y -= 5 * mm
    c.drawString(margin_x, y, f"Leistungsdatum: {invoice.get('service_date','')}")

    # Kunde
    y -= 15 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Rechnung an:")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, client.get("name", ""))
    y -= 4 * mm
    for line in client.get("address_lines", []) or []:
        c.drawString(margin_x, y, str(line))
        y -= 4 * mm

    # Tabelle
    y -= 10 * mm
    y = _draw_table_header(c, table_left, table_right, y)

    total = 0.0

    for it in items or []:
        qty = _safe_float(it.get("qty", 0))
        unit = _safe_float(it.get("unit_price", 0))
        line_total = qty * unit
        total += line_total

        desc = str(it.get("description", ""))
        wrapped = textwrap.wrap(desc, width=60) or [""]

        first_line = True
        for wline in wrapped:
            # Seitenumbruch + Tabellenkopf neu
            if y < 55 * mm:
                c.showPage()
                y = height - 20 * mm
                y = _draw_table_header(c, table_left, table_right, y)

            c.drawString(table_left, y, wline)

            if first_line:
                # Menge hübscher: 1 statt 1.0
                if qty % 1 == 0:
                    qty_str = str(int(qty))
                else:
                    qty_str = str(qty).rstrip("0").rstrip(".")
                c.drawRightString(table_right - 60 * mm, y, qty_str)
                c.drawRightString(table_right - 30 * mm, y, euro(unit))
                c.drawRightString(table_right, y, euro(line_total))
                first_line = False

            y -= 6 * mm

    # Gesamt (kommt VOR dem Hinweis)
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(table_right - 30 * mm, y, "Gesamt:")
    c.drawRightString(table_right, y, euro(total))

    # Hinweis (nicht "steuerfrei", sondern: keine USt ausgewiesen)
    show_vat_note = invoice.get("show_vat_note", True)
    if show_vat_note:
        y -= 12 * mm
        c.setFont("Helvetica", 9)
        c.drawString(
            table_left,
            y,
            "Hinweis: Gemäß § 19 UStG (Kleinunternehmerregelung) wird keine Umsatzsteuer ausgewiesen.",
        )
        y -= 5 * mm

    # Fälligkeitsdatum robust berechnen
    try:
        invoice_date = datetime.strptime(invoice.get("date", ""), "%d.%m.%Y")
    except ValueError:
        invoice_date = datetime.today()

    due_days = int(_safe_float(payment.get("due_days", 14), default=14))
    due_date = invoice_date + timedelta(days=due_days)

    # Zahlungsinfos
    c.setFont("Helvetica", 9)
    c.drawString(table_left, y, f"Zahlungsziel: {due_days} Tage")
    y -= 5 * mm
    c.drawString(table_left, y, f"Fällig am: {due_date.strftime('%d.%m.%Y')}")
    y -= 6 * mm

    c.drawString(table_left, y, f"Kontoinhaber: {payment.get('account_holder','')}")
    y -= 5 * mm
    c.drawString(table_left, y, f"IBAN: {payment.get('iban','')}")
    if payment.get("bic"):
        y -= 5 * mm
        c.drawString(table_left, y, f"BIC: {payment.get('bic','')}")

    c.save()
