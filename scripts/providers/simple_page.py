"""Very small provider for three explicitly reviewed public quote pages.

This is intentionally not a generic scraper. It only accepts three hard-coded
instrument/URL pairs used by this private portfolio and falls back to the last
stored positive price if the page layout changes or the request fails.
"""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .base import MarketDataProvider, PriceQuote, ProviderError

APPROVED = {
    "boerse-de-aktienfonds": {
        "isin": "LU2115464500",
        "url": "https://www.boerse.de/fonds/boersede-Aktienfonds-thesaurierend/LU2115464500",
        "provider_symbol": "LU2115464500",
        "exchange": "Stuttgart (EUWAX)",
        "kind": "boerse_de_fund",
    },
    "boerse-de-technologiefonds": {
        "isin": "LU2479335734",
        "url": "https://www.boerse.de/fonds/boersede-Technologiefonds-thesaurierend/LU2479335734",
        "provider_symbol": "LU2479335734",
        "exchange": "Stuttgart (EUWAX)",
        "kind": "boerse_de_fund",
    },
    "wisdomtree-physical-bitcoin": {
        "isin": "GB00BJYDH287",
        "url": "https://www.marketscreener.com/quote/etf/WISDOMTREE-PHYSICAL-BITCO-121444436/quotes/",
        "provider_symbol": "WBIT",
        "exchange": "Xetra",
        "kind": "marketscreener_wbit",
    },
}


def _text(document: str) -> str:
    document = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", document)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", document))).strip()


def _decimal(raw: str) -> Decimal:
    raw = raw.strip().replace("\xa0", " ")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise ProviderError(f"Invalid webpage price: {raw!r}") from error
    if not value.is_finite() or value <= 0:
        raise ProviderError("Webpage price must be positive")
    return value


class SimplePageProvider(MarketDataProvider):
    name = "simple_page"

    def __init__(self, opener: Callable[..., Any] = urllib.request.urlopen, now: Callable[[], datetime] | None = None):
        self.opener = opener
        self.now = now or (lambda: datetime.now(UTC))

    def search(self, keywords: str):
        raise ProviderError("Simple webpage quotes require an explicitly reviewed instrument mapping")

    def _load(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; private-portfolio-dashboard/1.0)",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
            },
        )
        try:
            with self.opener(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise ProviderError(f"Webpage request failed: {error}") from error

    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        approved = APPROVED.get(instrument_id)
        if approved is None:
            raise ProviderError("Instrument is not approved for simple webpage pricing")
        url = str(metadata.get("url") or approved["url"])
        if url != approved["url"]:
            raise ProviderError("URL does not match the approved instrument mapping")

        text = _text(self._load(url))
        isin = approved["isin"]
        if isin not in text:
            raise ProviderError(f"ISIN not found on quote page: {isin}")

        if approved["kind"] == "boerse_de_fund":
            # boerse.de renders the headline quote directly after the ISIN / asset type.
            patterns = [
                rf"ISIN\s*:?\s*{re.escape(isin)}.*?Typ\s*:?\s*Aktienfonds\s+([0-9]{{1,4}}(?:[.,][0-9]{{1,6}})?)\s*EUR",
                r"aktueller Kurs\s*:?\s*([0-9]{1,4}(?:[.,][0-9]{1,6})?)",
            ]
        else:
            # MarketScreener Xetra page: WBIT + ISIN, followed by delayed/closed quote in EUR.
            patterns = [
                rf"{re.escape(isin)}.*?Xetra.*?([0-9]{{1,4}}(?:[.,][0-9]{{1,6}})?)\s*(?:EUR|€)",
                rf"WBIT.*?{re.escape(isin)}.*?([0-9]{{1,4}}(?:[.,][0-9]{{1,6}})?)\s*(?:EUR|€)",
            ]

        match = next((re.search(pattern, text, flags=re.I | re.S) for pattern in patterns if re.search(pattern, text, flags=re.I | re.S)), None)
        if not match:
            raise ProviderError("No positive EUR quote found on approved webpage")
        price = _decimal(match.group(1))

        fetched = self.now()
        date_match = re.search(r"(\d{2}[./]\d{2}[./]\d{4}|\d{4}-\d{2}-\d{2})", text)
        market_time = fetched.isoformat().replace("+00:00", "Z")
        if date_match:
            raw = date_match.group(1).replace("/", ".")
            try:
                market_time = datetime.strptime(raw, "%d.%m.%Y").date().isoformat() if "." in raw else raw
            except ValueError:
                pass

        return PriceQuote(
            instrument_id=instrument_id,
            price=price,
            currency="EUR",
            provider=self.name,
            provider_symbol=approved["provider_symbol"],
            exchange=approved["exchange"],
            market_time=market_time,
            fetched_at=fetched.isoformat().replace("+00:00", "Z"),
            metadata={
                "isin": isin,
                "valuation_price_eur": str(price),
                "source_url": url,
            },
        )
