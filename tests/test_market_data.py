import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from providers.alphavantage import AlphaVantageProvider
from providers.base import DailyLimitError, MissingApiKeyError, ProviderError
from scripts.calculate_dry_run import calculate
from scripts.market_data import build_coverage, resolve_quote


def alpha(tmp_path, payload):
    return AlphaVantageProvider(
        api_key="free-test-key",
        usage_file=tmp_path / "usage.json",
        transport=lambda _url: payload,
        today=lambda: date(2026, 8, 24),
    )


def test_missing_api_key(tmp_path):
    provider = AlphaVantageProvider(api_key="", usage_file=tmp_path / "usage.json")
    with pytest.raises(MissingApiKeyError):
        provider.search("DE000A0S9GB0")


def test_free_daily_limit_is_enforced(tmp_path):
    usage = tmp_path / "usage.json"
    usage.write_text(json.dumps({"date": "2026-08-24", "requests": 25}))
    provider = AlphaVantageProvider(api_key="key", usage_file=usage, transport=lambda _url: {}, today=lambda: date(2026, 8, 24))
    with pytest.raises(DailyLimitError):
        provider.search("anything")


@pytest.mark.parametrize(
    ("matches", "expected"),
    [
        ([{"1. symbol": "ONE", "2. name": "One", "4. region": "X", "8. currency": "EUR", "9. matchScore": "1"}], "matched"),
        ([{"1. symbol": "ONE"}, {"1. symbol": "TWO"}], "ambiguous"),
        ([], "not_found"),
    ],
)
def test_search_mapping_statuses(tmp_path, matches, expected):
    assert alpha(tmp_path, {"bestMatches": matches}).search("query").status.value == expected


def test_same_day_fresh_cache_avoids_provider_call():
    class FailingProvider:
        def quote(self, *_args, **_kwargs):
            raise AssertionError("provider must not be called")

    cached = {"instrument_id": "x", "price": "12", "status": "fresh", "fetched_at": "2026-08-24T08:00:00Z"}
    quote, warning = resolve_quote({"id": "x"}, {"primary_provider": "p", "provider_symbol": "X"}, {"p": FailingProvider()}, {"x": cached}, date(2026, 8, 24))
    assert quote is cached
    assert warning is None


def test_provider_failure_uses_positive_stale_fallback():
    class FailedProvider:
        def quote(self, *_args, **_kwargs):
            raise ProviderError("offline")

    cached = {"instrument_id": "x", "price": "12", "status": "fallback", "fetched_at": None}
    quote, warning = resolve_quote({"id": "x"}, {"primary_provider": "p", "provider_symbol": "X"}, {"p": FailedProvider()}, {"x": cached})
    assert quote["status"] == "stale"
    assert Decimal(quote["price"]) > 0
    assert "offline" in warning


def test_no_live_or_cached_price_never_creates_zero():
    quote, warning = resolve_quote({"id": "x"}, {"manual_or_legacy_fallback": True}, {}, {})
    assert quote is None
    assert "No valid" in warning


def test_offline_coverage_does_not_guess_symbols():
    instruments = [{"id": "x", "name": "Example", "isin": "XX"}]
    mappings = {"mappings": [{"instrument_id": "x", "status": "needs_review", "primary_provider": "alphavantage_free", "provider_symbol": None, "manual_or_legacy_fallback": True}]}
    report = build_coverage(instruments, mappings)
    assert report["alpha_vantage_requests"] == 0
    assert report["instruments"][0]["status"] == "needs_review"
    assert report["instruments"][0]["provider_symbol"] is None


def test_dry_run_has_no_zero_prices_and_exact_consistent_sums():
    result = calculate()
    assert all(position["price"] > 0 for position in result["positions"])
    assert all(result["validations"].values())
    assert Decimal(str(result["resolved"])) + Decimal(str(result["unresolved"])) == Decimal(str(result["total"]))


def test_known_legacy_asset_total_difference_is_not_a_hard_failure(tmp_path):
    root = Path(__file__).resolve().parents[1]
    prices = json.loads((root / "data/prices/latest.json").read_text())
    prices["prices"][0]["price"] = "428.1000001"
    prices_path = tmp_path / "prices.json"
    prices_path.write_text(json.dumps(prices))

    result = calculate(prices_path=prices_path)

    assert all(result["validations"].values())
    assert result["legacy_consistency"]["assets_equal_total"] is False


def test_free_provider_mapping_covers_all_instruments_and_funds_use_boersede():
    root = Path(__file__).resolve().parents[1]
    instruments = json.loads((root / "data/portfolio/instruments.yml").read_text())["instruments"]
    mappings = json.loads((root / "data/market-data/yahoo-mappings.yml").read_text())["mappings"]
    assert {item["id"] for item in instruments} == {item["instrument_id"] for item in mappings}
    by_id = {item["instrument_id"]: item for item in mappings}
    assert by_id["boerse-de-aktienfonds"]["primary_provider"] == "boersede_fund"
    assert by_id["boerse-de-technologiefonds"]["primary_provider"] == "boersede_fund"
    assert by_id["boerse-de-aktienfonds"]["enabled_for_test"] is True
    assert by_id["boerse-de-technologiefonds"]["enabled_for_test"] is True
    assert by_id["ishares-core-msci-world"]["allowed_quote_types"] == ["ETF"]
