#!/usr/bin/env python3
"""Real-browser smoke test for the generated dashboard."""
from __future__ import annotations

import contextlib
import re
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    "history": [("#historyKpis .card", 4), ("#historyChart svg", 1), ("#historyBars .bar-row", 1)],
    "movers": [("#moversGrid .mover-card", 4), ("#moversGrid .mover-side", 8)],
    "dashboard": [("#kpis .card", 4), ("#topBars .bar-row", 1), ("#assetLegend .legend-row", 1), ("#assetDonut .donut-segment", 1), ("#assetDonut .donut-callout", 8)],
    "treemap": [("#treemapBox .tile", 1)],
    "sectors": [("#sectorBars .bar-row", 1), ("#sectorLegend .legend-row", 1), ("#sectorDonut .donut-segment", 1), ("#sectorDonut .donut-callout", 8)],
    "regions": [("#directCountries .bar-row", 1), ("#nonEquity .bar-row", 1)],
    "risk": [("#riskKpis .card", 4), ("#riskMeters .risk", 1), ("#riskNotes p", 1)],
    "transactions": [("#transactions tbody tr", 439)],
}


def free_port() -> int:
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    port = free_port()
    handler = lambda *a, **kw: SimpleHTTPRequestHandler(*a, directory=str(ROOT), **kw)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    browser_errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda exc: browser_errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: browser_errors.append(f"console error: {msg.text}") if msg.type == "error" else None)
            response = page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
            assert response and response.ok, f"Dashboard HTTP load failed: {response.status if response else 'no response'}"
            page.wait_for_timeout(250)

            for page_id, checks in PAGES.items():
                nav = page.locator(f'#nav button[data-page="{page_id}"]')
                assert nav.count() == 1, f"Navigation button missing for {page_id}"
                nav.click()
                section = page.locator(f"#{page_id}")
                section.wait_for(state="visible")
                assert "active" in (section.get_attribute("class") or "").split(), f"Page {page_id} did not activate"
                for selector, minimum in checks:
                    count = page.locator(selector).count()
                    assert count >= minimum, f"Page {page_id}: expected >= {minimum} elements for {selector}, got {count}"

            # History axis must use years with quarter labels, not arbitrary dates.
            years = page.locator("#historyChart .history-year-label")
            quarters = page.locator("#historyChart .history-quarter-label")
            assert years.count() >= 6, f"Expected year labels, got {years.count()}"
            assert quarters.count() >= 20, f"Expected quarterly labels, got {quarters.count()}"
            assert all(re.fullmatch(r"20\d{2}", (years.nth(i).text_content() or "").strip()) for i in range(years.count()))
            assert all(re.fullmatch(r"Q[1-4]", (quarters.nth(i).text_content() or "").strip()) for i in range(quarters.count()))
            chart_text = page.locator("#historyChart").text_content() or ""
            assert "Kumulierter Geldfluss" in chart_text
            assert "Nettoeinzahlungen" not in chart_text

            # Checkpoint comparison uses only year + half-year intervals and EUR values.
            history_rows = page.locator("#historyBars .bar-row")
            assert history_rows.count() >= 10
            for i in range(history_rows.count()):
                row_text = history_rows.nth(i).inner_text()
                assert re.search(r"20\d{2}\s*·\s*H[12]", row_text), f"Missing half-year interval in row {i}: {row_text}"
                assert "%" not in row_text, f"Unexpected percentage in Stichtagsvergleich row {i}: {row_text}"
                assert "€" in row_text, f"Missing EUR value in Stichtagsvergleich row {i}: {row_text}"
                assert not re.search(r"\d{2}\.\d{2}\.20\d{2}", row_text), f"Raw date still shown in row {i}: {row_text}"

            for selector in ("#assetDonut .donut-segment", "#sectorDonut .donut-segment"):
                segments = page.locator(selector)
                assert segments.count() > 0
                for i in range(segments.count()):
                    title = segments.nth(i).locator("title").text_content() or ""
                    assert "·" in title and "%" in title, f"Missing name/percentage tooltip for {selector} segment {i}"

            assert not browser_errors, "Browser JavaScript/console errors:\n" + "\n".join(browser_errors)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    print("Browser gate passed: all pages render; history uses year/quarter axis, half-year checkpoints and cumulative cash-flow wording.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
