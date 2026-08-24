#!/usr/bin/env python3
"""Provider-neutral coverage discovery, cache use and stale fallback."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from providers.alphavantage import AlphaVantageProvider
from providers.base import CoverageStatus, MarketDataProvider, ProviderError

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = ROOT / "data/market-data/provider-mappings.yml"
COVERAGE = ROOT / "data/market-data/coverage.json"
PRICE_CACHE = ROOT / "data/prices/latest.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def cached_today(entry: dict[str, Any], today: date) -> bool:
    fetched = entry.get("fetched_at")
    return bool(fetched and datetime.fromisoformat(fetched.replace("Z", "+00:00")).date() == today and entry.get("status") == "fresh")


def resolve_quote(instrument: dict[str, Any], mapping: dict[str, Any], providers: dict[str, MarketDataProvider], cache: dict[str, dict[str, Any]], today: date | None = None) -> tuple[dict[str, Any] | None, str | None]:
    today = today or datetime.now(UTC).date()
    instrument_id = instrument["id"]
    cached = cache.get(instrument_id)
    if cached and cached_today(cached, today):
        return cached, None
    errors = []
    for field in ("primary_provider", "fallback_provider"):
        provider_name = mapping.get(field)
        symbol = mapping.get("provider_symbol") if field == "primary_provider" else mapping.get("fallback_symbol")
        if not provider_name or not symbol:
            continue
        provider = providers.get(provider_name)
        if not provider:
            errors.append(f"Provider unavailable: {provider_name}")
            continue
        try:
            return provider.quote(instrument_id, symbol, currency=mapping.get("currency"), exchange=mapping.get("exchange")).to_dict(), None
        except ProviderError as error:
            errors.append(str(error))
    if cached and Decimal(str(cached["price"])) > 0:
        fallback = dict(cached)
        fallback["status"] = "stale"
        return fallback, "; ".join(errors) or "No live provider mapping; using last valid price"
    return None, "; ".join(errors) or "No valid live or legacy price available"


def build_coverage(instruments: list[dict[str, Any]], mappings: dict[str, Any], live_discovery: bool = False, provider: MarketDataProvider | None = None, discovery: dict[str, Any] | None = None) -> dict[str, Any]:
    by_id = {item["instrument_id"]: item for item in mappings["mappings"]}
    rows = []
    requests = 0
    for instrument in instruments:
        mapping = by_id[instrument["id"]]
        status = CoverageStatus(mapping["status"])
        candidates = []
        message = mapping.get("notes")
        if live_discovery and status != CoverageStatus.MATCHED:
            result = (provider or AlphaVantageProvider()).search(instrument.get("isin") or instrument["name"])
            requests += 1
            status, candidates, message = result.status, [candidate.__dict__ for candidate in result.candidates], result.message
        discovered = (discovery or {}).get("results", {}).get(instrument["id"])
        if discovered:
            status = CoverageStatus(discovered["status"])
            candidates = discovered.get("candidates", [])
            message = discovered.get("message")
        rows.append({
            "instrument_id": instrument["id"], "name": instrument["name"], "isin": instrument.get("isin"),
            "status": status.value, "primary_provider": mapping.get("primary_provider"),
            "fallback_provider": mapping.get("fallback_provider"), "manual_or_legacy_fallback": mapping.get("manual_or_legacy_fallback", True),
            "provider_symbol": mapping.get("provider_symbol"), "exchange": mapping.get("exchange"),
            "currency": mapping.get("currency"), "free": mapping.get("free"), "candidates": candidates, "message": message,
        })
    return {
        "schema_version": 1,
        "generated_without_external_requests": not live_discovery,
        "research_status": "blocked_environment" if not live_discovery else "live_discovery_completed",
        "alpha_vantage_requests": requests,
        "instruments": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true", help="Use Alpha Vantage free SYMBOL_SEARCH (max 23 requests)")
    parser.add_argument("--discovery-results", type=Path, help="Candidate-only discovery JSON to include without activating mappings")
    parser.add_argument("--output", type=Path, default=COVERAGE)
    args = parser.parse_args()
    instruments = load_json(ROOT / "data/portfolio/instruments.yml")["instruments"]
    mappings = load_json(MAPPINGS)
    discovery = load_json(args.discovery_results) if args.discovery_results and args.discovery_results.exists() else None
    report = build_coverage(instruments, mappings, args.discover, discovery=discovery)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
