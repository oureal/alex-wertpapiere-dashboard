from datetime import UTC, datetime
from decimal import Decimal
import urllib.error

import pytest

from providers.base import ProviderError
from providers.monega_nav import MonegaNavProvider
from scripts.update_yahoo_prices import update_prices


class Headers:
    @staticmethod
    def get_content_charset():
        return "utf-8"


class Response:
    headers = Headers()

    def __init__(self, document):
        self.document = document

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.document.encode()


def document(*, name="boerse.de-Aktienfonds - V EUR ACC", isin="LU2115464500", price="141,37", date="23.08.2026"):
    return f"<html><h1>{name}</h1><dl><dt>ISIN</dt><dd>{isin}</dd><dt>Anteilspreis</dt><dd>{price} EUR</dd><dt>Bewertungsdatum</dt><dd>{date}</dd></dl></html>"


def provider_for(payload):
    return MonegaNavProvider(
        opener=lambda _request, timeout: Response(payload),
        now=lambda: datetime(2026, 8, 24, 12, tzinfo=UTC),
    )


def quote(provider):
    return provider.quote(
        "boerse-de-aktienfonds",
        "LU2115464500",
        isin="LU2115464500",
        expected_fund_name="boerse.de-Aktienfonds - V EUR ACC",
        expected_share_class="V EUR ACC",
        url="https://www.monega.de/fonds/boersede-aktienfonds/",
    )


def test_exact_monega_isin_and_share_class_return_official_eur_nav():
    result = quote(provider_for(document())).to_dict()
    assert result["price"] == "141.37"
    assert result["valuation_price_eur"] == "141.37"
    assert result["currency"] == "EUR"
    assert result["market_time"] == "2026-08-23"
    assert result["isin"] == result["identifier"] == result["provider_symbol"] == "LU2115464500"
    assert result["fund_name"] == "boerse.de-Aktienfonds - V EUR ACC"
    assert result["share_class"] == "V EUR ACC"
    assert result["provider"] == "monega_nav"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (document(name="boerse.de-Aktienfonds - R EUR ACC"), "share-class mismatch"),
        (document(date=""), "NAV date missing"),
        (document(price="0,00"), "greater than zero"),
        ("<html>boerse.de-Aktienfonds - V EUR ACC LU2115464500 changed schema</html>", "response schema"),
    ],
)
def test_invalid_monega_responses_are_rejected(payload, message):
    with pytest.raises(ProviderError, match=message):
        quote(provider_for(payload))


def test_monega_network_failure_is_rejected():
    def offline(_request, timeout):
        raise urllib.error.URLError("offline")

    with pytest.raises(ProviderError, match="Monega request failed"):
        quote(MonegaNavProvider(opener=offline))


def test_monega_failure_keeps_only_positive_legacy_fallback():
    class FailedMonega:
        def quote(self, *_args, **_metadata):
            raise ProviderError("offline")

    instruments = [{"id": "boerse-de-aktienfonds"}]
    mappings = {"mappings": [{
        "instrument_id": "boerse-de-aktienfonds", "isin": "LU2115464500", "symbol": "LU2115464500",
        "primary_provider": "monega_nav", "enabled_for_test": True,
        "expected_fund_name": "boerse.de-Aktienfonds - V EUR ACC", "expected_share_class": "V EUR ACC",
        "source_url": "https://www.monega.de/fonds/boersede-aktienfonds/",
    }]}
    existing = {"prices": [{
        "instrument_id": "boerse-de-aktienfonds", "price": "137.54", "currency": "EUR",
        "provider": "manual_or_legacy_fallback", "status": "fallback", "fetched_at": None,
    }]}

    result = update_prices(instruments, mappings, existing, object(), monega_provider=FailedMonega())

    assert result["prices"][0]["status"] == "fallback"
    assert Decimal(result["prices"][0]["price"]) > 0
    assert "offline" in result["warnings"][0]


def test_monega_failure_rejects_nonpositive_fallback():
    class FailedMonega:
        def quote(self, *_args, **_metadata):
            raise ProviderError("offline")

    mappings = {"mappings": [{
        "instrument_id": "fund", "isin": "LU2115464500", "symbol": "LU2115464500",
        "primary_provider": "monega_nav", "enabled_for_test": True,
        "expected_fund_name": "boerse.de-Aktienfonds - V EUR ACC", "expected_share_class": "V EUR ACC",
        "source_url": "https://www.monega.de/fonds/boersede-aktienfonds/",
    }]}
    existing = {"prices": [{"instrument_id": "fund", "price": "0", "currency": "EUR", "status": "fallback", "fetched_at": None}]}
    with pytest.raises(ValueError, match="No positive"):
        update_prices([{"id": "fund"}], mappings, existing, object(), monega_provider=FailedMonega())
