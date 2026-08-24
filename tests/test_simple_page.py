from datetime import UTC, datetime

import pytest

from providers.base import ProviderError
from providers.simple_page import SimplePageProvider


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


def provider(document):
    return SimplePageProvider(
        opener=lambda _request, timeout: Response(document),
        now=lambda: datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
    )


def test_boersede_aktienfonds_headline_price():
    document = """
    <html><body>
    boerse.de-Aktienfonds (thesaurierend) WKN A2PZMR ISIN: LU2115464500
    Typ: Aktienfonds 140,21 EUR 0,30 EUR 0,21 % 11:46:20 Stuttgart (EUWAX)
    </body></html>
    """
    quote = provider(document).quote(
        "boerse-de-aktienfonds", "LU2115464500",
        url="https://www.boerse.de/fonds/boersede-Aktienfonds-thesaurierend/LU2115464500",
    )
    assert str(quote.price) == "140.21"
    assert quote.currency == "EUR"
    assert quote.provider == "simple_page"


def test_boersede_technologiefonds_headline_price():
    document = """
    <html><body>
    boerse.de-Technologiefonds (thesaurierend) WKN TMG4TT ISIN: LU2479335734
    Typ: Aktienfonds 156,32 EUR 2,47 EUR 1,61 % 21:55:04 Stuttgart (EUWAX)
    </body></html>
    """
    quote = provider(document).quote(
        "boerse-de-technologiefonds", "LU2479335734",
        url="https://www.boerse.de/fonds/boersede-Technologiefonds-thesaurierend/LU2479335734",
    )
    assert str(quote.price) == "156.32"


def test_wbit_marketscreener_xetra_price():
    document = """
    <html><body>
    WisdomTree Physical Bitcoin - USD WBIT GB00BJYDH287
    Market Closed - Xetra 17:36:01 21/08/2026 15,86 EUR +7,28 %
    </body></html>
    """
    quote = provider(document).quote(
        "wisdomtree-physical-bitcoin", "WBIT",
        url="https://www.marketscreener.com/quote/etf/WISDOMTREE-PHYSICAL-BITCO-121444436/quotes/",
    )
    assert str(quote.price) == "15.86"
    assert quote.exchange == "Xetra"


def test_wrong_url_or_missing_isin_is_rejected():
    with pytest.raises(ProviderError):
        provider("LU2115464500 140,21 EUR").quote(
            "boerse-de-aktienfonds", "LU2115464500", url="https://example.com"
        )
    with pytest.raises(ProviderError):
        provider("Typ: Aktienfonds 140,21 EUR").quote(
            "boerse-de-aktienfonds", "LU2115464500",
            url="https://www.boerse.de/fonds/boersede-Aktienfonds-thesaurierend/LU2115464500",
        )
