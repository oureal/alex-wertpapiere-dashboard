#!/usr/bin/env python3
"""Persist security value snapshots and embed top movers for day/week/month/total."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PORTFOLIO = ROOT / "data/generated/dry-run-portfolio.json"
PRICES = ROOT / "data/prices/latest.json"
HISTORY = ROOT / "data/history/security-history.json"
LEGACY_DIR = ROOT / "dashboard/history"

NAME_TO_ID = {
    "Berkshire Hathaway": "berkshire-hathaway-b",
    "Xetra Gold": "xetra-gold",
    "Allianz": "allianz",
    "Microsoft": "microsoft",
    "Eli Lilly": "eli-lilly",
    "Siemens": "siemens",
    "HSBC": "hsbc",
    "Apple": "apple",
    "Linde": "linde",
    "boerse.de-Aktienfonds": "boerse-de-aktienfonds",
    "Global Titans 50": "ishares-global-titans-50",
    "boerse.de-Technologiefonds": "boerse-de-technologiefonds",
    "Nvidia": "nvidia",
    "AMD": "amd",
    "MSCI World": "ishares-core-msci-world",
    "Alphabet": "alphabet-c",
    "Micron Technology": "micron-technology",
    "World Value": "ishares-msci-world-value-factor",
    "WisdomTree Physical Bitcoin": "wisdomtree-physical-bitcoin",
    "Marvell Technology": "marvell-technology",
    "TSMC": "tsmc-adr",
    "Broadcom": "broadcom",
    "Siemens Energy": "siemens-energy",
}
ID_TO_NAME = {v: k for k, v in NAME_TO_ID.items()}


def load_inline(path: Path) -> tuple[str, re.Match[str], dict]:
    text = path.read_text()
    match = re.search(r"const DATA=(\{.*?\});\n", text, flags=re.S)
    if not match:
        raise SystemExit(f"DATA object missing in {path}")
    return text, match, json.loads(match.group(1))


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%d.%m.%Y")


def load_existing() -> list[dict]:
    if HISTORY.exists():
        doc = json.loads(HISTORY.read_text())
        return list(doc.get("snapshots", []))
    return []


def legacy_snapshots() -> list[dict]:
    out = []
    if not LEGACY_DIR.exists():
        return out
    for path in sorted(LEGACY_DIR.glob("*.html")):
        try:
            _, _, data = load_inline(path)
        except Exception:
            continue
        date = str(data.get("meta", {}).get("asof", "")).strip()
        if not date:
            continue
        values = {}
        for row in data.get("assets", []):
            iid = NAME_TO_ID.get(row.get("name"))
            if iid:
                values[iid] = float(row.get("value", 0) or 0)
        if values:
            out.append({"date": date, "time": None, "values": values, "source": "legacy-dashboard"})
    return out


def current_time(prices: dict) -> tuple[str, str]:
    stamps = [x.get("fetched_at") for x in prices.get("prices", []) if x.get("fetched_at")]
    if stamps:
        newest = max(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
        local = newest.astimezone(ZoneInfo("Europe/Vienna"))
    else:
        local = datetime.now(ZoneInfo("Europe/Vienna"))
    return local.strftime("%d.%m.%Y"), local.strftime("%H:%M")


def current_values(portfolio: dict) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in portfolio.get("positions", []):
        iid = row.get("instrument_id")
        if iid and iid != "cash":
            values[iid] = values.get(iid, 0.0) + float(row.get("market_value_eur", 0) or 0)
    return values


def normalize(points: list[dict]) -> list[dict]:
    by_date = {}
    for p in points:
        date = p.get("date")
        if not date:
            continue
        try:
            parse_date(date)
        except ValueError:
            continue
        old = by_date.get(date)
        # Prefer the newer/current snapshot for duplicate dates.
        if old is None or p.get("source") == "current":
            by_date[date] = p
    return [by_date[d] for d in sorted(by_date, key=parse_date)]


def baseline_for(period: str, snaps: list[dict], current: dict) -> dict | None:
    cur_dt = parse_date(current["date"])
    previous = [s for s in snaps if parse_date(s["date"]) < cur_dt]
    if period == "day":
        return previous[-1] if previous else None
    if period == "week":
        same = [s for s in snaps if parse_date(s["date"]).isocalendar()[:2] == cur_dt.isocalendar()[:2]]
        return same[0] if same and same[0]["date"] != current["date"] else (previous[-1] if previous else None)
    if period == "month":
        same = [s for s in snaps if (parse_date(s["date"]).year, parse_date(s["date"]).month) == (cur_dt.year, cur_dt.month)]
        return same[0] if same and same[0]["date"] != current["date"] else (previous[-1] if previous else None)
    return snaps[0] if snaps and snaps[0]["date"] != current["date"] else None


def ranking(base: dict | None, current: dict) -> dict:
    if not base:
        return {"from": None, "to": current["date"], "gainers": [], "losers": []}
    rows = []
    for iid, now in current["values"].items():
        before = float(base.get("values", {}).get(iid, 0) or 0)
        now = float(now or 0)
        if before <= 0 or now <= 0:
            continue
        delta = now - before
        pct = delta / before
        rows.append({"id": iid, "name": ID_TO_NAME.get(iid, iid), "pct": pct, "value": delta, "current": now, "base": before})
    gainers = sorted((r for r in rows if r["value"] > 0), key=lambda r: (r["pct"], r["value"]), reverse=True)[:3]
    losers = sorted((r for r in rows if r["value"] < 0), key=lambda r: (r["pct"], r["value"]))[:3]
    return {"from": base["date"], "to": current["date"], "gainers": gainers, "losers": losers}


def main() -> int:
    portfolio = json.loads(PORTFOLIO.read_text())
    prices = json.loads(PRICES.read_text())
    date, time = current_time(prices)
    current = {"date": date, "time": time, "values": current_values(portfolio), "source": "current"}

    snaps = normalize(legacy_snapshots() + load_existing() + [current])
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps({"schema_version": 1, "snapshots": snaps}, ensure_ascii=False, indent=2) + "\n")

    periods = {}
    for key in ("day", "week", "month", "total"):
        periods[key] = ranking(baseline_for(key, snaps, current), current)

    text, match, data = load_inline(INDEX)
    data["movers"] = {"asof": date, "time": time, "periods": periods}
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    INDEX.write_text(text[:match.start(1)] + encoded + text[match.end(1):])
    print(f"Stored {len(snaps)} security snapshots and embedded movers for {date} {time}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
