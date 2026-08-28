#!/usr/bin/env python3
# This script is intentionally the single safe dashboard shell synchronizer used by the production workflow.
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import json
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PRICES = ROOT / "data/prices/latest.json"
TRANSACTIONS = ROOT / "data/transactions.json"


def latest_stamp() -> str | None:
    if not PRICES.exists():
        return None
    doc = json.loads(PRICES.read_text())
    stamps = [x.get("fetched_at") for x in doc.get("prices", []) if x.get("fetched_at")]
    if not stamps:
        return None
    newest = max(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
    local = newest.astimezone(ZoneInfo("Europe/Vienna"))
    return local.strftime("%d.%m.%Y, %H:%M Uhr")


def fmt_number(value, digits=2) -> str:
    if value in (None, ""):
        return "–"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    text = f"{number:,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def transaction_section() -> str:
    doc = {"transactions": []}
    if TRANSACTIONS.exists():
        doc = json.loads(TRANSACTIONS.read_text())
    rows = list(doc.get("transactions", []))
    rows.sort(key=lambda x: (str(x.get("date", "")), str(x.get("time", ""))), reverse=True)

    labels = {
        "deposit": "Einzahlung",
        "withdrawal": "Auszahlung",
        "buy": "Kauf",
        "sell": "Verkauf",
        "dividend": "Dividende",
        "fee": "Gebühr",
        "other": "Sonstige",
    }

    if not rows:
        body = '<div class="card"><div class="muted">Noch keine Transaktionen erfasst.</div></div>'
    else:
        table_rows = []
        for item in rows:
            kind = str(item.get("type", "other"))
            security = item.get("security") or item.get("name") or "–"
            isin = item.get("isin") or ""
            security_html = escape(str(security))
            if isin:
                security_html += f'<div class="muted small">{escape(str(isin))}</div>'
            currency = escape(str(item.get("currency") or "EUR"))
            amount = item.get("amount")
            amount_html = "–" if amount in (None, "") else f'{fmt_number(amount)} {currency}'
            price = item.get("price")
            price_html = "–" if price in (None, "") else f'{fmt_number(price, 4)} {currency}'
            fees = item.get("fees")
            fees_html = "–" if fees in (None, "") else f'{fmt_number(fees)} {currency}'
            note = escape(str(item.get("note") or "")) or "–"
            table_rows.append(
                "<tr>"
                f'<td style="text-align:left">{escape(str(item.get("date") or "–"))}</td>'
                f'<td style="text-align:left"><span class="pill">{escape(labels.get(kind, kind))}</span></td>'
                f'<td style="text-align:left">{security_html}</td>'
                f'<td>{fmt_number(item.get("quantity"), 6)}</td>'
                f'<td>{price_html}</td>'
                f'<td>{amount_html}</td>'
                f'<td>{fees_html}</td>'
                f'<td style="text-align:left;white-space:normal;min-width:180px">{note}</td>'
                "</tr>"
            )
        body = (
            '<div class="card"><div class="table-wrap" style="max-height:none">'
            '<table><thead><tr>'
            '<th style="text-align:left">Datum</th><th style="text-align:left">Art</th>'
            '<th style="text-align:left">Wertpapier</th><th>Stück</th><th>Kurs</th>'
            '<th>Betrag</th><th>Gebühren</th><th style="text-align:left">Details</th>'
            '</tr></thead><tbody>' + "".join(table_rows) + '</tbody></table></div></div>'
        )

    return (
        '<section id="transactions" class="page">\n'
        ' <div class="header"><div><h1>Transaktionen</h1></div></div>\n'
        f' {body}\n'
        '</section>'
    )


def synchronize_transactions(text: str) -> str:
    if 'data-page="transactions"' not in text:
        risk_button = '<button data-page="risk"><span class="n">7</span>Risiko</button>'
        transaction_button = '<button data-page="transactions"><span class="n">8</span>Transaktionen</button>'
        if risk_button not in text:
            raise SystemExit("Risk navigation button not found")
        text = text.replace(risk_button, risk_button + "\n    " + transaction_button, 1)

    section = transaction_section()
    pattern = r'<section id="transactions" class="page(?: active)?">.*?</section>'
    if re.search(pattern, text, flags=re.S):
        text = re.sub(pattern, section, text, count=1, flags=re.S)
    else:
        if "</main>" not in text:
            raise SystemExit("Main closing tag not found")
        text = text.replace("</main>", section + "\n</main>", 1)
    return text


def main() -> int:
    text = INDEX.read_text()
    original = text
    text = text.replace("Portfolio Lens", "Portfolio")
    text = text.replace('<div class="muted">Fortlaufende Entwicklung des Depotwerts über alle dokumentierten Stichtage</div>', '')
    text = text.replace('<div class="notice small" style="margin-top:16px">Die Rangfolge basiert auf der Veränderung des Positionswerts in EUR und Prozent zwischen zwei gespeicherten Stichtagen. Käufe, Verkäufe oder Stückzahländerungen können den Wertbeitrag beeinflussen; die Anzeige ist daher keine bereinigte Kursperformance.</div>', '')
    stamp = latest_stamp()
    if stamp:
        text = re.sub(r'<div class="sub">.*?</div>', f'<div class="sub">Stand {stamp}</div>', text, count=1, flags=re.S)
        text = re.sub(r'Datenstand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?', f'Datenstand {stamp}', text)
    else:
        text = re.sub(r'<div class="sub">\s*Look-through Dashboard\s*·?\s*(.*?)</div>', r'<div class="sub">\1</div>', text, count=1, flags=re.S)

    text = synchronize_transactions(text)

    sidebar = re.search(r'<div class="sub">.*?</div>', text, flags=re.S)
    if not sidebar:
        raise SystemExit("Sidebar status element missing")
    if "Look-through Dashboard" in sidebar.group(0):
        raise SystemExit("Sidebar label removal failed")
    if "Fortlaufende Entwicklung des Depotwerts über alle dokumentierten Stichtage" in text:
        raise SystemExit("History subtitle removal failed")
    if "Die Rangfolge basiert auf der Veränderung des Positionswerts" in text:
        raise SystemExit("Movers explanatory notice removal failed")
    if 'data-page="transactions"' not in text or 'id="transactions"' not in text:
        raise SystemExit("Transactions page synchronization failed")

    if text != original:
        INDEX.write_text(text)
        print("Dashboard shell synchronized.")
    else:
        print("Dashboard shell already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
