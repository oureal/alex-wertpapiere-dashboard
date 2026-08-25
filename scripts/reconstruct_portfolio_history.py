#!/usr/bin/env python3
"""Reconstruct weekly portfolio values and cash-flow-aware performance from transactions."""
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

MARKET = {
    "US0846707026": ("BRK-B", "USD"), "DE0008404005": ("ALV.DE", "EUR"),
    "US0079031078": ("AMD", "USD"), "US02079K1079": ("GOOG", "USD"),
    "US67066G1040": ("NVDA", "USD"), "US5951121038": ("MU", "USD"),
    "US8740391003": ("TSM", "USD"), "US11135F1012": ("AVGO", "USD"),
    "US5738741041": ("MRVL", "USD"), "FR0000121014": ("MC.PA", "EUR"),
    "DE0007037129": ("RWE.DE", "EUR"), "DE0007100000": ("MBG.DE", "EUR"),
    "CH0038863350": ("NESN.SW", "CHF"), "US61174X1090": ("MNST", "USD"),
    "US2441991054": ("DE", "USD"), "US53814L1089": ("LTHM", "USD"),
    "US35834F1049": ("FREY", "USD"), "DE0006289382": ("EXI2.DE", "EUR"),
    "IE00BP3QZB59": ("IS3S.DE", "EUR"), "GB00BJYDH287": ("WBIT.DE", "EUR"),
    "IE00B1XNHC34": ("IQQH.DE", "EUR"), "IE00B4L5Y983": ("EUNL.DE", "EUR"),
    "IE00BF4RFH31": ("IUSN.DE", "EUR"), "DE000A0F5UH1": ("ISPA.DE", "EUR"),
    "DE000ENER6Y0": ("ENR.DE", "EUR"), "DE000ENERGY0": ("ENR.DE", "EUR"),
}


def parse_iso(v): return datetime.strptime(v, "%Y-%m-%d").date()
def parse_de(v): return datetime.strptime(v, "%d.%m.%Y").date()
def de(v): return v.strftime("%d.%m.%Y")

def weekly_dates(start, end_exclusive):
    points=[start]; current=start
    while current.weekday()!=4: current+=timedelta(days=1)
    while current<end_exclusive:
        if current>start: points.append(current)
        current+=timedelta(days=7)
    last=end_exclusive-timedelta(days=1)
    if last>=start and last not in points: points.append(last)
    return sorted(set(points))

def history_series(symbol,start,end):
    try:
        frame=yf.Ticker(symbol).history(start=start.isoformat(),end=(end+timedelta(days=1)).isoformat(),auto_adjust=False,actions=False)
        if frame is None or frame.empty or "Close" not in frame: return {}
        result={}
        for idx,value in frame["Close"].items():
            try:
                price=float(value)
                if price>0: result[idx.date()]=price
            except (TypeError,ValueError): pass
        return result
    except Exception as exc:
        print(f"Historical quote fallback for {symbol}: {exc}"); return {}

def previous(series,when):
    candidates=[d for d in series if d<=when]
    return series[max(candidates)] if candidates else None

def implied_eur_price(tx):
    qty=float(tx.get("quantity") or 0); amount=abs(float(tx.get("amount_eur") or 0)); fees=float(tx.get("fees_eur") or 0)
    if qty<=0 or amount<=0: return None
    gross=amount-fees
    return gross/qty if gross>0 else None

def is_external_cashflow(tx):
    return tx.get("type") in {"Einzahlung","Auszahlung"}

def reconstruct():
    doc=json.loads(TRANSACTIONS.read_text(encoding="utf-8"))
    txs=sorted(doc.get("transactions",[]),key=lambda r:(parse_iso(r["date"]),r.get("type","")))
    if not txs: raise ValueError("No transactions available for historical reconstruction")
    start=parse_iso(txs[0]["date"]); points=weekly_dates(start,VALIDATED_START)
    isins=sorted({r.get("isin") for r in txs if r.get("isin")}); market={}
    currencies={c for isin,(_,c) in MARKET.items() if isin in isins and c!="EUR"}
    for isin in isins:
        if isin in MARKET: market[isin]=history_series(MARKET[isin][0],start,VALIDATED_START)
    fx={"EUR":{}}
    for currency in currencies: fx[currency]=history_series(f"{currency}EUR=X",start,VALIDATED_START)
    holdings=defaultdict(float); fallback_eur={}; cash=0.0; net_contributions=0.0; cursor=0; rows=[]; yahoo_valuations=0; fallback_valuations=0
    for point in points:
        while cursor<len(txs) and parse_iso(txs[cursor]["date"])<=point:
            tx=txs[cursor]; amount=float(tx.get("amount_eur") or 0); cash+=amount
            if is_external_cashflow(tx): net_contributions+=amount
            kind=tx.get("type"); isin=tx.get("isin"); qty=float(tx.get("quantity") or 0)
            if isin and qty:
                if kind=="Kauf": holdings[isin]+=qty
                elif kind=="Verkauf": holdings[isin]-=qty
                implied=implied_eur_price(tx)
                if implied and implied>0: fallback_eur[isin]=implied
            cursor+=1
        securities=0.0; unresolved=[]
        for isin,qty in holdings.items():
            if abs(qty)<1e-9: continue
            unit_eur=None; mapping=MARKET.get(isin)
            if mapping:
                raw=previous(market.get(isin,{}),point)
                if raw is not None:
                    currency=mapping[1]
                    if currency=="EUR": unit_eur=raw
                    else:
                        rate=previous(fx.get(currency,{}),point)
                        if rate is not None and rate>0: unit_eur=raw*rate
                    if unit_eur is not None: yahoo_valuations+=1
            if unit_eur is None:
                unit_eur=fallback_eur.get(isin)
                if unit_eur is not None: fallback_valuations+=1
            if unit_eur is None: unresolved.append(isin); continue
            securities+=qty*unit_eur
        value=cash+securities; gain=value-net_contributions
        rows.append({"date":de(point),"value":round(value,2),"net_contributions":round(net_contributions,2),"gain":round(gain,2),"simple_return":round(gain/net_contributions,8) if net_contributions>0 else None,"reconstructed":True,"unresolved_positions":len(unresolved)})
    meta={"schema_version":2,"method":"weekly transaction-ledger reconstruction with external cashflows separated from portfolio valuation","start":start.isoformat(),"end_exclusive":VALIDATED_START.isoformat(),"points":len(rows),"transactions":len(txs),"market_mapped_isins":len([i for i in isins if i in MARKET]),"all_isins":len(isins),"yahoo_valuation_uses":yahoo_valuations,"fallback_valuation_uses":fallback_valuations,"warning":"Reconstructed values are estimates and are not broker-verified historical account statements."}
    return rows,meta

def merge(rows,meta):
    current=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"history":[]}
    validated=[]; last_contrib=rows[-1]["net_contributions"] if rows else 0.0
    for row in current.get("history",[]):
        try:
            if parse_de(row["date"])>=VALIDATED_START:
                value=float(row["value"]); gain=value-last_contrib
                validated.append({"date":row["date"],"value":value,"net_contributions":last_contrib,"gain":round(gain,2),"simple_return":round(gain/last_contrib,8) if last_contrib>0 else None,"validated":True})
        except (KeyError,ValueError,TypeError): pass
    combined=[{k:v for k,v in row.items() if k not in {"reconstructed","unresolved_positions"}} for row in rows]+validated
    HISTORY.write_text(json.dumps({"schema_version":3,"description":"Cash-flow-aware reconstructed history before 17.07.2026 plus validated dashboard values thereafter.","reconstruction":meta,"history":combined},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    RECONSTRUCTED.write_text(json.dumps({"schema_version":2,"meta":meta,"history":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Reconstructed {len(rows)} historical points; retained {len(validated)} validated points.")

def main():
    rows,meta=reconstruct()
    if not rows or rows[0]["date"]!="16.08.2022": raise ValueError("Historical reconstruction does not start at documented depot beginning 16.08.2022")
    merge(rows,meta); return 0

if __name__=="__main__": raise SystemExit(main())