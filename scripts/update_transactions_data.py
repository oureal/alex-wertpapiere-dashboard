#!/usr/bin/env python3
from pathlib import Path
import json
import html
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
TRANSACTIONS = ROOT / "data/transactions.json"


def eur(value):
    if value is None:
        return "–"
    s = f"{abs(float(value)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "+" if float(value) > 0 else "-" if float(value) < 0 else ""
    return f"{sign}{s} €"


def num(value):
    if value is None:
        return "–"
    x = float(value)
    return f"{x:g}".replace(".", ",")


def date_de(value):
    y, m, d = value.split("-")
    return f"{d}.{m}.{y}"


def build_section(doc):
    tx = doc.get("transactions", [])
    count = len(tx)
    deposits = sum(float(x.get("amount_eur", 0)) for x in tx if x.get("type") == "Einzahlung")
    withdrawals = sum(abs(float(x.get("amount_eur", 0))) for x in tx if x.get("type") == "Auszahlung")
    fees = sum(float(x.get("fees_eur", 0) or 0) for x in tx)
    orders = sum(1 for x in tx if x.get("type") in {"Kauf", "Verkauf"})
    start = tx[-1]["date"] if tx else None
    end = tx[0]["date"] if tx else None

    rows = []
    for x in tx:
        typ = html.escape(str(x.get("type", "")))
        name = html.escape(str(x.get("name", "")))
        ids = []
        if x.get("wkn"):
            ids.append(f"WKN {html.escape(str(x['wkn']))}")
        if x.get("isin"):
            ids.append(f"ISIN {html.escape(str(x['isin']))}")
        detail = " · ".join(ids)
        qty = num(x.get("quantity")) if x.get("quantity") is not None else "–"
        price = "–"
        if x.get("price") is not None:
            price = f"{num(x.get('price'))} {html.escape(str(x.get('price_currency', 'EUR')))}"
        fees_cell = eur(x.get("fees_eur")) if x.get("fees_eur") not in (None, 0, 0.0) else "–"
        amount = eur(x.get("amount_eur"))
        name_html = f"<b>{name}</b>"
        if detail:
            name_html += f"<div class=\"muted small\">{detail}</div>"
        rows.append(
            "<tr>"
            f"<td>{date_de(x['date'])}</td>"
            f"<td>{typ}</td>"
            f"<td>{name_html}</td>"
            f"<td>{qty}</td>"
            f"<td>{price}</td>"
            f"<td>{fees_cell}</td>"
            f"<td>{amount}</td>"
            "</tr>"
        )

    period = f"{date_de(start)} – {date_de(end)}" if start and end else "–"
    note = html.escape(doc.get("source_note", ""))
    return f'''<!-- TRANSACTIONS_START -->
<section id="transactions" class="page">
 <div class="header"><div><h1>Transaktionen</h1></div><div class="badge">{count} Vorgänge</div></div>
 <div class="grid kpis">
  <div class="card kpi"><div class="label">Zeitraum</div><div class="value" style="font-size:18px">{period}</div><div class="note">historische Onvista-Daten</div></div>
  <div class="card kpi"><div class="label">Käufe & Verkäufe</div><div class="value">{orders}</div><div class="note">Wertpapiertransaktionen</div></div>
  <div class="card kpi"><div class="label">Einzahlungen</div><div class="value">{eur(deposits)}</div><div class="note">historische Geldzuflüsse</div></div>
  <div class="card kpi"><div class="label">Spesen</div><div class="value">{eur(-fees)}</div><div class="note">erfasste Orderkosten</div></div>
 </div>
 <div class="notice small" style="margin-bottom:16px">{note} Auszahlungen gesamt: {eur(-withdrawals)}.</div>
 <div class="card">
  <div class="table-wrap" style="max-height:70vh">
   <table>
    <thead><tr><th>Datum</th><th>Typ</th><th>Bezeichnung</th><th>Stück</th><th>Kurs</th><th>Spesen</th><th>Betrag</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
   </table>
  </div>
 </div>
</section>
<!-- TRANSACTIONS_END -->'''


def main():
    doc = json.loads(TRANSACTIONS.read_text())
    if len(doc.get("transactions", [])) != 240:
        raise SystemExit(f"Expected 240 historical transactions, got {len(doc.get('transactions', []))}")
    text = INDEX.read_text()
    section = build_section(doc)
    marker_pattern = r'<!-- TRANSACTIONS_START -->.*?<!-- TRANSACTIONS_END -->'
    if re.search(marker_pattern, text, flags=re.S):
        text = re.sub(marker_pattern, section, text, count=1, flags=re.S)
    else:
        old_pattern = r'<section id="transactions" class="page">.*?</section>'
        if not re.search(old_pattern, text, flags=re.S):
            raise SystemExit("Transactions section not found")
        text = re.sub(old_pattern, section, text, count=1, flags=re.S)
    INDEX.write_text(text)
    print(f"Rendered {len(doc['transactions'])} transactions into dashboard.")


if __name__ == "__main__":
    main()
