"""Strict adapter for two reviewed boerse.de fund pages."""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .base import MarketDataProvider, PriceQuote, ProviderError

APPROVED_URLS = {
    "LU2115464500": "https://www.boerse.de/fonds/boersede-Aktienfonds-thesaurierend/LU2115464500",
    "LU2479335734": "https://www.boerse.de/fonds/boersede-Technologiefonds-thesaurierend/LU2479335734",
}


def _text(document: str) -> str:
    document = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", document)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", document))).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _price(value: str) -> Decimal:
    normalized = value.replace(".", "").replace(",", ".")
    try:
        price = Decimal(normalized)
    except InvalidOperation as error:
        raise ProviderError(f"Invalid boerse.de fund price: {value!r}") from error
    if not price.is_finite() or price <= 0:
        raise ProviderError("boerse.de fund price must be greater than zero")
    return price


class BoersedeFundProvider(MarketDataProvider):
    name = "boersede_fund"

    def __init__(self, opener: Callable[..., Any] = urllib.request.urlopen, now: Callable[[], datetime] | None = None):
        self.opener = opener
        self.now = now or (lambda: datetime.now(UTC))

    def search(self, keywords: str):
        raise ProviderError("boerse.de fund mappings require an explicitly reviewed ISIN and URL")

    def _load(self, isin: str, url: str) -> str:
        if APPROVED_URLS.get(isin) != url:
            raise ProviderError("boerse.de fund URL is not approved for this ISIN")
        request = urllib.request.Request(url, headers={"User-Agent": "private-portfolio-market-data-test/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="strict")
        except (OSError, UnicodeError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise ProviderError(f"boerse.de fund request failed: {error}") from error

    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        isin = str(metadata.get("isin") or symbol)
        expected_name = str(metadata.get("expected_fund_name") or "")
        share_class = str(metadata.get("expected_share_class") or "")
        document = _text(self._load(isin, str(metadata.get("url") or "")))
        if isin not in document:
            raise ProviderError(f"boerse.de fund ISIN not found: {isin}")
        normalized = _normalized(document)
        name_tokens = [_normalized(token) for token in re.split(r"[- ]+", expected_name) if len(_normalized(token)) > 2]
        if not expected_name or not share_class or any(token not in normalized for token in name_tokens):
            raise ProviderError(f"boerse.de fund identity mismatch for {isin}")
        if not any(marker in normalized for marker in ("thesaurierend", "acc", _normalized(share_class))):
            raise ProviderError(f"boerse.de fund share-class mismatch for {isin}")
        price_match = re.search(
            r"(?i)(?:fondspreis|anteils(?:wert|preis)|nav|rücknahmepreis|kurs)\s*(?:\([^)]*\))?\s*:?\s*(?:EUR\s*)?([+-]?\d{1,3}(?:\.\d{3})*(?:,\d+)?|[+-]?\d+(?:[.,]\d+)?)\s*(?:EUR)?",
            document,
        )
        if not price_match:
            raise ProviderError("Unexpected boerse.de fund response schema: price missing")
        price = _price(price_match.group(1))
        date_match = re.search(
            r"(?i)(?:bewertungsdatum|kursdatum|nav[ -]?datum|stand|per)\s*:?\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
            document,
        )
        fetched_at = self.now().isoformat().replace("+00:00", "Z")
        if date_match:
            raw_date = date_match.group(1)
            try:
                market_time = datetime.strptime(raw_date, "%d.%m.%Y").date().isoformat() if "." in raw_date else datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
            except ValueError as error:
                raise ProviderError(f"Invalid boerse.de fund price date: {raw_date}") from error
        else:
            market_time = fetched_at
        return PriceQuote(
            instrument_id=instrument_id, price=price, currency="EUR", provider=self.name,
            provider_symbol=isin, exchange=None, market_time=market_time, fetched_at=fetched_at,
            metadata={"isin": isin, "identifier": isin, "fund_name": expected_name,
                      "share_class": share_class, "valuation_price_eur": str(price),
                      "source_url": metadata["url"]},
        )
