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


def _draw_table_header_and_grid(
    c: canvas.Canvas,
    table_left: float,
    table_right: float,
    y: float,
    col_qty_x: float,
    col_unit_x: float,
    col_amt_x: float,
    grid_bottom_y: float,
) -> float:
    """
    Zeichnet Kopf + horizontale Linien + vertikale Spaltenlinien (Grid).
    Gibt neues y zurück (Startposition für erste Tabellenzeile).
    """
    # Oberer Strich
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(table_left, y, table_right, y)

    # Vertikale Linien (von Kopfbereich bis grid_bottom_y)
    # Spalten: Leistung | Menge | Einzelpreis | Betrag
    c.setLineWidth(0.5)
    c.line(col_qty_x, y, col_qty_x, grid_bottom_y)
    c.line(col_unit_x, y, col_unit_x, grid_bottom_y)
    c.line(col_amt_x, y, col_amt_x, grid_bottom_y)

    # Header-Text
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left, y, "Leistung")
    c.drawRightString(col_unit_x - 5 * mm, y, "Menge")          # rechts in die Menge-Spalte
    c.drawRightString(col_amt_x - 5 * mm, y, "Einzelpreis")      # rechts in die Einzelpreis-Spalte
    c.drawRightString(table_right, y, "Betrag")                  # ganz rechts

    # Trennlinie unter Header
    y -= 4 * mm
    c.setLineWidth(0.5)
    c.line(table_left, y, table_right, y)

    # Start y für Content
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
    # ========= EINSTELLUNGEN =========
    LOGO_W = 80 * mm
    LOGO_H = 50 * mm

    GAP_AFTER_TOTAL = 12 * mm
    GAP_AFTER_NOTE = 15 * mm
    LINE_GAP_PAYMENT = 6 * mm  # <- wenn du die Zeilen unten links näher willst: 5-6mm

    FIXED_DUE_DAYS = 14

    # Default-Positionen (Vorlage), falls items leer ist:
    DEFAULT_ITEMS = [
        {"description": "Behandlung (60 Minuten)", "qty": 1, "unit_price": 0},
        # Du kannst mehr Vorlagen hinzufügen:
        # {"description": "Behandlung (30 Minuten)", "qty": 1, "unit_price": 0},
    ]
    # ================================

    # Datum automatisch heute
    today = datetime.today().strftime("%d.%m.%Y")
    invoice["date"] = today
    invoice["service_date"] = today

    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    table_left = margin_x
    table_right = width - margin_x
    right_x = width - margin_x

    y_top = height - 20 * mm

    # Logo oben links
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

    # Abstand nach Kopf
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

    # Tabelle – Spaltenpositionen
    y -= 10 * mm

    # x-Positionen für Spaltentrenner (du kannst die Zahlen später feinjustieren)
    col_qty_x = table_right - 60 * mm   # Grenze zwischen Leistung und Menge
    col_unit_x = table_right - 30 * mm  # Grenze zwischen Menge und Einzelpreis
    col_amt_x = table_right - 0 * mm    # Grenze zwischen Einzelpreis und Betrag (Betrag ist ganz rechts)
    # Für Betrag brauchen wir keine extra Grenze am rechten Rand, der ist table_right.

    # Unterkante für Grid auf jeder Seite
    grid_bottom_y = 55 * mm

    y = _draw_table_header_and_grid(
        c=c,
        table_left=table_left,
        table_right=table_right,
        y=y,
        col_qty_x=col_qty_x,
        col_unit_x=col_unit_x,
        col_amt_x=table_right - 0 * mm,
        grid_bottom_y=grid_bottom_y,
    )

    # Wenn items leer ist -> Vorlage benutzen
    if not items:
        items = DEFAULT_ITEMS

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
            if y < grid_bottom_y:
                c.showPage()
                y_top2 = height - 20 * mm
                y = y_top2

                # Tabelle neu starten inkl. Grid-Linien
                y = _draw_table_header_and_grid(
                    c=c,
                    table_left=table_left,
                    table_right=table_right,
                    y=y,
                    col_qty_x=col_qty_x,
                    col_unit_x=col_unit_x,
                    col_amt_x=table_right - 0 * mm,
                    grid_bottom_y=grid_bottom_y,
                )

            # Leistung
            c.drawString(table_left, y, wline)

            if first_line:
                qty_str = str(int(qty)) if qty % 1 == 0 else str(qty).rstrip("0").rstrip(".")
                # Menge rechtsbündig innerhalb der Menge-Spalte
                c.drawRightString(col_unit_x - 5 * mm, y, qty_str)
                # Einzelpreis rechtsbündig innerhalb der Einzelpreis-Spalte
                c.drawRightString(table_right - 5 * mm - 30 * mm, y, euro(unit))
                # Betrag ganz rechts
                c.drawRightString(table_right, y, euro(line_total))
                first_line = False

            y -= 6 * mm

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
    invoice_date = datetime.strptime(invoice.get("date", ""), "%d.%m.%Y")
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
