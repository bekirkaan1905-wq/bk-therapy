from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import os, textwrap

def euro(amount: float) -> str:
    s = f"{amount:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"

def generate_invoice_pdf(output_pdf_path: str, logo_path: str, issuer: dict, client: dict,
                         invoice: dict, items: list, payment: dict):
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4
    margin_x = 20 * mm
    y = height - 20 * mm

    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, margin_x, y - 24*mm, width=40*mm, height=24*mm,
                        mask='auto', preserveAspectRatio=True, anchor='sw')
        except Exception:
            pass

    right_x = width - margin_x
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right_x, y, issuer["name"])

    c.setFont("Helvetica", 10)
    yy = y - 5*mm
    for line in issuer.get("address_lines", []):
        c.drawRightString(right_x, yy, line)
        yy -= 4*mm

    if issuer.get("phone"):
        c.drawRightString(right_x, yy, f"Tel: {issuer['phone']}")
        yy -= 4*mm
    if issuer.get("email"):
        c.drawRightString(right_x, yy, issuer["email"])
        yy -= 4*mm
    if issuer.get("tax_number"):
        c.drawRightString(right_x, yy, f"St-Nr.: {issuer['tax_number']}")
        yy -= 4*mm

    y -= 38*mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, invoice.get("title", "Rechnung"))

    y -= 10*mm
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Rechnungsnummer: {invoice.get('number','')}")
    y -= 5*mm
    c.drawString(margin_x, y, f"Rechnungsdatum: {invoice.get('date','')}")
    y -= 5*mm
    c.drawString(margin_x, y, f"Leistungsdatum: {invoice.get('service_date','')}")

    y -= 15*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Rechnung an:")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, client.get("name",""))
    y -= 4*mm
    for line in client.get("address_lines", []):
        c.drawString(margin_x, y, line)
        y -= 4*mm

    y -= 10*mm
    table_left = margin_x
    table_right = width - margin_x

    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(table_left, y, table_right, y)

    y -= 7*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left, y, "Leistung")
    c.drawRightString(table_right - 60*mm, y, "Menge")
    c.drawRightString(table_right - 30*mm, y, "Einzelpreis")
    c.drawRightString(table_right, y, "Betrag")

    y -= 4*mm
    c.setLineWidth(0.5)
    c.line(table_left, y, table_right, y)

    c.setFont("Helvetica", 10)
    y -= 7*mm
    total = 0.0

    for it in items:
        qty = float(it["qty"])
        unit = float(it["unit_price"])
        line_total = qty * unit
        total += line_total

        desc = str(it["description"])
        wrapped = textwrap.wrap(desc, width=60) or [""]

        first = True
        for wline in wrapped:
            if y < 55*mm:
                c.showPage()
                y = height - 20*mm
            c.drawString(table_left, y, wline)
            if first:
                c.drawRightString(table_right - 60*mm, y, str(qty))
                c.drawRightString(table_right - 30*mm, y, euro(unit))
                c.drawRightString(table_right, y, euro(line_total))
                first = False
            y -= 6*mm

    y -= 10*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(table_right - 30*mm, y, "Gesamt:")
    c.drawRightString(table_right, y, euro(total))

    y -= 12*mm
    c.setFont("Helvetica", 9)
    c.drawString(table_left, y,
        "Hinweis: Gemäß § 19 UStG (Kleinunternehmerregelung) wird keine Umsatzsteuer berechnet."
    )

    y -= 12*mm
    c.setFont("Helvetica", 10)
    due_days = payment.get("due_days", 7)
    c.drawString(table_left, y, f"Zahlungsziel: {due_days} Tage")
    y -= 6*mm
    c.drawString(table_left, y, f"Kontoinhaber: {payment.get('account_holder','')}")
    y -= 5*mm
    c.drawString(table_left, y, f"IBAN: {payment.get('iban','')}")
    if payment.get("bic"):
        y -= 5*mm
        c.drawString(table_left, y, f"BIC: {payment.get('bic','')}")

    c.save()