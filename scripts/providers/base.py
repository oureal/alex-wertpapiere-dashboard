"""Provider-neutral market-data contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class CoverageStatus(str, Enum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    UNSUPPORTED_FREE = "unsupported_free"
    NEEDS_REVIEW = "needs_review"


class ProviderError(RuntimeError):
    pass


class MissingApiKeyError(ProviderError):
    pass


class DailyLimitError(ProviderError):
    pass


@dataclass(frozen=True)
class ProviderSymbol:
    symbol: str
    name: str
    exchange: str | None
    region: str | None
    currency: str | None
    match_score: Decimal | None = None


@dataclass(frozen=True)
class CoverageResult:
    provider: str
    status: CoverageStatus
    candidates: tuple[ProviderSymbol, ...] = ()
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        for candidate in result["candidates"]:
            if candidate["match_score"] is not None:
                candidate["match_score"] = str(candidate["match_score"])
        return result


@dataclass(frozen=True)
class PriceQuote:
    instrument_id: str
    price: Decimal
    currency: str
    provider: str
    provider_symbol: str
    exchange: str | None
    market_time: str
    fetched_at: str
    status: str = "fresh"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("A market price must be greater than zero")
        datetime.fromisoformat(self.fetched_at.replace("Z", "+00:00"))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        metadata = result.pop("metadata")
        result["price"] = str(self.price)
        result.update(metadata)
        return result


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def search(self, keywords: str) -> CoverageResult:
        """Return provider candidates without guessing a mapping."""

    @abstractmethod
    def quote(self, instrument_id: str, symbol: str, **metadata: Any) -> PriceQuote:
        """Load one positive quote for an explicitly mapped provider symbol."""
