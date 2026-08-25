import json
import re

from scripts.update_dashboard_data import refresh_document


def _dashboard_data(document: str) -> dict:
    match = re.search(r"const DATA=(\{.*?\});\n", document, flags=re.S)
    assert match
    return json.loads(match.group(1))


def test_refresh_document_replaces_dynamic_dashboard_values():
    index = '''<html><head><title>Depot Look-through Dashboard · 21.08.2026</title></head><body>\nLook-through Dashboard · Stand 21.08.2026\nDatenstand 21.08.2026\nDepotwerte 21.08.2026\n<script>\nconst DATA={"meta":{"asof":"21.08.2026","total":100.0,"companyCount":5},"companies":[],"sectors":[],"assets":[],"history":[{"date":"21.08.2026","value":100.0}]};\n</script></body></html>'''
    portfolio = {
        "total": 120.0,
        "resolved": 90.0,
        "unresolved": 30.0,
        "direct_total": 60.0,
        "top10": 70.0,
        "top20": 85.0,
        "hhi": 500.0,
        "cash": 10.0,
        "gold": 5.0,
        "bitcoin_etp": 2.0,
        "companies": [{"name": "Acme", "sector": "Tech", "direct": 20.0, "indirect": 5.0, "total": 25.0, "sources": {"direct": 20.0, "boerse-de-aktienfonds": 5.0}}],
        "sectors": [{"name": "Tech", "value": 25.0}],
        "assets": [{"name": "cash", "value": 10.0}],
    }
    prices = {"prices": [{"fetched_at": "2026-08-24T13:33:00Z"}]}
    updated = refresh_document(index, portfolio, prices)
    assert '<title>Portfolio · 24.08.2026</title>' in updated
    assert '"total":120.0' in updated
    assert '"name":"Acme"' in updated
    assert '"boerse":5.0' in updated
    assert '"name":"Bargeld","value":10.0' in updated
    assert '"date":"24.08.2026","value":120.0' in updated


def test_same_day_refresh_keeps_previous_day_as_change_baseline():
    index = '''<html><head><title>Depot Look-through Dashboard · 24.08.2026</title></head><body>\nLook-through Dashboard · Stand 24.08.2026\nDatenstand 24.08.2026\nDepotwerte 24.08.2026\n<script>\nconst DATA={"meta":{"asof":"24.08.2026","total":120.0,"previousTotal":100.0},"companies":[],"sectors":[],"assets":[],"history":[{"date":"21.08.2026","value":100.0},{"date":"24.08.2026","value":120.0}]};\n</script></body></html>'''
    portfolio = {
        "total": 125.0,
        "resolved": 100.0,
        "unresolved": 25.0,
        "direct_total": 70.0,
        "top10": 75.0,
        "top20": 90.0,
        "hhi": 500.0,
        "cash": 10.0,
        "gold": 5.0,
        "bitcoin_etp": 2.0,
        "companies": [],
        "sectors": [],
        "assets": [],
    }
    prices = {"prices": [{"fetched_at": "2026-08-24T16:00:00Z"}]}

    updated = refresh_document(index, portfolio, prices)
    data = _dashboard_data(updated)

    assert [(row["date"], row["value"]) for row in data["history"]] == [
        ("21.08.2026", 100.0),
        ("24.08.2026", 125.0),
    ]
    assert all("net_contributions" in row for row in data["history"])
    assert data["meta"]["previousTotal"] == 100.0
    assert data["meta"]["change"] == 25.0
    assert data["meta"]["changePct"] == 0.25
