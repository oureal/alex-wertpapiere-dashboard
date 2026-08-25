#!/usr/bin/env python3
"""Reconstruct weekly combined Depot 1 + Depot 2 history from Onvista transactions."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
TX_FILES=[ROOT/'data/transactions-depot1.json',ROOT/'data/transactions.json']
HISTORY=ROOT/'data/history/portfolio-history.json'
RECONSTRUCTED=ROOT/'data/history/reconstructed-history.json'
VALIDATED_START=date(2026,7,17)
MARKET={
'US0846707026':('BRK-B','USD'),'DE0008404005':('ALV.DE','EUR'),'US0079031078':('AMD','USD'),'US02079K1079':('GOOG','USD'),'US67066G1040':('NVDA','USD'),'US5951121038':('MU','USD'),'US8740391003':('TSM','USD'),'US11135F1012':('AVGO','USD'),'US5738741041':('MRVL','USD'),'FR0000121014':('MC.PA','EUR'),'DE0007037129':('RWE.DE','EUR'),'DE0007100000':('MBG.DE','EUR'),'CH0038863350':('NESN.SW','CHF'),'US61174X1090':('MNST','USD'),'US2441991054':('DE','USD'),'US53814L1089':('LTHM','USD'),'US35834F1049':('FREY','USD'),'DE0006289382':('EXI2.DE','EUR'),'IE00BP3QZB59':('IS3S.DE','EUR'),'GB00BJYDH287':('WBIT.DE','EUR'),'IE00B1XNHC34':('IQQH.DE','EUR'),'IE00B4L5Y983':('EUNL.DE','EUR'),'IE00BF4RFH31':('IUSN.DE','EUR'),'DE000A0F5UH1':('ISPA.DE','EUR'),'DE000ENER6Y0':('ENR.DE','EUR'),'DE000ENERGY0':('ENR.DE','EUR'),
'US5949181045':('MSFT','USD'),'DE0007236101':('SIE.DE','EUR'),'US5324571083':('LLY','USD'),'US0378331005':('AAPL','USD'),'IE000S9YS762':('LIN','USD'),'GB0005405286':('HSBA.L','GBP'),'DE000A0S9GB0':('4GLD.DE','EUR'),'US7427181091':('PG','USD'),'US88160R1014':('TSLA','USD'),'US8334451098':('SNOW','USD'),'US81762P1021':('NOW','USD'),'US70450Y1038':('PYPL','USD'),'DE000BASF111':('BAS.DE','EUR'),'FR0000125486':('DG.PA','EUR'),'AT0000746409':('VER.VI','EUR'),'DE0005552004':('DHL.DE','EUR'),'DE0007664039':('VOW3.DE','EUR'),'US62914V1061':('NIO','USD')}

def iso(v): return datetime.strptime(v,'%Y-%m-%d').date()
def de(v): return v.strftime('%d.%m.%Y')
def deparse(v): return datetime.strptime(v,'%d.%m.%Y').date()
def weekly(start,end):
    out=[start]; d=start
    while d.weekday()!=4:d+=timedelta(days=1)
    while d<end:
        if d>start:out.append(d)
        d+=timedelta(days=7)
    last=end-timedelta(days=1)
    if last>=start and last not in out:out.append(last)
    return sorted(set(out))
def series(symbol,start,end):
    try:
        f=yf.Ticker(symbol).history(start=start.isoformat(),end=(end+timedelta(days=1)).isoformat(),auto_adjust=False,actions=False)
        return {i.date():float(v) for i,v in f['Close'].items() if float(v)>0} if f is not None and not f.empty and 'Close' in f else {}
    except Exception as e:
        print(f'Historical quote fallback for {symbol}: {e}'); return {}
def prev(s,day):
    ds=[d for d in s if d<=day]; return s[max(ds)] if ds else None
def implied(tx):
    q=float(tx.get('quantity') or 0); a=abs(float(tx.get('amount_eur') or 0)); fee=float(tx.get('fees_eur') or 0)
    return (a-fee)/q if q>0 and a>fee else None
def load_transactions():
    alltx=[]
    for path in TX_FILES:
        doc=json.loads(path.read_text(encoding='utf-8'))
        depot=doc.get('depot') or ('depot1' if 'depot1' in path.name else 'depot2')
        for r in doc.get('transactions',[]):
            row=dict(r); row.setdefault('depot',depot); alltx.append(row)
    return sorted(alltx,key=lambda r:(iso(r['date']),r.get('depot',''),r.get('type','')))
def reconstruct():
    txs=load_transactions(); start=iso(txs[0]['date']); points=weekly(start,VALIDATED_START)
    isins=sorted({r.get('isin') for r in txs if r.get('isin')}); market={i:series(MARKET[i][0],start,VALIDATED_START) for i in isins if i in MARKET}
    currencies={MARKET[i][1] for i in isins if i in MARKET and MARKET[i][1]!='EUR'}; fx={c:series(f'{c}EUR=X',start,VALIDATED_START) for c in currencies}
    holdings=defaultdict(float); fallback={}; cash=0.0; contrib=0.0; cursor=0; rows=[]; yahoo=0; fb=0
    for point in points:
        while cursor<len(txs) and iso(txs[cursor]['date'])<=point:
            t=txs[cursor]; cash+=float(t.get('amount_eur') or 0)
            if t.get('type') in {'Einzahlung','Auszahlung'}: contrib+=float(t.get('amount_eur') or 0)
            i=t.get('isin'); q=float(t.get('quantity') or 0)
            if i and q:
                holdings[i]+=q if t.get('type')=='Kauf' else -q if t.get('type')=='Verkauf' else 0
                p=implied(t)
                if p and p>0:fallback[i]=p
            cursor+=1
        securities=0.0; unresolved=0
        for i,q in holdings.items():
            if abs(q)<1e-9:continue
            unit=None
            if i in MARKET:
                raw=prev(market.get(i,{}),point)
                if raw is not None:
                    cur=MARKET[i][1]
                    if cur=='EUR':unit=raw
                    else:
                        rate=prev(fx.get(cur,{}),point)
                        if rate:unit=raw*rate
                    if unit is not None:yahoo+=1
            if unit is None:
                unit=fallback.get(i)
                if unit is not None:fb+=1
            if unit is None:unresolved+=1;continue
            securities+=q*unit
        value=cash+securities; gain=value-contrib
        rows.append({'date':de(point),'value':round(value,2),'net_contributions':round(contrib,2),'gain':round(gain,2),'simple_return':round(gain/contrib,8) if contrib>0 else None,'reconstructed':True,'unresolved_positions':unresolved})
    meta={'schema_version':3,'method':'weekly combined Depot 1 + Depot 2 transaction-ledger reconstruction','start':start.isoformat(),'end_exclusive':VALIDATED_START.isoformat(),'points':len(rows),'transactions':len(txs),'depot1_transactions':199,'depot2_transactions':240,'market_mapped_isins':len([i for i in isins if i in MARKET]),'all_isins':len(isins),'yahoo_valuation_uses':yahoo,'fallback_valuation_uses':fb,'warning':'Historical values are reconstructed estimates and are not broker-verified statements.'}
    return rows,meta
def merge(rows,meta):
    old=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else {'history':[]}; validated=[]; lastc=rows[-1]['net_contributions']
    for r in old.get('history',[]):
        try:
            if deparse(r['date'])>=VALIDATED_START:
                v=float(r['value']); g=v-lastc; validated.append({'date':r['date'],'value':v,'net_contributions':lastc,'gain':round(g,2),'simple_return':round(g/lastc,8) if lastc>0 else None,'validated':True})
        except Exception:pass
    combined=[{k:v for k,v in r.items() if k not in {'reconstructed','unresolved_positions'}} for r in rows]+validated
    HISTORY.write_text(json.dumps({'schema_version':4,'description':'Combined Depot 1 + Depot 2 cash-flow-aware history; reconstructed before 17.07.2026 and validated thereafter.','reconstruction':meta,'history':combined},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    RECONSTRUCTED.write_text(json.dumps({'schema_version':3,'meta':meta,'history':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Reconstructed {len(rows)} combined historical points from {meta['transactions']} transactions; retained {len(validated)} validated points.")
def main():
    rows,meta=reconstruct()
    if not rows or rows[0]['date']!='02.06.2020':raise ValueError('Combined history does not begin at Depot 1 start 02.06.2020')
    if meta['transactions']!=439:raise ValueError(f"Expected 439 transactions, got {meta['transactions']}")
    merge(rows,meta)
if __name__=='__main__':main()
