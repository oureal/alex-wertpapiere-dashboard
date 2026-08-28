#!/usr/bin/env python3
"""Validate migrated portfolio data and report known legacy inconsistencies."""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path

from verify_immutable_history import verify as verify_history

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data/legacy/validation-report.json"
TOLERANCE = 0.01
LEGACY_CUTOFF = "2026-08-21"


def close(left: float, right: float) -> bool:
    return abs(left - right) <= TOLERANCE


def valid_isin(isin: str) -> bool:
    if len(isin) != 12 or not isin[:2].isalpha() or not isin[2:].isalnum():
        return False
    expanded = "".join(str(int(char, 36)) for char in isin.upper())
    total = 0
    for index, digit in enumerate(reversed(expanded)):
        value = int(digit) * (1 if index % 2 == 0 else 2)
        total += value // 10 + value % 10
    return total % 10 == 0


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def build_report(root: Path = ROOT) -> dict:
    legacy = json.loads((root / "data/legacy/index-data-2026-08-21.json").read_text())
    instrument_doc = json.loads((root / "data/portfolio/instruments.yml").read_text())
    instruments = instrument_doc["instruments"]
    holdings = load_csv(root / "data/portfolio/holdings.csv")
    cash = load_csv(root / "data/portfolio/cash.csv")
    transactions = load_csv(root / "data/portfolio/transactions.csv")
    dry_run = json.loads((root / "data/generated/dry-run-portfolio.json").read_text())
    ids = [item["id"] for item in instruments]
    instrument_by_id = {item["id"]: item for item in instruments}

    checks: list[dict] = []
    inconsistencies: list[dict] = []

    def check(name: str, passed: bool, details: dict | None = None) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "details": details or {}})

    check("unique_instrument_ids", len(ids) == len(set(ids)), {"count": len(ids)})
    invalid_isins = [item["id"] for item in instruments if item["isin"] and not valid_isin(item["isin"])]
    check("valid_present_isins", not invalid_isins, {"invalid_instrument_ids": invalid_isins})
    negative = [row for row in holdings if row["quantity"] and float(row["quantity"]) < 0]
    check("no_unintended_negative_quantities", not negative, {"negative_rows": negative})
    unknown = sorted({row["instrument_id"] for row in holdings} - set(ids))
    check("holdings_reference_known_instruments", not unknown, {"unknown_instrument_ids": unknown})
    siemens_energy = next(
        (row for row in transactions if row["instrument_id"] == "siemens-energy"),
        None,
    )
    broadcom = next((row for row in holdings if row["instrument_id"] == "broadcom"), None)
    check(
        "siemens_energy_depot_assignment_confirmed",
        siemens_energy is not None
        and broadcom is not None
        and siemens_energy["depot"] == "Depot 2"
        and siemens_energy["depot"] == broadcom["depot"]
        and siemens_energy["needs_confirmation"] == "false",
        {
            "depot": siemens_energy["depot"] if siemens_energy else None,
            "broadcom_depot": broadcom["depot"] if broadcom else None,
            "needs_confirmation": siemens_energy["needs_confirmation"] if siemens_energy else None,
        },
    )
    for name, passed in dry_run["validations"].items():
        check(f"dry_run_{name}", passed, {"dry_run_total": dry_run["total"]})

    meta = legacy["meta"]
    check(
        "resolved_plus_unresolved_equals_total",
        close(meta["resolved"] + meta["unresolved"], meta["total"]),
        {"resolved": meta["resolved"], "unresolved": meta["unresolved"], "total": meta["total"]},
    )
    company_total = sum(company["total"] for company in legacy["companies"])
    check(
        "company_exposures_equal_resolved",
        close(company_total, meta["resolved"]),
        {"company_exposures": company_total, "resolved": meta["resolved"]},
    )
    company_direct = sum(company["direct"] for company in legacy["companies"])
    # Compare only holdings belonging to the immutable legacy snapshot. Positions
    # bought after 2026-08-21 are valid live holdings, not part of the legacy baseline.
    migrated_direct = sum(
        float(row["legacy_market_value_eur"])
        for row in holdings
        if row["as_of"] <= LEGACY_CUTOFF
        and instrument_by_id[row["instrument_id"]]["asset_type"] == "equity"
    )
    check(
        "direct_holdings_consistent_with_company_exposures",
        close(migrated_direct, company_direct) and close(company_direct, meta["directTotal"]),
        {
            "legacy_cutoff": LEGACY_CUTOFF,
            "migrated_direct": migrated_direct,
            "company_direct": company_direct,
            "meta_direct": meta["directTotal"],
        },
    )
    migrated_cash = sum(float(row["balance_eur"]) for row in cash)
    # cash.csv is a live portfolio input while meta.cash belongs to the immutable
    # 2026-08-21 legacy reference. Deposits after that date are expected to make
    # the two values diverge, so validate the live cash input itself rather than
    # incorrectly treating a legitimate new cashflow as a migration failure.
    check(
        "current_cash_is_non_negative",
        migrated_cash >= 0,
        {"current_cash": migrated_cash, "legacy_meta_cash": meta["cash"], "difference": migrated_cash - meta["cash"]},
    )
    migrated_total = sum(float(row["legacy_market_value_eur"]) for row in holdings) + migrated_cash
    price_plausibility = []
    for row in holdings:
        if not row["quantity"] or not row["derived_legacy_unit_price_eur"]:
            continue
        quantity = Decimal(row["quantity"])
        unit_price = Decimal(row["derived_legacy_unit_price_eur"])
        documented_value = Decimal(row["legacy_market_value_eur"])
        reproduced_value = quantity * unit_price
        difference = reproduced_value - documented_value
        price_plausibility.append(
            {
                "depot": row["depot"],
                "instrument_id": row["instrument_id"],
                "quantity": str(quantity),
                "legacy_unit_price_eur": str(unit_price),
                "documented_value_eur": str(documented_value),
                "reproduced_value_eur": str(reproduced_value),
                "difference_eur": str(difference),
                "status": "plausible" if abs(difference) <= Decimal("0.01") else "mismatch",
                "price_is_derived": row["instrument_id"] != "siemens-energy",
            }
        )
    check(
        "quantities_times_legacy_unit_prices_reproduce_values",
        all(item["status"] == "plausible" for item in price_plausibility),
        {"checked_rows": len(price_plausibility)},
    )
    immutable_errors = verify_history(root=root)
    check("immutable_legacy_files_unchanged", not immutable_errors, {"errors": immutable_errors})

    aggregates = {
        "meta_total": meta["total"],
        "assets_total": sum(item["value"] for item in legacy["assets"]),
        "meta_resolved": meta["resolved"],
        "sectors_total": sum(item["value"] for item in legacy["sectors"]),
        "sources_total": sum(item["value"] for item in legacy["sources"]),
        "meta_direct": meta["directTotal"],
        "asset_direct": next(item["value"] for item in legacy["assets"] if item["name"] == "Direktbestand"),
        "migrated_holdings_plus_cash": migrated_total,
    }
    for identifier, left, right in (
        ("assets_total_differs_from_meta_total", aggregates["assets_total"], aggregates["meta_total"]),
        ("sectors_total_differs_from_meta_resolved", aggregates["sectors_total"], aggregates["meta_resolved"]),
        ("sources_total_differs_from_meta_resolved", aggregates["sources_total"], aggregates["meta_resolved"]),
        ("asset_direct_differs_from_meta_direct", aggregates["asset_direct"], aggregates["meta_direct"]),
        ("migrated_legacy_values_differ_from_meta_total", aggregates["migrated_holdings_plus_cash"], aggregates["meta_total"]),
    ):
        if not close(left, right):
            inconsistencies.append({"id": identifier, "status": "known_legacy_warning", "left": left, "right": right, "difference": left - right, "corrected": False})

    missing_market_data = [
        {"instrument_id": item["id"], "name": item["name"], "missing": [field for field in ("ticker", "exchange", "price_source") if item[field] is None]}
        for item in instruments
        if any(item[field] is None for field in ("ticker", "exchange", "price_source"))
    ]
    missing_master_data = [
        {"instrument_id": item["id"], "name": item["name"], "missing": item["missing_fields"]}
        for item in instruments
        if item["missing_fields"]
    ]
    return {
        "schema_version": 1,
        "legacy_reference": "data/legacy/index-data-2026-08-21.json",
        "overall_status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "checks": checks,
        "known_legacy_inconsistencies": inconsistencies,
        "legacy_aggregates": aggregates,
        "missing_master_data": missing_master_data,
        "missing_market_data": missing_market_data,
        "legacy_value_plausibility": price_plausibility,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check-report", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.check_report:
        if not args.report.exists() or args.report.read_text() != rendered:
            print(f"ERROR: Validation report is stale: {args.report}")
            return 1
    else:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
