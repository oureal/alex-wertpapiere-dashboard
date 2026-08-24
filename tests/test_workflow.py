from pathlib import Path
import urllib.error

from scripts.network_diagnostics import SOURCES, diagnose


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/market-data-test.yml"


def test_workflow_is_manual_read_only_and_has_no_publish_or_schedule():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "push:" not in text
    assert "contents: read" in text
    assert "git push" not in text
    assert "git commit" not in text
    assert "pages" not in text.lower()
    assert "index.html" not in text


def test_workflow_uses_yfinance_without_secret_and_uploads_all_required_private_artifacts():
    text = WORKFLOW.read_text()
    assert "secrets." not in text
    assert "update_yahoo_prices.py" in text
    assert "boerse.de" in text
    assert "yfinance" in (ROOT / "requirements-dev.txt").read_text()
    for filename in (
        "coverage.json",
        "discovery-results.json",
        "research-report.json",
        "latest.json",
        "dry-run-portfolio.json",
        "validation-report.json",
    ):
        assert filename in text
    assert "actions/upload-artifact@v4" in text
    assert "retention-days: 7" in text


def test_network_diagnostics_records_success_without_portfolio_payload():
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    report = diagnose(opener=lambda _request, timeout: Response())
    assert len(report["results"]) == len(SOURCES)
    assert all(row["reachable"] for row in report["results"])
    assert all(set(row) == {"source", "url", "reachable", "http_status", "error", "elapsed_ms"} for row in report["results"])


def test_network_diagnostics_never_raises_for_network_failure():
    def offline(_request, timeout):
        raise urllib.error.URLError("offline")

    report = diagnose(opener=offline)
    assert all(not row["reachable"] for row in report["results"])
    assert all("offline" in row["error"] for row in report["results"])
