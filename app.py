from flask import Flask, request, send_file
from invoice_pdf import generate_invoice_pdf
import tempfile
import os

app = Flask(__name__)

# Deine festen Firmendaten
ISSUER = {
    "name": "BK THERAPY",
    "address_lines": ["Augsburgerstraße 100", "86368 Gersthofen", "Deutschland"],
    "phone": "+49 173 8623626",
    "email": "bk-therapy@outlook.de",
    "tax_number": "102/223/41561",
}

PAYMENT = {
    "due_days": 7,  # Zahlungsziel: 7 Tage
    "account_holder": "Bekir Kaan Gülseren",
    "iban": "DE51 7206 9736 0002 5296 37",
    "bic": "GENODEF1BLT",
}

LOGO_PATH = "logo.png"  # dein Logo im gleichen Ordner

HTML_FORM = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>BK THERAPY – Rechnung erstellen</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; }
    input, textarea { width: 100%; padding: 10px; margin: 6px 0 16px; }
    .row { display: flex; gap: 12px; }
    .col { flex: 1; }
    button { padding: 12px 18px; font-size: 16px; cursor: pointer; }
    small { color: #555; }
  </style>
</head>
<body>
  <h2>BK THERAPY – Rechnung erstellen</h2>

  <form method="post" action="/generate">
    <div class="row">
      <div class="col">
        <label>Kundenname</label>
        <input name="client_name" required placeholder="Max Mustermann"/>
      </div>
      <div class="col">
        <label>Rechnungsnummer</label>
        <input name="invoice_number" required placeholder="2026-001"/>
      </div>
    </div>

    <div class="row">
      <div class="col">
        <label>Rechnungsdatum</label>
        <input name="invoice_date" required placeholder="21.01.2026"/>
      </div>
      <div class="col">
        <label>Leistungsdatum</label>
        <input name="service_date" required placeholder="21.01.2026"/>
      </div>
    </div>

    <label>Kundenadresse (eine Zeile pro Zeile)</label>
    <textarea name="client_address" rows="3" placeholder="Musterweg 5&#10;86152 Augsburg"></textarea>

    <h3>Positionen</h3>
    <small>
      Format: Beschreibung | Menge | Preis  
      (z.B. "Massage 60 Min | 1 | 70") – eine Position pro Zeile
    </small>
    <textarea name="items" rows="6" required
      placeholder="Massage (60 Minuten) | 1 | 70&#10;Schröpfen (Rücken) | 1 | 30"></textarea>

    <button type="submit">PDF-Rechnung erstellen</button>
  </form>
</body>
</html>
"""

@app.get("/")
def index():
    return HTML_FORM

@app.post("/generate")
def generate():
    client_name = request.form.get("client_name", "").strip()
    client_address_raw = request.form.get("client_address", "").strip()
    invoice_number = request.form.get("invoice_number", "").strip()
    invoice_date = request.form.get("invoice_date", "").strip()
    service_date = request.form.get("service_date", "").strip()
    items_raw = request.form.get("items", "").strip()

    client = {
        "name": client_name,
        "address_lines": [l.strip() for l in client_address_raw.splitlines() if l.strip()],
    }

    invoice = {
        "title": "Rechnung",
        "number": invoice_number,
        "date": invoice_date,
        "service_date": service_date,
    }

    items = []
    for line in items_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            return f"Fehler in Position: '{line}'. Format: Beschreibung | Menge | Preis", 400
        desc, qty_s, price_s = parts
        try:
            qty = float(qty_s.replace(",", "."))
            price = float(price_s.replace(",", "."))
        except ValueError:
            return f"Fehler: Menge/Preis ungültig in '{line}'", 400
        items.append({"description": desc, "qty": qty, "unit_price": price})

    if not items:
        return "Bitte mindestens eine Position eingeben.", 400

    tmpdir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmpdir, f"Rechnung_{invoice_number}.pdf")

    generate_invoice_pdf(
        output_pdf_path=pdf_path,
        logo_path=LOGO_PATH,
        issuer=ISSUER,
        client=client,
        invoice=invoice,
        items=items,
        payment=PAYMENT,
    )

    return send_file(pdf_path, as_attachment=True,
                     download_name=f"Rechnung_{invoice_number}.pdf")

if __name__ == "__main__":
    # wichtig für Online (Render)
    app.run(host="0.0.0.0", port=5000)