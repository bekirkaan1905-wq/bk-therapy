from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import os
import textwrap


def euro(amount: float) -> str:
    s = f"{amount:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def _safe_float(x, default=0.0) -> float:
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return float(default)


def _draw_table_header(c: canvas.Canvas, table_left: float, table_right: float, y: float) -> float:
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


def _draw_vertical_lines(c: canvas.Canvas, x_positions: list[float], y_top: float, y_bottom: float):
    """Senkrechte Linien zwischen Spalten (nur auf aktueller Seite)."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    for x in x_positions:
        c.line(x, y_top, x, y_bottom)


def generate_invoice_pdf(
    output_pdf_path: str,
    logo_path: str | None,
    issuer: dict,
    client: dict,
    invoice: dict,
    items: list,
    payment: dict,
):
    # ========= EINSTELLUNGEN =========
    LOGO_W = 80 * mm
    LOGO_H = 50 * mm

    GAP_AFTER_TOTAL = 12 * mm
    GAP_AFTER_NOTE = 15 * mm
    LINE_GAP_PAYMENT = 6 * mm  # <- wenn näher: 5*mm

    FIXED_DUE_DAYS = 14
    # ================================

    # Datum automatisch: heute
    today = datetime.today().strftime("%d.%m.%Y")
    invoice["date"] = today
    invoice["service_date"] = today

    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    table_left = margin_x
    table_right = width - margin_x
    right_x = width - margin_x

    # Spalten (Trennlinien) – genau passend zu deinen Spalten
    x_qty_col = table_right - 70 * mm   # Linie zwischen Leistung und Menge
    x_unit_col = table_right - 40 * mm  # Linie zwischen Menge und Einzelpreis
    x_amt_col = table_right - 15 * mm   # Linie zwischen Einzelpreis und Betrag

    y_top = height - 20 * mm

    # Logo
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                margin_x,
                y_top - LOGO_H,
                width=LOGO_W,
                height=LOGO_H,
                mask="auto",
                preserveAspectRatio=True,
                anchor="sw",
            )
        except Exception:
            pass

    # Aussteller rechts
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

    # Abstand nach Kopf (wegen Logo)
    y = y_top - (LOGO_H + 15 * mm)

    # Titel
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, invoice.get("title", "Rechnung"))

    # Rechnungsdaten
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

    # Tabelle starten
    y -= 10 * mm
    table_top_line_y = y  # obere Linie der Tabelle auf dieser Seite
    y = _draw_table_header(c, table_left, table_right, y)

    total = 0.0

    # Für Linien: wir merken uns, wie weit wir nach unten gekommen sind (auf dieser Seite)
    page_table_bottom_y = y

    for it in items or []:
        qty = _safe_float(it.get("qty", 0))
        unit = _safe_float(it.get("unit_price", 0))
        line_total = qty * unit
        total += line_total

        desc = str(it.get("description", ""))
        wrapped = textwrap.wrap(desc, width=60) or [""]

        first_line = True
        for wline in wrapped:
            # Seitenumbruch
            if y < 55 * mm:
                # Vor dem Seitenwechsel: vertikale Linien für die aktuelle Seite zeichnen
                _draw_vertical_lines(
                    c,
                    x_positions=[x_qty_col, x_unit_col, x_amt_col],
                    y_top=table_top_line_y,
                    y_bottom=page_table_bottom_y,
                )

                c.showPage()

                # neue Seite: Tabelle neu starten
                y_top = height - 20 * mm
                y = y_top
                table_top_line_y = y
                y = _draw_table_header(c, table_left, table_right, y)
                page_table_bottom_y = y

            # Leistung
            c.drawString(table_left, y, wline)

            if first_line:
                qty_str = str(int(qty)) if qty % 1 == 0 else str(qty).rstrip("0").rstrip(".")
                # WICHTIG: Reihenfolge korrekt: Menge, Einzelpreis, Betrag
                c.drawRightString(table_right - 60 * mm, y, qty_str)
                c.drawRightString(table_right - 30 * mm, y, euro(unit))
                c.drawRightString(table_right, y, euro(line_total))
                first_line = False

            y -= 6 * mm
            page_table_bottom_y = y  # immer aktualisieren

    # Nach der letzten Zeile: vertikale Linien für die letzte Seite zeichnen
    _draw_vertical_lines(
        c,
        x_positions=[x_qty_col, x_unit_col, x_amt_col],
        y_top=table_top_line_y,
        y_bottom=page_table_bottom_y,
    )

    # Gesamt
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(table_right - 30 * mm, y, "Gesamt:")
    c.drawRightString(table_right, y, euro(total))

    y -= GAP_AFTER_TOTAL

    # Hinweis
    show_vat_note = invoice.get("show_vat_note", True)
    if show_vat_note:
        c.setFont("Helvetica", 9)
        c.drawString(
            table_left,
            y,
            "Hinweis: Gemäß § 19 UStG (Kleinunternehmerregelung) wird keine Umsatzsteuer ausgewiesen.",
        )
        y -= GAP_AFTER_NOTE
    else:
        y -= 6 * mm

    # Fälligkeitsdatum (14 Tage fest)
    try:
        invoice_date = datetime.strptime(invoice.get("date", ""), "%d.%m.%Y")
    except ValueError:
        invoice_date = datetime.today()

    due_days = FIXED_DUE_DAYS
    due_date = invoice_date + timedelta(days=due_days)

    # Zahlungsinfos (unten links)
    c.setFont("Helvetica", 9)
    c.drawString(table_left, y, f"Zahlungsziel: {due_days} Tage")
    y -= LINE_GAP_PAYMENT
    c.drawString(table_left, y, f"Fällig am: {due_date.strftime('%d.%m.%Y')}")
    y -= LINE_GAP_PAYMENT

    c.drawString(table_left, y, f"Kontoinhaber: {payment.get('account_holder','')}")
    y -= LINE_GAP_PAYMENT
    c.drawString(table_left, y, f"IBAN: {payment.get('iban','')}")
    if payment.get("bic"):
        y -= LINE_GAP_PAYMENT
        c.drawString(table_left, y, f"BIC: {payment.get('bic','')}")

    c.save()
