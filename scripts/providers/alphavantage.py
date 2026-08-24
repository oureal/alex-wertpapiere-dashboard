"""Alpha Vantage free-tier adapter with local daily request accounting."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from .base import (
    CoverageResult,
    CoverageStatus,
    DailyLimitError,
    MarketDataProvider,
    MissingApiKeyError,
    PriceQuote,
    ProviderError,
    ProviderSymbol,
)

Transport = Callable[[str], dict[str, Any]]


class AlphaVantageProvider(MarketDataProvider):
    name = "alphavantage_free"
    daily_limit = 25
    endpoint = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str | None = None, usage_file: Path | None = None, transport: Transport | None = None, today: Callable[[], date] = date.today):
        self.api_key = api_key if api_key is not None else os.getenv("ALPHAVANTAGE_API_KEY")
        self.usage_file = usage_file or Path(".cache/market-data/alphavantage-usage.json")
        self.transport = transport or self._http_get
        self.today = today

    def _require_key(self) -> None:
        if not self.api_key:
            raise MissingApiKeyError("ALPHAVANTAGE_API_KEY is not set")

    def _usage(self) -> dict[str, Any]:
        current = self.today().isoformat()
        if not self.usage_file.exists():
            return {"date": current, "requests": 0}
        state = json.loads(self.usage_file.read_text())
        return state if state.get("date") == current else {"date": current, "requests": 0}

    def _request(self, **params: str) -> dict[str, Any]:
        self._require_key()
        usage = self._usage()
        if usage["requests"] >= self.daily_limit:
            raise DailyLimitError(f"Alpha Vantage free daily limit ({self.daily_limit}) reached")
        query = urllib.parse.urlencode({**params, "apikey": self.api_key})
        usage["requests"] += 1
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        self.usage_file.write_text(json.dumps(usage, indent=2) + "\n")
        try:
            payload = self.transport(f"{self.endpoint}?{query}")
        except Exception as error:
            raise ProviderError(f"Alpha Vantage request failed: {error}") from error
        if any(key in payload for key in ("Error Message", "Information", "Note")):
            message = payload.get("Error Message") or payload.get("Information") or payload.get("Note")
            raise ProviderError(str(message))
        return payload

    @staticmethod
    def _http_get(url: str) -> dict[str, Any]:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)

    def search(self, keywords: str) -> CoverageResult:
        payload = self._request(function="SYMBOL_SEARCH", keywords=keywords)
        matches = payload.get("bestMatches", [])
        candidates = tuple(
            ProviderSymbol(
                symbol=item.get("1. symbol", ""),
                name=item.get("2. name", ""),
                exchange=None,
                region=item.get("4. region"),
                currency=item.get("8. currency"),
                match_score=Decimal(item["9. matchScore"]) if item.get("9. matchScore") else None,
            )
            for item in matches
            if item.get("1. symbol")
        )
        if not candidates:
            return CoverageResult(self.name, CoverageStatus.NOT_FOUND, message="No free search result")
        if len(candidates) == 1:
            return CoverageResult(self.name, CoverageStatus.MATCHED, candidates)
        return CoverageResult(self.name, CoverageStatus.AMBIGUOUS, candidates, "Multiple candidates require review")

    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        if not metadata.get("currency"):
            raise ProviderError(f"Confirmed quote currency is required for {symbol}")
        payload = self._request(function="GLOBAL_QUOTE", symbol=symbol)
        quote = payload.get("Global Quote", {})
        try:
            price = Decimal(quote["05. price"])
        except (KeyError, InvalidOperation) as error:
            raise ProviderError(f"No valid quote returned for {symbol}") from error
        if price <= 0:
            raise ProviderError(f"Non-positive quote returned for {symbol}")
        market_time = quote.get("07. latest trading day")
        if not market_time:
            raise ProviderError(f"No market timestamp returned for {symbol}")
        return PriceQuote(
            instrument_id=instrument_id,
            price=price,
            currency=metadata["currency"],
            provider=self.name,
            provider_symbol=symbol,
            exchange=metadata.get("exchange"),
            market_time=market_time,
            fetched_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
