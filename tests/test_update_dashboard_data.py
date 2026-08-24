from scripts.update_dashboard_data import refresh_document


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
    assert 'Depot Look-through Dashboard · 24.08.2026' in updated
    assert '"total":120.0' in updated
    assert '"name":"Acme"' in updated
    assert '"boerse":5.0' in updated
    assert '"name":"Bargeld","value":10.0' in updated
    assert '"date":"24.08.2026","value":120.0' in updated
