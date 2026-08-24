#!/usr/bin/env python3
"""Controlled, resumable Alpha Vantage free-tier symbol discovery.

This command never activates mappings. It writes candidates for human review only.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from providers.alphavantage import AlphaVantageProvider
from providers.base import DailyLimitError, MissingApiKeyError, ProviderError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/market-data/discovery-results.local.json"


def discover(instruments, provider, existing=None, selected=None, max_requests=23):
    results = dict((existing or {}).get("results", {}))
    requests = 0
    for instrument in instruments:
        instrument_id = instrument["id"]
        if selected and instrument_id not in selected:
            continue
        if instrument_id in results and results[instrument_id].get("status") in {"matched", "ambiguous", "not_found"}:
            continue
        if requests >= max_requests:
            break
        try:
            result = provider.search(instrument.get("isin") or instrument["name"])
            requests += 1
            results[instrument_id] = {
                "instrument_id": instrument_id,
                "isin": instrument.get("isin"),
                **result.to_dict(),
                "reviewed": False,
            }
        except (MissingApiKeyError, DailyLimitError):
            raise
        except ProviderError as error:
            requests += 1
            results[instrument_id] = {
                "instrument_id": instrument_id,
                "isin": instrument.get("isin"),
                "provider": provider.name,
                "status": "needs_review",
                "candidates": [],
                "message": str(error),
                "reviewed": False,
            }
    return {
        "schema_version": 1,
        "purpose": "candidate_review_only",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "requests_this_run": requests,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument", action="append", dest="instruments", help="Internal instrument ID; repeatable")
    parser.add_argument("--max-requests", type=int, default=23)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not 1 <= args.max_requests <= 25:
        parser.error("--max-requests must be between 1 and 25")
    instruments = json.loads((ROOT / "data/portfolio/instruments.yml").read_text())["instruments"]
    known_ids = {item["id"] for item in instruments}
    selected = set(args.instruments or [])
    unknown = selected - known_ids
    if unknown:
        parser.error(f"unknown instrument IDs: {', '.join(sorted(unknown))}")
    existing = json.loads(args.output.read_text()) if args.output.exists() else None
    try:
        report = discover(instruments, AlphaVantageProvider(), existing, selected, args.max_requests)
    except (MissingApiKeyError, DailyLimitError) as error:
        print(f"ERROR: {error}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {report['requests_this_run']} new discovery results to {args.output}")
    print("No provider mapping was activated; every candidate requires explicit review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
