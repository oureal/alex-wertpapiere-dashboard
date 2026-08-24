from providers.base import CoverageResult, CoverageStatus, ProviderSymbol
from scripts.discover_market_data import discover


class FakeProvider:
    name = "fake_free"

    def __init__(self):
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return CoverageResult(
            self.name,
            CoverageStatus.MATCHED,
            (ProviderSymbol("TEST", "Test", None, "Test Region", "EUR"),),
        )


def test_discovery_is_bounded_and_uses_isin_without_activating_mapping():
    provider = FakeProvider()
    instruments = [
        {"id": "one", "name": "One", "isin": "ISIN1"},
        {"id": "two", "name": "Two", "isin": "ISIN2"},
    ]
    result = discover(instruments, provider, max_requests=1)
    assert result["requests_this_run"] == 1
    assert provider.queries == ["ISIN1"]
    assert result["purpose"] == "candidate_review_only"
    assert result["results"]["one"]["reviewed"] is False


def test_discovery_resumes_without_repeating_completed_request():
    provider = FakeProvider()
    existing = {
        "results": {
            "one": {"instrument_id": "one", "status": "matched", "reviewed": False}
        }
    }
    instruments = [
        {"id": "one", "name": "One", "isin": "ISIN1"},
        {"id": "two", "name": "Two", "isin": "ISIN2"},
    ]
    result = discover(instruments, provider, existing=existing, max_requests=1)
    assert provider.queries == ["ISIN2"]
    assert set(result["results"]) == {"one", "two"}
