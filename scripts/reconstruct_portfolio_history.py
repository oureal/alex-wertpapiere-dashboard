#!/usr/bin/env python3
"""Reconstruct weekly portfolio values from the Onvista transaction ledger.

The reconstruction is intentionally separate from the validated live portfolio path.
It values historical holdings with free Yahoo history where available and falls back
to the last observed transaction price in EUR for instruments without a usable free
history. Existing validated portfolio-history points from VALIDATED_START onward are
never replaced.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS = ROOT / "data/transactions.json"
HISTORY = ROOT / "data/history/portfolio-history.json"
RECONSTRUCTED = ROOT / "data/history/reconstructed-history.json"
VALIDATED_START = date(2026, 7, 17)

# Yahoo symbols are used only for historical valuation. Values are converted to EUR.
# Instruments omitted here remain fully supported via transaction-price fallback.
MARKET = {
    "US0846707026": ("BRK-B", "USD"),
    "DE0008404005": ("ALV.DE", "EUR"),
    "US0079031078": ("AMD", "USD"),
    "US02079K1079": ("GOOG", "USD"),
    "US67066G1040": ("NVDA", "USD"),
    "US5951121038": ("MU", "USD"),
    "US8740391003": ("TSM", "USD"),
    "US11135F1012": ("AVGO", "USD"),
    "US5738741041": ("MRVL", "USD"),
    "FR0000121014": ("MC.PA", "EUR"),
    "DE0007037129": ("RWE.DE", "EUR"),
    "DE0007100000": ("MBG.DE", "EUR"),
    "CH0038863350": ("NESN.SW", "CHF"),
    "US61174X1090": ("MNST", "USD"),
    "US2441991054": ("DE", "USD"),
    "US53814L1089": ("LTHM", "USD"),
    "US35834F1049": ("FREY", "USD"),
    "DE0006289382": ("EXI2.DE", "EUR"),
    "IE00BP3QZB59": ("IS3S.DE", "EUR"),
    "GB00BJYDH287": ("WBIT.DE", "EUR"),
    "IE00B1XNHC34": ("IQQH.DE", "EUR"),
    "IE00B4L5Y983": ("EUNL.DE", "EUR"),
    "IE00BF4RFH31": ("IUSN.DE", "EUR"),
    "DE000A0F5UH1": ("ISPA.DE", "EUR"),
    "DE000ENER6Y0": ("ENR.DE", "EUR"),
    "DE000ENERGY0": ("ENR.DE", "EUR"),
}


def parse_iso(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_de(value: str) -> date:
    return datetime.strptime(value, "%d.%m.%Y").date()


def de(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def weekly_dates(start: date, end_exclusive: date) -> list[date]:
    points = [start]
    current = start
    # Friday closes provide a compact long-term history without bloating the static page.
    while current.weekday() != 4:
        current += timedelta(days=1)
    while current < end_exclusive:
        if current > start:
            points.append(current)
        current += timedelta(days=7)
    last = end_exclusive - timedelta(days=1)
    if last >= start and last not in points:
        points.append(last)
    return sorted(set(points))


def history_series(symbol: str, start: date, end: date) -> dict[date, float]:
    try:
        frame = yf.Ticker(symbol).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            actions=False,
        )
        if frame is None or frame.empty or "Close" not in frame:
            return {}
        result = {}
        for idx, value in frame["Close"].items():
            try:
                price = float(value)
                if price > 0:
                    result[idx.date()] = price
            except (TypeError, ValueError):
                pass
        return result
    except Exception as exc:  # Free market data must never break production history.
        print(f"Historical quote fallback for {symbol}: {exc}")
        return {}


def previous(series: dict[date, float], when: date) -> float | None:
    candidates = [d for d in series if d <= when]
    return series[max(candidates)] if candidates else None


def implied_eur_price(tx: dict) -> float | None:
    qty = float(tx.get("quantity") or 0)
    amount = abs(float(tx.get("amount_eur") or 0))
    fees = float(tx.get("fees_eur") or 0)
    if qty <= 0 or amount <= 0:
        return None
    gross = amount - fees
    return gross / qty if gross > 0 else None


def reconstruct() -> tuple[list[dict], dict]:
    doc = json.loads(TRANSACTIONS.read_text(encoding="utf-8"))
    txs = sorted(doc.get("transactions", []), key=lambda row: (parse_iso(row["date"]), row.get("type", "")))
    if not txs:
        raise ValueError("No transactions available for historical reconstruction")
    start = parse_iso(txs[0]["date"])
    points = weekly_dates(start, VALIDATED_START)

    isins = sorted({row.get("isin") for row in txs if row.get("isin")})
    market = {}
    currencies = {currency for isin, (_, currency) in MARKET.items() if isin in isins and currency != "EUR"}
    for isin in isins:
        mapping = MARKET.get(isin)
        if mapping:
            market[isin] = history_series(mapping[0], start, VALIDATED_START)

    fx = {"EUR": {}}
    for currency in currencies:
        fx[currency] = history_series(f"{currency}EUR=X", start, VALIDATED_START)

    holdings: dict[str, float] = defaultdict(float)
    fallback_eur: dict[str, float] = {}
    cash = 0.0
    cursor = 0
    rows = []
    yahoo_valuations = 0
    fallback_valuations = 0

    for point in points:
        while cursor < len(txs) and parse_iso(txs[cursor]["date"]) <= point:
            tx = txs[cursor]
            cash += float(tx.get("amount_eur") or 0)
            kind = tx.get("type")
            isin = tx.get("isin")
            qty = float(tx.get("quantity") or 0)
            if isin and qty:
                if kind == "Kauf":
                    holdings[isin] += qty
                elif kind == "Verkauf":
                    holdings[isin] -= qty
                implied = implied_eur_price(tx)
                if implied and implied > 0:
                    fallback_eur[isin] = implied
            cursor += 1

        securities = 0.0
        unresolved = []
        for isin, qty in holdings.items():
            if abs(qty) < 1e-9:
                continue
            unit_eur = None
            mapping = MARKET.get(isin)
            if mapping:
                raw = previous(market.get(isin, {}), point)
                if raw is not None:
                    currency = mapping[1]
                    if currency == "EUR":
                        unit_eur = raw
                    else:
                        rate = previous(fx.get(currency, {}), point)
                        if rate is not None and rate > 0:
                            unit_eur = raw * rate
                    if unit_eur is not None:
                        yahoo_valuations += 1
            if unit_eur is None:
                unit_eur = fallback_eur.get(isin)
                if unit_eur is not None:
                    fallback_valuations += 1
            if unit_eur is None:
                unresolved.append(isin)
                continue
            securities += qty * unit_eur

        rows.append({
            "date": de(point),
            "value": round(cash + securities, 2),
            "reconstructed": True,
            "unresolved_positions": len(unresolved),
        })

    meta = {
        "schema_version": 1,
        "method": "weekly transaction-ledger reconstruction with Yahoo historical close where available and last transaction EUR price fallback",
        "start": start.isoformat(),
        "end_exclusive": VALIDATED_START.isoformat(),
        "points": len(rows),
        "transactions": len(txs),
        "market_mapped_isins": len([isin for isin in isins if isin in MARKET]),
        "all_isins": len(isins),
        "yahoo_valuation_uses": yahoo_valuations,
        "fallback_valuation_uses": fallback_valuations,
        "warning": "Reconstructed values are estimates and are not broker-verified historical account statements.",
    }
    return rows, meta


def merge(rows: list[dict], meta: dict) -> None:
    current = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"history": []}
    validated = []
    for row in current.get("history", []):
        try:
            if parse_de(row["date"]) >= VALIDATED_START:
                validated.append({"date": row["date"], "value": float(row["value"])})
        except (KeyError, ValueError, TypeError):
            pass
    combined = [{"date": row["date"], "value": row["value"]} for row in rows] + validated
    HISTORY.write_text(json.dumps({
        "schema_version": 2,
        "description": "Reconstructed weekly portfolio history before 17.07.2026 plus validated dashboard values from 17.07.2026 onward.",
        "reconstruction": meta,
        "history": combined,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RECONSTRUCTED.write_text(json.dumps({"schema_version": 1, "meta": meta, "history": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reconstructed {len(rows)} historical points; retained {len(validated)} validated points.")


def main() -> int:
    rows, meta = reconstruct()
    if not rows or rows[0]["date"] != "16.08.2022":
        raise ValueError("Historical reconstruction does not start at documented depot beginning 16.08.2022")
    merge(rows, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
