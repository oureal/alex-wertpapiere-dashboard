#!/usr/bin/env python3
"""Fail CI if any visible dashboard page is missing, stale, or structurally empty."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PORTFOLIO = ROOT / "data/generated/dry-run-portfolio.json"
HISTORY = ROOT / "data/history/portfolio-history.json"
SECURITY_HISTORY = ROOT / "data/history/security-history.json"
TX1 = ROOT / "data/transactions-depot1.json"
TX2 = ROOT / "data/transactions.json"

PAGES = {
    "history": "Gesamtdepotentwicklung",
    "movers": "Gewinner & Verlierer",
    "dashboard": "Depotübersicht",
    "treemap": "Interaktive Look-through-Treemap",
    "sectors": "Branchenanalyse",
    "regions": "Länder & Währungen",
    "risk": "Risikoanalyse",
    "transactions": "Transaktionen",
}


def inline_data(html: str) -> dict:
    match = re.search(r"const DATA=(\{.*?\});\n", html, flags=re.S)
    if not match:
        raise AssertionError("Inline DATA object missing")
    return json.loads(match.group(1))


def require_dom_id(html: str, element_id: str) -> None:
    assert re.search(rf'\bid=["\']{re.escape(element_id)}["\']', html), f"DOM element #{element_id} missing"


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    data = inline_data(html)
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    persisted_history = json.loads(HISTORY.read_text(encoding="utf-8"))["history"]
    security_history = json.loads(SECURITY_HISTORY.read_text(encoding="utf-8"))["snapshots"]
    depot1 = json.loads(TX1.read_text(encoding="utf-8"))["transactions"]
    depot2 = json.loads(TX2.read_text(encoding="utf-8"))["transactions"]

    for page_id, title in PAGES.items():
        assert re.search(rf'<section id="{page_id}" class="page(?: active)?">', html), f"Page {page_id} missing"
        assert f'data-page="{page_id}"' in html, f"Navigation for {page_id} missing"
        assert title in html, f"Visible title for {page_id} missing"
    assert html.count('class="page active"') == 1, "Exactly one start page must be active"
    assert '<section id="history" class="page active">' in html, "History must remain the start page"
    assert '<div class="brand">Portfolio</div>' in html, "Portfolio brand missing"
    sidebar = re.search(r'<div class="sub">.*?</div>', html, flags=re.S)
    assert sidebar and "Look-through Dashboard" not in sidebar.group(0), "Old sidebar label returned"
    assert "Fortlaufende Entwicklung des Depotwerts über alle dokumentierten Stichtage" not in html
    assert "US überwiegend Schluss 20.08." not in html, "Hard-coded stale market-data subtitle returned"
    assert re.search(r'<title>Portfolio · \d{2}\.\d{2}\.\d{4}</title>', html), "Browser title not synchronized"
    assert 'responsive-dashboard-v2' in html, "Responsive CSS marker missing"
    assert 'id="manualUpdateLink"' in html, "Manual update control missing"

    assert float(data["meta"]["total"]) > 0
    assert abs(float(data["meta"]["total"]) - float(portfolio["total"])) < 1e-6
    assert len(data.get("companies", [])) >= 100, "Look-through company data unexpectedly sparse"
    assert data.get("sectors"), "Sector data empty"
    assert data.get("assets"), "Asset allocation data empty"
    assert float(data["meta"]["directTotal"]) > 0
    assert float(data["meta"]["resolved"]) > 0
    for element_id in ("kpis", "topBars", "assetDonut", "assetLegend", "directIndirect", "resolution", "treemapBox", "companyDetail", "sectorBars", "sectorDonut", "sectorLegend", "sectorCompanies", "directCountries", "nonEquity", "riskKpis", "riskMeters", "overlapList", "riskNotes"):
        require_dom_id(html, element_id)

    history = data.get("history", [])
    assert history == persisted_history, "Inline/persisted history mismatch"
    assert len(history) > 300, f"History too short: {len(history)}"
    assert float(history[0].get("net_contributions", 0)) > 0, "History starts before first positive contribution"
    assert all("net_contributions" in row and "gain" in row for row in history), "Cash-flow fields missing"
    assert abs(float(history[-1]["value"]) - float(data["meta"]["total"])) < 1e-6
    assert "dynamic-history-labels-v2" not in html, "Obsolete history KPI override still present"
    assert "Kumulierter Geldfluss" in html, "Cumulative cash-flow wording missing"
    assert "net_contributions" in html, "Cash-flow series missing from rendered dashboard"
    assert "history-quarter-label" in html and "Q${q}" in html, "Quarter-axis renderer missing"
    assert "checkpointRows" in html and "H${half}" in html, "Checkpoint renderer missing"
    for element_id in ("historyChart", "historyKpis", "historyBars", "historyRangeControls", "checkpointControls"):
        require_dom_id(html, element_id)
    for token in ('data-range="m1"', 'data-range="m6"', 'data-range="y1"', 'data-range="y3"', 'data-range="y5"', 'data-range="max"'):
        assert token in html, f"History range control missing: {token}"
    assert 'data-mode="year"' in html and 'data-mode="half"' in html, "Checkpoint mode controls missing"

    movers = data.get("movers", {})
    periods = movers.get("periods", {})
    assert set(periods) >= {"day", "week", "month", "total"}, "Mover periods incomplete"
    for key in ("day", "week", "month", "total"):
        period = periods[key]
        assert period.get("from"), f"Mover baseline missing for {key}"
        assert int(period.get("coverage", 0)) > 0, f"Mover coverage empty for {key}"
        assert period.get("gainers") or period.get("losers"), f"No mover rows for {key}"
    assert len(security_history) >= 2, "Security history needs at least two snapshots"
    require_dom_id(html, "moversGrid")
    require_dom_id(html, "moversAsOf")

    assert len(depot1) == 199 and len(depot2) == 240
    assert "440 Vorgänge" in html
    section = re.search(r'<section id="transactions" class="page">(.*?)</section>', html, flags=re.S)
    assert section, "Transactions section missing"
    tbody = re.search(r'<tbody>(.*?)</tbody>', section.group(1), flags=re.S)
    assert tbody, "Transaction table body missing"
    rendered_rows = tbody.group(1).count("<tr>")
    assert rendered_rows == 440, f"Expected 440 rendered transaction rows, got {rendered_rows}"
    assert "28.08.2026" in section.group(1) and "+1.000,00 €" in section.group(1), "Confirmed Depot 2 deposit missing"
    assert "Depot 1" in section.group(1) and "Depot 2" in section.group(1)

    print(
        "Dashboard complete: 8 pages; "
        f"{len(data['companies'])} companies; {len(data['sectors'])} sectors; "
        f"{len(history)} history points; movers day/week/month/total populated; "
        f"{rendered_rows} effective transactions rendered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
