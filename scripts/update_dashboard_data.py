#!/usr/bin/env python3
"""Refresh the inline dashboard DATA object from validated portfolio output."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
        return datetime.now().strftime("%d.%m.%Y")
    newest = max(datetime.fromisoformat(stamp.replace("Z", "+00:00")) for stamp in stamps)
    return newest.strftime("%d.%m.%Y")


def _previous_total(history: list[dict], asof: str, fallback: float) -> float:
    for point in reversed(history):
        if point.get("date") != asof:
            return float(point["value"])
    return float(fallback)


def refresh_document(index_text: str, portfolio: dict, prices: dict) -> str:
    match = re.search(r"const DATA=(\{.*?\});\n", index_text, flags=re.S)
    if not match:
        raise ValueError("Could not find inline dashboard DATA object")
    data = json.loads(match.group(1))
    total = float(portfolio["total"])
    direct_total = float(portfolio["direct_total"])
    resolved = float(portfolio["resolved"])
    unresolved = float(portfolio["unresolved"])
    asof = _asof(prices)

    history = list(data.get("history", []))
    previous_total = _previous_total(history, asof, data.get("meta", {}).get("previousTotal", data.get("meta", {}).get("total", total)))
    if history and history[-1].get("date") == asof:
        history[-1]["value"] = total
    else:
        history.append({"date": asof, "value": total})

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
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=ROOT / "index.html")
    parser.add_argument("--portfolio", type=Path, default=ROOT / "data/generated/dry-run-portfolio.json")
    parser.add_argument("--prices", type=Path, default=ROOT / "data/prices/latest.json")
    args = parser.parse_args()
    portfolio = json.loads(args.portfolio.read_text())
    prices = json.loads(args.prices.read_text())
    args.index.write_text(refresh_document(args.index.read_text(), portfolio, prices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
