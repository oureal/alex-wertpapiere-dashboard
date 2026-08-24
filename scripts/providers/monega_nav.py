"""Strict adapter for official Monega NAV pages of reviewed share classes."""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .base import MarketDataProvider, PriceQuote, ProviderError

OFFICIAL_HOST = "https://www.monega.de/"


def _text(document: str) -> str:
    document = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", document)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", document))).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _decimal(value: str) -> Decimal:
    normalized = value.replace(".", "").replace(",", ".")
    try:
        price = Decimal(normalized)
    except InvalidOperation as error:
        raise ProviderError(f"Invalid Monega NAV: {value!r}") from error
    if not price.is_finite() or price <= 0:
        raise ProviderError("Monega NAV must be greater than zero")
    return price


class MonegaNavProvider(MarketDataProvider):
    name = "monega_nav"

    def __init__(self, opener: Callable[..., Any] = urllib.request.urlopen, now: Callable[[], datetime] | None = None):
        self.opener = opener
        self.now = now or (lambda: datetime.now(UTC))

    def search(self, keywords: str):
        raise ProviderError("Monega NAV mappings require an explicitly reviewed ISIN and share class")

    def _load(self, url: str) -> str:
        if not url.startswith(OFFICIAL_HOST):
            raise ProviderError("Monega mapping does not use the official monega.de host")
        request = urllib.request.Request(url, headers={"User-Agent": "private-portfolio-market-data-test/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="strict")
        except (OSError, UnicodeError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise ProviderError(f"Monega request failed: {error}") from error

    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        isin = str(metadata.get("isin") or symbol)
        expected_name = str(metadata.get("expected_fund_name") or "")
        share_class = str(metadata.get("expected_share_class") or "")
        if isin not in {"LU2115464500", "LU2479335734"} or not expected_name or not share_class:
            raise ProviderError("Monega mapping is not an approved fund share class")
        text = _text(self._load(str(metadata.get("url") or "")))
        if isin not in text:
            raise ProviderError(f"Monega ISIN not found: {isin}")
        normalized = _normalized(text)
        if _normalized(expected_name) not in normalized or _normalized(share_class) not in normalized:
            raise ProviderError(f"Monega share-class mismatch for {isin}")
        price_match = re.search(
            r"(?i)(?:anteils(?:wert|preis)|nav|rücknahmepreis)\s*(?:\([^)]*\))?\s*:?\s*(?:EUR\s*)?([+-]?\d{1,3}(?:\.\d{3})*(?:,\d+)?|[+-]?\d+(?:[.,]\d+)?)\s*(?:EUR)?",
            text,
        )
        if not price_match:
            raise ProviderError("Unexpected Monega response schema: NAV missing")
        date_match = re.search(
            r"(?i)(?:bewertungsdatum|kursdatum|nav[ -]?datum|stand|per)\s*:?\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
            text,
        )
        if not date_match:
            raise ProviderError("Unexpected Monega response schema: NAV date missing")
        raw_date = date_match.group(1)
        try:
            market_date = datetime.strptime(raw_date, "%d.%m.%Y").date().isoformat() if "." in raw_date else datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
        except ValueError as error:
            raise ProviderError(f"Invalid Monega NAV date: {raw_date}") from error
        price = _decimal(price_match.group(1))
        return PriceQuote(
            instrument_id=instrument_id,
            price=price,
            currency="EUR",
            provider=self.name,
            provider_symbol=isin,
            exchange=None,
            market_time=market_date,
            fetched_at=self.now().isoformat().replace("+00:00", "Z"),
            metadata={
                "isin": isin,
                "identifier": isin,
                "fund_name": expected_name,
                "share_class": share_class,
                "valuation_price_eur": str(price),
                "source_url": metadata["url"],
            },
        )
