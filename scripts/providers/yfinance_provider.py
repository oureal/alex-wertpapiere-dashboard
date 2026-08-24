"""Yahoo Finance adapter using yfinance, with strict runtime identity checks."""
from __future__ import annotations

import importlib
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from .base import MarketDataProvider, PriceQuote, ProviderError


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    def __init__(self, ticker_factory: Callable[[str], Any] | None = None, now: Callable[[], datetime] | None = None):
        if ticker_factory is None:
            ticker_factory = importlib.import_module("yfinance").Ticker
        self.ticker_factory = ticker_factory
        self.now = now or (lambda: datetime.now(UTC))

    def search(self, keywords: str):
        raise ProviderError("yfinance mappings require explicit reviewed symbols")

    @staticmethod
    def _metadata(ticker: Any) -> dict[str, Any]:
        try:
            return dict(ticker.info or {})
        except Exception as error:
            raise ProviderError(f"Yahoo metadata request failed: {error}") from error

    @staticmethod
    def _officially_verified_mapping(instrument_id: str, symbol: str, metadata: dict[str, Any]) -> bool:
        mapping = metadata.get("officially_verified_mapping")
        return bool(
            instrument_id == "wisdomtree-physical-bitcoin"
            and symbol == "WBIT.DE"
            and isinstance(mapping, dict)
            and mapping.get("isin") == "GB00BJYDH287"
            and mapping.get("product_ticker") == "WBIT"
            and mapping.get("market") == "Germany"
            and mapping.get("trading_currency") == "EUR"
            and mapping.get("currency_override") == "EUR"
            and mapping.get("provenance") == "wisdomtree_official_listing"
            and str(mapping.get("source_url", "")).startswith("https://www.wisdomtree.eu/")
        )

    @classmethod
    def _validate_identity(cls, instrument_id: str, symbol: str, info: dict[str, Any], metadata: dict[str, Any]) -> tuple[str, str]:
        name = str(info.get("longName") or info.get("shortName") or "")
        tokens = metadata.get("expected_name_tokens") or []
        normalized = _normalized(name)
        verified = cls._officially_verified_mapping(instrument_id, symbol, metadata)
        if not verified and (not name or any(_normalized(token) not in normalized for token in tokens)):
            raise ProviderError(f"Yahoo identity mismatch for {symbol}: {name!r}")
        quote_type = str(info.get("quoteType") or "").upper()
        allowed = {str(item).upper() for item in metadata.get("allowed_quote_types", ("EQUITY", "ETF", "MUTUALFUND"))}
        if not verified and quote_type not in allowed:
            raise ProviderError(f"Unsupported Yahoo quote type for {symbol}: {quote_type or 'missing'}")
        currency = str(info.get("currency") or "").upper()
        exchange = str(info.get("fullExchangeName") or info.get("exchange") or "")
        if not currency:
            if verified:
                currency = str(metadata["officially_verified_mapping"]["currency_override"])
            else:
                raise ProviderError(f"Yahoo currency missing for {symbol}")
        if not exchange:
            raise ProviderError(f"Yahoo exchange missing for {symbol}")
        preferred = metadata.get("preferred_currency")
        if preferred and currency != str(preferred).upper():
            raise ProviderError(f"Yahoo currency mismatch for {symbol}: expected {preferred}, got {currency}")
        return currency, exchange

    @staticmethod
    def _close_from_history(history: Any) -> tuple[Decimal, str] | None:
        if history is None or getattr(history, "empty", False) or "Close" not in history:
            return None
        closes = history["Close"].dropna()
        for timestamp, raw in reversed(list(closes.items())):
            try:
                price = Decimal(str(raw))
            except (InvalidOperation, ValueError):
                continue
            if price.is_finite() and price > 0:
                market_time = timestamp.to_pydatetime().isoformat() if hasattr(timestamp, "to_pydatetime") else str(timestamp)
                return price, market_time
        return None

    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        try:
            ticker = self.ticker_factory(symbol)
            info = self._metadata(ticker)
            currency, exchange = self._validate_identity(instrument_id, symbol, info, metadata)
            history = ticker.history(period="10d", interval="1d", auto_adjust=False)
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError(f"Yahoo request failed for {symbol}: {error}") from error
        selected = self._close_from_history(history)
        if selected is None:
            raw_price, raw_time = info.get("regularMarketPrice"), info.get("regularMarketTime")
            try:
                price = Decimal(str(raw_price))
            except (InvalidOperation, ValueError):
                price = Decimal("0")
            if not price.is_finite() or price <= 0 or not raw_time:
                raise ProviderError(f"No positive timestamped Yahoo price for {symbol}")
            selected = (price, datetime.fromtimestamp(int(raw_time), UTC).isoformat())
        price, market_time = selected
        return PriceQuote(
            instrument_id=instrument_id,
            price=price,
            currency=currency,
            provider=self.name,
            provider_symbol=symbol,
            exchange=exchange,
            market_time=market_time,
            fetched_at=self.now().isoformat().replace("+00:00", "Z"),
            status="fresh",
        )
