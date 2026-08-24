#!/usr/bin/env python3
"""Build a non-production portfolio calculation from one consistent pipeline."""
from __future__ import annotations

import csv
import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ZERO = Decimal("0")
SOURCE_FIELDS = {
    "boerse-de-aktienfonds": "boerse",
    "ishares-global-titans-50": "titans",
    "boerse-de-technologiefonds": "tech",
    "ishares-core-msci-world": "world",
    "ishares-msci-world-value-factor": "value",
}
NON_EQUITY = {"etc", "etp"}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def number(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001")))


def balanced_rows(values: list[tuple[str, Decimal]], target: Decimal) -> list[dict[str, Any]]:
    """Round rows to six decimals and put only the rounding residual in the largest row."""
    rounded = [(name, value.quantize(Decimal("0.000001"))) for name, value in values]
    if rounded:
        name, value = rounded[0]
        rounded[0] = (name, value + target - sum((item[1] for item in rounded), ZERO))
    return [{"name": name, "value": number(value)} for name, value in rounded]


def calculate(root: Path = ROOT, prices_path: Path | None = None) -> dict[str, Any]:
    instruments = {item["id"]: item for item in json.loads((root / "data/portfolio/instruments.yml").read_text())["instruments"]}
    holdings = load_csv(root / "data/portfolio/holdings.csv")
    cash_rows = load_csv(root / "data/portfolio/cash.csv")
    cache_doc = json.loads((prices_path or root / "data/prices/latest.json").read_text())
    prices = {item["instrument_id"]: item for item in cache_doc["prices"]}
    legacy = json.loads((root / "data/legacy/index-data-2026-08-21.json").read_text())
    aliases = json.loads((root / "data/lookthrough/aliases.yml").read_text())["aliases"]
    alias_by_instrument: dict[str, list[str]] = defaultdict(list)
    for alias in aliases:
        alias_by_instrument[alias["instrument_id"]].append(alias["alias"])

    positions = []
    warnings = list(cache_doc.get("warnings", []))
    values_by_instrument: dict[str, Decimal] = defaultdict(lambda: ZERO)
    reference_values_by_instrument: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in holdings:
        quote = prices.get(row["instrument_id"])
        if not quote or quote.get("price") in (None, 0, "0"):
            raise ValueError(f"No positive price for {row['instrument_id']}")
        if quote["currency"] != "EUR" and not quote.get("valuation_price_eur"):
            raise ValueError(f"No EUR valuation price for {row['instrument_id']} ({quote['currency']})")
        price = Decimal(str(quote.get("valuation_price_eur") or quote["price"]))
        if price <= 0:
            raise ValueError(f"Non-positive price for {row['instrument_id']}")
        quantity = Decimal(row["quantity"])
        market_value = quantity * price
        values_by_instrument[row["instrument_id"]] += market_value
        reference_values_by_instrument[row["instrument_id"]] += Decimal(row["legacy_market_value_eur"])
        positions.append({"depot": row["depot"], "instrument_id": row["instrument_id"], "quantity": number(quantity), "price": number(Decimal(str(quote["price"]))), "currency": quote["currency"], "valuation_price_eur": number(price), "market_value_eur": number(market_value), "price_status": quote["status"]})
        if quote["status"] != "fresh":
            warnings.append(f"{row['instrument_id']}: using {quote['status']} price from {quote['market_time']}")

    cash = sum((Decimal(row["balance_eur"]) for row in cash_rows), ZERO)
    total = sum(values_by_instrument.values(), ZERO) + cash
    company_values: dict[str, dict[str, Any]] = {}
    for company in legacy["companies"]:
        company_values[company["name"]] = {"name": company["name"], "sector": company["sector"], "direct": ZERO, "indirect": ZERO, "sources": defaultdict(lambda: ZERO)}

    # Direct equity positions resolve entirely to their aliased company.
    direct_total = ZERO
    for instrument_id, value in values_by_instrument.items():
        instrument = instruments[instrument_id]
        if instrument["asset_type"] != "equity":
            continue
        names = alias_by_instrument.get(instrument_id, []) + [instrument["name"]]
        target = next((company_values[name] for name in names if name in company_values), None)
        if target is None:
            raise ValueError(f"No company alias for direct equity {instrument_id}")
        target["direct"] += value
        target["sources"]["direct"] += value
        direct_total += value

    source_totals: dict[str, Decimal] = {field: sum((Decimal(str(company[field])) for company in legacy["companies"]), ZERO) for field in SOURCE_FIELDS.values()}
    resolved_by_source: dict[str, Decimal] = {"direct": direct_total}
    unresolved = cash
    for instrument_id, value in values_by_instrument.items():
        instrument = instruments[instrument_id]
        if instrument_id in SOURCE_FIELDS:
            field = SOURCE_FIELDS[instrument_id]
            base = source_totals[field]
            reference_value = reference_values_by_instrument[instrument_id]
            resolution = min(Decimal("1"), base / reference_value)
            resolved_value = value * resolution
            resolved_by_source[instrument_id] = resolved_value
            unresolved += value - resolved_value
            for legacy_company in legacy["companies"]:
                contribution = Decimal(str(legacy_company[field]))
                if contribution and base:
                    allocated = resolved_value * contribution / base
                    company_values[legacy_company["name"]]["indirect"] += allocated
                    company_values[legacy_company["name"]]["sources"][instrument_id] += allocated
        elif instrument["asset_type"] in NON_EQUITY:
            unresolved += value
        elif instrument["asset_type"] != "equity":
            unresolved += value

    companies = []
    sectors: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for company in company_values.values():
        exposure = company["direct"] + company["indirect"]
        if exposure <= 0:
            continue
        sectors[company["sector"]] += exposure
        companies.append({"name": company["name"], "sector": company["sector"], "direct": number(company["direct"]), "indirect": number(company["indirect"]), "total": number(exposure), "sources": {key: number(value) for key, value in company["sources"].items()}})
    companies.sort(key=lambda item: item["total"], reverse=True)
    resolved = sum((Decimal(str(item["total"])) for item in companies), ZERO)
    # Recompute unresolved from the exact resolved output so the invariant is authoritative.
    unresolved = total - resolved
    sector_rows = balanced_rows(sorted(sectors.items(), key=lambda item: item[1], reverse=True), resolved)
    source_rows = balanced_rows(list(resolved_by_source.items()), resolved)
    assets = balanced_rows(list(values_by_instrument.items()) + [("cash", cash)], total)
    exposures = [Decimal(str(item["total"])) for item in companies]
    hhi = sum(((value / total * 100) ** 2 for value in exposures), ZERO)
    validations = {
        "resolved_plus_unresolved_equals_total": resolved + unresolved == total,
        "company_exposures_equal_resolved": sum(exposures, ZERO) == resolved,
        "sectors_equal_resolved": sum((Decimal(str(item["value"])) for item in sector_rows), ZERO) == resolved,
        "sources_equal_resolved": sum((Decimal(str(item["value"])) for item in source_rows), ZERO) == resolved,
        "assets_equal_total": sum((Decimal(str(item["value"])) for item in assets), ZERO) == total,
        "direct_consistent": Decimal(str(number(resolved_by_source["direct"]))) == Decimal(str(number(direct_total))),
    }
    if not all(validations.values()):
        raise ValueError(f"Dry-run sum validation failed: {validations}")
    return {
        "schema_version": 1, "mode": "dry-run", "price_quality_warnings": sorted(set(warnings)),
        "positions": positions, "cash": number(cash), "total": number(total), "direct_total": number(direct_total),
        "fund_etf_total": number(sum((value for key, value in values_by_instrument.items() if instruments[key]["asset_type"] in {"fund", "etf"}), ZERO)),
        "gold": number(values_by_instrument.get("xetra-gold", ZERO)), "bitcoin_etp": number(values_by_instrument.get("wisdomtree-physical-bitcoin", ZERO)),
        "resolved": number(resolved), "unresolved": number(unresolved), "companies": companies, "sectors": sector_rows,
        "sources": source_rows, "assets": assets, "top10": number(sum(exposures[:10], ZERO)), "top20": number(sum(exposures[:20], ZERO)),
        "hhi": number(hhi), "validations": validations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/generated/dry-run-portfolio.json")
    parser.add_argument("--prices", type=Path, default=ROOT / "data/prices/latest.json")
    args = parser.parse_args()
    result = calculate(prices_path=args.prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("total", "resolved", "unresolved", "hhi", "validations")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
