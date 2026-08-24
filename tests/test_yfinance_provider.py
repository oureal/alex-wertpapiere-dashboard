from datetime import UTC, datetime
from decimal import Decimal

import pytest

from providers.base import ProviderError
from providers.yfinance_provider import YFinanceProvider
from providers.base import PriceQuote
from scripts.update_yahoo_prices import update_prices


class Series:
    def __init__(self, values): self.values = values
    def dropna(self): return self
    def items(self): return iter(self.values)


class History:
    def __init__(self, values): self.values = values; self.empty = not values
    def __contains__(self, key): return key == "Close"
    def __getitem__(self, key): return Series(self.values)


class Ticker:
    def __init__(self, info, values=(), error=None): self.info = info; self.values = values; self.error = error
    def history(self, **_kwargs):
        if self.error: raise self.error
        return History(self.values)


def provider(ticker):
    return YFinanceProvider(ticker_factory=lambda _symbol: ticker, now=lambda: datetime(2026, 8, 24, 12, tzinfo=UTC))


def metadata(**extra):
    return {"expected_name_tokens": ["microsoft"], "allowed_quote_types": ["EQUITY"], **extra}


def valid_info(**extra):
    return {"longName": "Microsoft Corporation", "quoteType": "EQUITY", "currency": "USD", "exchange": "NMS", **extra}


def test_valid_yahoo_ticker_uses_last_positive_close_and_currency():
    quote = provider(Ticker(valid_info(), [("2026-08-21", 100), ("2026-08-22", 101.5)])).quote("microsoft", "MSFT", **metadata())
    assert quote.price == Decimal("101.5")
    assert quote.market_time == "2026-08-22"
    assert quote.currency == "USD"
    assert quote.exchange == "NMS"


def test_nonexistent_or_wrong_ticker_is_rejected():
    with pytest.raises(ProviderError, match="identity mismatch"):
        provider(Ticker({"quoteType": "EQUITY", "currency": "USD", "exchange": "NMS"})).quote("x", "NONE", **metadata())


def test_empty_history_without_timestamped_regular_price_is_rejected():
    with pytest.raises(ProviderError, match="No positive timestamped"):
        provider(Ticker(valid_info())).quote("microsoft", "MSFT", **metadata())


def test_empty_history_can_use_positive_timestamped_regular_price():
    info = valid_info(regularMarketPrice=99.5, regularMarketTime=1787400000)
    quote = provider(Ticker(info)).quote("microsoft", "MSFT", **metadata())
    assert quote.price == Decimal("99.5")
    assert quote.market_time


def test_nonpositive_close_and_regular_price_are_rejected():
    info = valid_info(regularMarketPrice=0, regularMarketTime=1787400000)
    with pytest.raises(ProviderError):
        provider(Ticker(info, [("2026-08-21", 0), ("2026-08-22", -1)])).quote("microsoft", "MSFT", **metadata())


def test_network_failure_is_provider_error():
    with pytest.raises(ProviderError, match="Yahoo request failed"):
        provider(Ticker(valid_info(), error=OSError("offline"))).quote("microsoft", "MSFT", **metadata())


def test_preferred_currency_must_match():
    with pytest.raises(ProviderError, match="currency mismatch"):
        provider(Ticker(valid_info(), [("2026-08-22", 1)])).quote("microsoft", "MSFT", **metadata(preferred_currency="EUR"))


def test_equity_and_etf_quote_types_are_mapping_controlled():
    etf = Ticker({"longName": "iShares Core MSCI World", "quoteType": "ETF", "currency": "EUR", "exchange": "GER"}, [("2026-08-22", 120)])
    quote = provider(etf).quote("world", "EUNL.DE", expected_name_tokens=["core", "msci", "world"], allowed_quote_types=["ETF"], preferred_currency="EUR")
    assert quote.price == 120
    with pytest.raises(ProviderError, match="quote type"):
        provider(etf).quote("world", "EUNL.DE", expected_name_tokens=["core"], allowed_quote_types=["EQUITY"])


def test_officially_verified_wisdomtree_mapping_accepts_incomplete_yahoo_identity():
    ticker = Ticker({"exchange": "GER"}, [("2026-08-22", 14.8)])
    verified = {
        "isin": "GB00BJYDH287", "product_ticker": "WBIT", "market": "Germany",
        "trading_currency": "EUR", "currency_override": "EUR", "provenance": "wisdomtree_official_listing",
        "source_url": "https://www.wisdomtree.eu/de-de/products/ucits-etfs-unleveraged-etps/cryptocurrency/wisdomtree-physical-bitcoin",
    }
    quote = provider(ticker).quote(
        "wisdomtree-physical-bitcoin", "WBIT.DE", expected_name_tokens=["wisdomtree", "bitcoin"],
        allowed_quote_types=["ETP"], preferred_currency="EUR", officially_verified_mapping=verified,
    )
    assert quote.price == Decimal("14.8")
    assert quote.currency == "EUR"


def test_official_mapping_does_not_disable_yahoo_identity_checks_globally():
    ticker = Ticker({"currency": "EUR", "exchange": "GER"}, [("2026-08-22", 14.8)])
    with pytest.raises(ProviderError, match="identity mismatch"):
        provider(ticker).quote(
            "another-instrument", "OTHER.DE", expected_name_tokens=["other"], allowed_quote_types=["ETP"],
            preferred_currency="EUR", officially_verified_mapping={"isin": "GB00BJYDH287"},
        )


def test_missing_yahoo_currency_remains_an_error_for_other_instruments():
    ticker = Ticker({"longName": "Microsoft Corporation", "quoteType": "EQUITY", "exchange": "NMS"}, [("2026-08-22", 101)])
    with pytest.raises(ProviderError, match="currency missing"):
        provider(ticker).quote("microsoft", "MSFT", **metadata())


def test_price_update_keeps_fallback_when_yahoo_fails():
    class Quotes:
        def quote(self, instrument_id, symbol, **_metadata):
            if instrument_id == "one":
                return PriceQuote("one", Decimal("10"), "EUR", "yfinance", symbol, "GER", "2026-08-22", "2026-08-24T12:00:00Z")
            raise ProviderError("not found")

    instruments = [{"id": "one"}, {"id": "two"}]
    mappings = {"mappings": [
        {"instrument_id": "one", "symbol": "ONE.DE", "enabled_for_test": True, "expected_name_tokens": ["one"], "allowed_quote_types": ["EQUITY"], "preferred_currency": "EUR"},
        {"instrument_id": "two", "symbol": "NONE", "enabled_for_test": True, "expected_name_tokens": ["two"], "allowed_quote_types": ["EQUITY"], "preferred_currency": "EUR"},
    ]}
    existing = {"prices": [
        {"instrument_id": "one", "price": "8", "currency": "EUR", "provider": "manual_or_legacy_fallback", "status": "fallback", "fetched_at": None},
        {"instrument_id": "two", "price": "9", "currency": "EUR", "provider": "manual_or_legacy_fallback", "status": "fallback", "fetched_at": None},
    ]}
    result = update_prices(instruments, mappings, existing, Quotes(), now=datetime(2026, 8, 24, tzinfo=UTC))
    by_id = {item["instrument_id"]: item for item in result["prices"]}
    assert by_id["one"]["status"] == "fresh"
    assert by_id["one"]["valuation_price_eur"] == "10"
    assert by_id["two"]["status"] == "fallback"
    assert Decimal(by_id["two"]["price"]) > 0
