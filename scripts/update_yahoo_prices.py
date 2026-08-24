#!/usr/bin/env python3
"""Load runtime-validated free-provider quotes and preserve positive fallbacks on failure."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from providers.base import ProviderError
from providers.boersede_fund import BoersedeFundProvider
from providers.monega_nav import MonegaNavProvider
from providers.simple_page import APPROVED as SIMPLE_PAGE_APPROVED, SimplePageProvider
from providers.yfinance_provider import YFinanceProvider

ROOT = Path(__file__).resolve().parents[1]


def _fresh_today(item: dict, today) -> bool:
    fetched = item.get("fetched_at")
    return bool(fetched and item.get("status") == "fresh" and datetime.fromisoformat(fetched.replace("Z", "+00:00")).date() == today)


def update_prices(
    instruments,
    mappings,
    existing,
    provider,
    now=None,
    boersede_provider=None,
    monega_provider=None,
    simple_page_provider=None,
):
    now = now or datetime.now(UTC)
    old = {item["instrument_id"]: item for item in existing["prices"]}
    mapping_by_id = {item["instrument_id"]: item for item in mappings["mappings"]}
    prices, warnings = [], []
    fx_cache: dict[str, Decimal] = {"EUR": Decimal("1")}

    def fx_to_eur(currency: str) -> Decimal:
        if currency in fx_cache:
            return fx_cache[currency]
        symbol = f"{currency}EUR=X"
        quote = provider.quote("fx-" + currency.lower() + "-eur", symbol, expected_name_tokens=[], allowed_quote_types=["CURRENCY"], preferred_currency="EUR")
        fx_cache[currency] = quote.price
        return quote.price

    for instrument in instruments:
        instrument_id = instrument["id"]
        fallback = old.get(instrument_id)
        mapping = mapping_by_id[instrument_id]
        if fallback and _fresh_today(fallback, now.date()):
            prices.append(fallback)
            continue

        # Three exceptional holdings use one explicitly reviewed public page each.
        # This keeps the private dashboard simple: page works -> use it; otherwise
        # continue with the existing provider and ultimately keep the last price.
        if instrument_id in SIMPLE_PAGE_APPROVED and simple_page_provider is not None:
            try:
                simple_quote = simple_page_provider.quote(
                    instrument_id,
                    mapping.get("symbol") or SIMPLE_PAGE_APPROVED[instrument_id]["provider_symbol"],
                    url=SIMPLE_PAGE_APPROVED[instrument_id]["url"],
                ).to_dict()
                prices.append(simple_quote)
                continue
            except ProviderError as error:
                warnings.append(f"{instrument_id}: simple page failed: {error}")

        primary_provider = mapping.get("primary_provider", "yfinance")
        if mapping.get("enabled_for_test") and mapping.get("symbol"):
            try:
                if primary_provider in {"boersede_fund", "monega_nav"}:
                    fund_provider = boersede_provider if primary_provider == "boersede_fund" else monega_provider
                    if fund_provider is None:
                        raise ProviderError(f"{primary_provider} provider is unavailable")
                    quote = fund_provider.quote(
                        instrument_id,
                        mapping["symbol"],
                        isin=mapping["isin"],
                        expected_fund_name=mapping["expected_fund_name"],
                        expected_share_class=mapping["expected_share_class"],
                        url=mapping["source_url"],
                    ).to_dict()
                else:
                    quote = provider.quote(
                        instrument_id,
                        mapping["symbol"],
                        expected_name_tokens=mapping["expected_name_tokens"],
                        allowed_quote_types=mapping["allowed_quote_types"],
                        preferred_currency=mapping.get("preferred_currency"),
                        officially_verified_mapping=mapping.get("officially_verified_mapping"),
                    ).to_dict()
                    rate = fx_to_eur(quote["currency"])
                    quote["valuation_price_eur"] = str(Decimal(quote["price"]) * rate)
                prices.append(quote)
                continue
            except ProviderError as error:
                warnings.append(f"{instrument_id}: {error}")
        else:
            warnings.append(f"{instrument_id}: no enabled free-provider mapping; legacy fallback required")
        if not fallback or Decimal(str(fallback["price"])) <= 0:
            raise ValueError(f"No positive Yahoo or fallback price for {instrument_id}")
        stale = dict(fallback)
        stale["status"] = "fallback" if stale.get("provider") == "manual_or_legacy_fallback" else "stale"
        stale.setdefault("valuation_price_eur", stale["price"] if stale["currency"] == "EUR" else None)
        prices.append(stale)
    return {"schema_version": 1, "prices": prices, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coverage-output", type=Path)
    parser.add_argument("--discovery-output", type=Path)
    parser.add_argument("--existing", type=Path, default=ROOT / "data/prices/latest.json")
    args = parser.parse_args()
    instruments = json.loads((ROOT / "data/portfolio/instruments.yml").read_text())["instruments"]
    mappings = json.loads((ROOT / "data/market-data/yahoo-mappings.yml").read_text())
    existing = json.loads(args.existing.read_text())
    result = update_prices(
        instruments,
        mappings,
        existing,
        YFinanceProvider(),
        boersede_provider=BoersedeFundProvider(),
        monega_provider=MonegaNavProvider(),
        simple_page_provider=SimplePageProvider(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    price_by_id = {item["instrument_id"]: item for item in result["prices"]}
    if args.coverage_output:
        coverage = {
            "schema_version": 1,
            "provider": "free_provider_pipeline",
            "instruments": [
                {
                    "instrument_id": item["id"],
                    "isin": item["isin"],
                    "candidate_symbol": next(row["symbol"] for row in mappings["mappings"] if row["instrument_id"] == item["id"]),
                    **price_by_id[item["id"]],
                    "automatable": price_by_id[item["id"]]["provider"] in {"yfinance", "simple_page", "boersede_fund", "monega_nav"},
                }
                for item in instruments
            ],
        }
        args.coverage_output.parent.mkdir(parents=True, exist_ok=True)
        args.coverage_output.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    if args.discovery_output:
        args.discovery_output.parent.mkdir(parents=True, exist_ok=True)
        args.discovery_output.write_text(json.dumps({"schema_version": 1, "provider": "free_provider_pipeline", "purpose": "runtime_validation", "mappings": mappings["mappings"]}, ensure_ascii=False, indent=2) + "\n")
    for warning in result["warnings"]:
        print(f"Provider warning: {warning}")
    fresh = sum(item["status"] == "fresh" for item in result["prices"])
    print(f"Free-provider update complete: {fresh} fresh, {len(result['prices']) - fresh} stale/fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
