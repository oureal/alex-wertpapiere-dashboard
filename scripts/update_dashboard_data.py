#!/usr/bin/env python3
"""Refresh the dashboard from validated portfolio output and persist the daily total history."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = ROOT / "data/history/portfolio-history.json"
SOURCE_FIELDS = {
    "boerse-de-aktienfonds": ("boerse", "boerse.de-Aktienfonds"),
    "ishares-global-titans-50": ("titans", "Global Titans 50"),
    "boerse-de-technologiefonds": ("tech", "boerse.de-Technologiefonds"),
    "ishares-core-msci-world": ("world", "MSCI World"),
    "ishares-msci-world-value-factor": ("value", "World Value"),
}
ASSET_NAMES = {
    "berkshire-hathaway-b": "Berkshire Hathaway",
    "xetra-gold": "Xetra Gold",
    "allianz": "Allianz",
    "microsoft": "Microsoft",
    "eli-lilly": "Eli Lilly",
    "siemens": "Siemens",
    "hsbc": "HSBC",
    "apple": "Apple",
    "linde": "Linde",
    "boerse-de-aktienfonds": "boerse.de-Aktienfonds",
    "ishares-global-titans-50": "Global Titans 50",
    "boerse-de-technologiefonds": "boerse.de-Technologiefonds",
    "nvidia": "Nvidia",
    "amd": "AMD",
    "ishares-core-msci-world": "MSCI World",
    "alphabet-c": "Alphabet",
    "micron-technology": "Micron Technology",
    "ishares-msci-world-value-factor": "World Value",
    "wisdomtree-physical-bitcoin": "WisdomTree Physical Bitcoin",
    "marvell-technology": "Marvell Technology",
    "tsmc-adr": "TSMC",
    "broadcom": "Broadcom",
    "siemens-energy": "Siemens Energy",
    "cash": "Bargeld",
}


def _asof(prices: dict) -> str:
    stamps = [item.get("fetched_at") for item in prices.get("prices", []) if item.get("fetched_at")]
    if not stamps:
        return datetime.now(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y")
    newest = max(datetime.fromisoformat(stamp.replace("Z", "+00:00")) for stamp in stamps)
    return newest.astimezone(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y")


def _update_notice(prices: dict) -> str:
    rows = prices.get("prices", [])
    stamps = [item.get("fetched_at") for item in rows if item.get("fetched_at")]
    if stamps:
        newest = max(datetime.fromisoformat(stamp.replace("Z", "+00:00")) for stamp in stamps)
        local = newest.astimezone(ZoneInfo("Europe/Vienna"))
        when = local.strftime("%d.%m.%Y, %H:%M Uhr")
    else:
        when = datetime.now(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y, %H:%M Uhr")

    total = len(rows)
    positive = sum(1 for item in rows if float(item.get("price", 0) or 0) > 0)
    fresh = sum(1 for item in rows if item.get("status") == "fresh")
    stale = sum(1 for item in rows if item.get("status") == "stale")
    fallback = sum(1 for item in rows if item.get("status") == "fallback")
    warning_count = len(prices.get("warnings", []))

    status_parts = [f"{positive}/{total} Kurse verfügbar", f"{fresh} frisch"]
    if stale or fallback:
        status_parts.append(f"{stale} veraltet · {fallback} fallback")
    else:
        status_parts.append("0 veraltet/fallback")
    status_parts.append("keine Warnungen" if warning_count == 0 else f"{warning_count} Warnung(en)")
    return "Letzte Kursaktualisierung: " + when + " · " + " · ".join(status_parts)


def _date_key(value: str) -> datetime:
    return datetime.strptime(value, "%d.%m.%Y")


def _normalize_history(points: list[dict]) -> list[dict]:
    by_date: dict[str, float] = {}
    for point in points:
        date = str(point.get("date", "")).strip()
        if not date:
            continue
        try:
            _date_key(date)
            value = float(point["value"])
        except (ValueError, TypeError, KeyError):
            continue
        by_date[date] = value
    return [{"date": date, "value": by_date[date]} for date in sorted(by_date, key=_date_key)]


def _load_inline_data(index_text: str) -> tuple[re.Match[str], dict]:
    match = re.search(r"const DATA=(\{.*?\});\n", index_text, flags=re.S)
    if not match:
        raise ValueError("Could not find inline dashboard DATA object")
    return match, json.loads(match.group(1))


def _load_history(history_path: Path, inline_history: list[dict]) -> list[dict]:
    if history_path.exists():
        doc = json.loads(history_path.read_text())
        if isinstance(doc, dict):
            points = doc.get("history", [])
        elif isinstance(doc, list):
            points = doc
        else:
            points = []
        return _normalize_history(points)
    return _normalize_history(inline_history)


def _store_history(history_path: Path, history: list[dict]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "description": "Daily validated total portfolio values used by the Gesamtdepotentwicklung dashboard.",
        "history": history,
    }
    history_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _previous_total(history: list[dict], asof: str, fallback: float) -> float:
    for point in reversed(history):
        if point.get("date") != asof:
            return float(point["value"])
    return float(fallback)


def refresh_document(index_text: str, portfolio: dict, prices: dict, history: list[dict]) -> str:
    match, data = _load_inline_data(index_text)
    total = float(portfolio["total"])
    direct_total = float(portfolio["direct_total"])
    resolved = float(portfolio["resolved"])
    unresolved = float(portfolio["unresolved"])
    asof = _asof(prices)

    history = _normalize_history(history)
    previous_total = _previous_total(
        history,
        asof,
        data.get("meta", {}).get("previousTotal", data.get("meta", {}).get("total", total)),
    )
    by_date = {point["date"]: float(point["value"]) for point in history}
    by_date[asof] = total
    history = _normalize_history([{"date": d, "value": v} for d, v in by_date.items()])

    meta = data.setdefault("meta", {})
    meta.update({
        "asof": asof,
        "total": total,
        "resolved": resolved,
        "unresolved": unresolved,
        "directTotal": direct_total,
        "indirectTotal": resolved - direct_total,
        "top10": float(portfolio["top10"]),
        "top20": float(portfolio["top20"]),
        "hhi": float(portfolio["hhi"]),
        "effectiveN": 10000.0 / float(portfolio["hhi"]) if float(portfolio["hhi"]) else 0.0,
        "previousTotal": previous_total,
        "change": total - previous_total,
        "changePct": (total - previous_total) / previous_total if previous_total else 0.0,
        "cash": float(portfolio["cash"]),
        "gold": float(portfolio["gold"]),
        "bitcoin": float(portfolio["bitcoin_etp"]),
        "unresolvedLookthroughTail": max(0.0, unresolved - float(portfolio["cash"]) - float(portfolio["gold"]) - float(portfolio["bitcoin_etp"])),
    })

    companies = []
    for rank, company in enumerate(portfolio["companies"], start=1):
        row = {
            "name": company["name"],
            "sector": company["sector"],
            "direct": float(company["direct"]),
            "boerse": 0.0,
            "titans": 0.0,
            "tech": 0.0,
            "world": 0.0,
            "value": 0.0,
            "indirect": float(company["indirect"]),
            "total": float(company["total"]),
            "share": float(company["total"]) / total if total else 0.0,
            "rank": rank,
        }
        contained = []
        if row["direct"] > 0:
            contained.append("Direkt")
        for source_id, amount in company.get("sources", {}).items():
            if source_id == "direct":
                continue
            field = SOURCE_FIELDS.get(source_id)
            if field:
                row[field[0]] = float(amount)
                if float(amount) > 0:
                    contained.append(field[1])
        row["contained"] = "; ".join(contained)
        companies.append(row)
    data["companies"] = companies
    data["sectors"] = [{"name": row["name"], "value": float(row["value"])} for row in portfolio["sectors"]]
    data["assets"] = [{"name": ASSET_NAMES.get(row["name"], row["name"]), "value": float(row["value"])} for row in portfolio["assets"]]
    data["history"] = history

    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    updated = index_text[:match.start(1)] + encoded + index_text[match.end(1):]
    updated = re.sub(r"<title>Depot Look-through Dashboard · [^<]+</title>", f"<title>Depot Look-through Dashboard · {asof}</title>", updated)
    updated = re.sub(r"Look-through Dashboard · Stand \d{2}\.\d{2}\.\d{4}", f"Look-through Dashboard · Stand {asof}", updated)
    updated = re.sub(r"Datenstand \d{2}\.\d{2}\.\d{4}", f"Datenstand {asof}", updated)
    updated = re.sub(r"Depotwerte \d{2}\.\d{2}\.\d{4}", f"Depotwerte {asof}", updated)
    notice = _update_notice(prices)
    updated = re.sub(
        r'<div class="notice small" style="margin-bottom:16px">.*?</div>',
        f'<div class="notice small" style="margin-bottom:16px">{notice}</div>',
        updated,
        count=1,
        flags=re.S,
    )
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=ROOT / "index.html")
    parser.add_argument("--portfolio", type=Path, default=ROOT / "data/generated/dry-run-portfolio.json")
    parser.add_argument("--prices", type=Path, default=ROOT / "data/prices/latest.json")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    args = parser.parse_args()

    index_text = args.index.read_text()
    _, inline_data = _load_inline_data(index_text)
    history = _load_history(args.history, inline_data.get("history", []))
    portfolio = json.loads(args.portfolio.read_text())
    prices = json.loads(args.prices.read_text())
    updated = refresh_document(index_text, portfolio, prices, history)
    _, updated_data = _load_inline_data(updated)
    _store_history(args.history, updated_data["history"])
    args.index.write_text(updated)
    print(f"Stored {len(updated_data['history'])} portfolio history points in {args.history}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
