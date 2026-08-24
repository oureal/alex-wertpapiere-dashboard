from datetime import UTC, datetime
from decimal import Decimal
import urllib.error

import pytest

from providers.base import ProviderError
from providers.boersede_fund import APPROVED_URLS, BoersedeFundProvider
from scripts.update_yahoo_prices import update_prices


class Headers:
    def get_content_charset(self): return "utf-8"


class Response:
    headers = Headers()
    def __init__(self, document): self.document = document
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def read(self): return self.document.encode()


FUNDS = (
    ("boerse-de-aktienfonds", "LU2115464500", "boerse.de-Aktienfonds", "V EUR ACC"),
    ("boerse-de-technologiefonds", "LU2479335734", "boerse.de-Technologiefonds", "T EUR ACC"),
)


def provider_for(payload):
    return BoersedeFundProvider(opener=lambda _request, timeout: Response(payload), now=lambda: datetime(2026, 8, 24, 12, tzinfo=UTC))


def quote(provider, instrument_id, isin, name, share_class):
    return provider.quote(instrument_id, isin, isin=isin, expected_fund_name=name,
                          expected_share_class=share_class, url=APPROVED_URLS[isin])


@pytest.mark.parametrize(("instrument_id", "isin", "name", "share_class"), FUNDS)
def test_exact_boersede_fund_isin_returns_positive_eur_price(instrument_id, isin, name, share_class):
    page = f"<h1>{name} thesaurierend {share_class}</h1> ISIN {isin} Kurs: 141,37 EUR Stand: 23.08.2026"
    result = quote(provider_for(page), instrument_id, isin, name, share_class).to_dict()
    assert result["price"] == result["valuation_price_eur"] == "141.37"
    assert result["currency"] == "EUR"
    assert result["market_time"] == "2026-08-23"
    assert result["isin"] == result["provider_symbol"] == isin
    assert result["provider"] == "boersede_fund"


@pytest.mark.parametrize("status", [403, 404])
def test_boersede_http_errors_are_rejected(status):
    def failed(request, timeout):
        raise urllib.error.HTTPError(request.full_url, status, "failed", {}, None)
    with pytest.raises(ProviderError, match="request failed"):
        quote(BoersedeFundProvider(opener=failed), *FUNDS[0])


@pytest.mark.parametrize(
    ("page", "message"),
    [
        ("boerse.de-Aktienfonds thesaurierend V EUR ACC ISIN LU2115464500", "price missing"),
        ("boerse.de-Aktienfonds thesaurierend V EUR ACC ISIN LU2115464500 Kurs: 0,00 EUR", "greater than zero"),
        ("boerse.de-Technologiefonds thesaurierend T EUR ACC ISIN LU2479335734 Kurs: 141,37 EUR", "ISIN not found"),
        ("LU2115464500 changed response schema", "identity mismatch"),
    ],
)
def test_invalid_boersede_fund_pages_are_rejected(page, message):
    with pytest.raises(ProviderError, match=message):
        quote(provider_for(page), *FUNDS[0])


def test_boersede_failure_keeps_positive_legacy_fallback():
    class FailedProvider:
        def quote(self, *_args, **_metadata): raise ProviderError("offline")
    instrument_id, isin, name, share_class = FUNDS[0]
    mappings = {"mappings": [{"instrument_id": instrument_id, "isin": isin, "symbol": isin,
        "primary_provider": "boersede_fund", "enabled_for_test": True, "expected_fund_name": name,
        "expected_share_class": share_class, "source_url": APPROVED_URLS[isin]}]}
    existing = {"prices": [{"instrument_id": instrument_id, "price": "137.54", "currency": "EUR",
                             "provider": "manual_or_legacy_fallback", "status": "fallback", "fetched_at": None}]}
    result = update_prices([{"id": instrument_id}], mappings, existing, object(), boersede_provider=FailedProvider())
    assert result["prices"][0]["status"] == "fallback"
    assert Decimal(result["prices"][0]["price"]) > 0
