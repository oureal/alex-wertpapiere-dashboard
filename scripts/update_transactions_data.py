#!/usr/bin/env python3
from pathlib import Path
import json, html, re
ROOT=Path(__file__).resolve().parents[1]; INDEX=ROOT/'index.html'; FILES=[ROOT/'data/transactions-depot1.json',ROOT/'data/transactions.json']
MANUAL_TX={"date":"2026-08-28","type":"Einzahlung","name":"Einzahlung","amount_eur":1000.0,"source":"User bestätigt","depot":"depot2"}
def eur(v):
    if v is None:return '–'
    s=f"{abs(float(v)):,.2f}".replace(',','X').replace('.',',').replace('X','.');sign='+' if float(v)>0 else '-' if float(v)<0 else '';return f'{sign}{s} €'
def num(v):
    if v is None:return '–'
    return f'{float(v):g}'.replace('.',',')
def dede(v): y,m,d=v.split('-');return f'{d}.{m}.{y}'
def load():
    out=[]
    for p in FILES:
        doc=json.loads(p.read_text(encoding='utf-8'));dep=doc.get('depot') or ('depot1' if 'depot1' in p.name else 'depot2')
        for x in doc.get('transactions',[]):
            r=dict(x);r.setdefault('depot',dep);out.append(r)
    if not any(x.get('date')==MANUAL_TX['date'] and x.get('type')=='Einzahlung' and x.get('depot')=='depot2' and abs(float(x.get('amount_eur') or 0)-1000.0)<1e-9 for x in out):
        out.append(dict(MANUAL_TX))
    return sorted(out,key=lambda x:x['date'],reverse=True)
def build(tx):
    count=len(tx);deposits=sum(float(x.get('amount_eur',0)) for x in tx if x.get('type')=='Einzahlung');withdrawals=sum(abs(float(x.get('amount_eur',0))) for x in tx if x.get('type')=='Auszahlung');fees=sum(float(x.get('fees_eur',0) or 0) for x in tx);orders=sum(1 for x in tx if x.get('type') in {'Kauf','Verkauf'});start=min(x['date'] for x in tx);end=max(x['date'] for x in tx)
    rows=[]
    for x in tx:
        typ=html.escape(str(x.get('type','')));name=html.escape(str(x.get('name','')));ids=[]
        if x.get('wkn'):ids.append('WKN '+html.escape(str(x['wkn'])))
        if x.get('isin'):ids.append('ISIN '+html.escape(str(x['isin'])))
        detail=' · '.join(ids);qty=num(x.get('quantity')) if x.get('quantity') is not None else '–';price='–'
        if x.get('price') is not None:price=f"{num(x.get('price'))} {html.escape(str(x.get('price_currency','EUR')))}"
        fees_cell=eur(x.get('fees_eur')) if x.get('fees_eur') not in (None,0,0.0) else '–';dep='Depot 1' if x.get('depot')=='depot1' else 'Depot 2'
        name_html=f'<b>{name}</b>'+ (f'<div class="muted small">{detail}</div>' if detail else '')
        rows.append(f'<tr><td>{dede(x["date"])}</td><td>{dep}</td><td>{typ}</td><td>{name_html}</td><td>{qty}</td><td>{price}</td><td>{fees_cell}</td><td>{eur(x.get("amount_eur"))}</td></tr>')
    return f'''<!-- TRANSACTIONS_START -->
<section id="transactions" class="page">
 <div class="header"><div><h1>Transaktionen</h1></div><div class="badge">{count} Vorgänge</div></div>
 <div class="grid kpis">
  <div class="card kpi"><div class="label">Zeitraum</div><div class="value" style="font-size:18px">{dede(start)} – {dede(end)}</div><div class="note">Depot 1 + Depot 2</div></div>
  <div class="card kpi"><div class="label">Käufe & Verkäufe</div><div class="value">{orders}</div><div class="note">Wertpapiertransaktionen</div></div>
  <div class="card kpi"><div class="label">Einzahlungen</div><div class="value">{eur(deposits)}</div><div class="note">dokumentierte Geldzuflüsse</div></div>
  <div class="card kpi"><div class="label">Spesen</div><div class="value">{eur(-fees)}</div><div class="note">erfasste Orderkosten</div></div>
 </div>
 <div class="notice small" style="margin-bottom:16px">Historische Onvista-Transaktionen aus Depot 1 und Depot 2. Auszahlungen gesamt: {eur(-withdrawals)}.</div>
 <div class="card"><div class="table-wrap" style="max-height:70vh"><table><thead><tr><th>Datum</th><th>Depot</th><th>Typ</th><th>Bezeichnung</th><th>Stück</th><th>Kurs</th><th>Spesen</th><th>Betrag</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>
</section>
<!-- TRANSACTIONS_END -->'''
def main():
    tx=load()
    if len(tx)!=440:raise SystemExit(f'Expected 440 effective transactions, got {len(tx)}')
    text=INDEX.read_text();section=build(tx);pat=r'<!-- TRANSACTIONS_START -->.*?<!-- TRANSACTIONS_END -->'
    if not re.search(pat,text,flags=re.S):raise SystemExit('Transactions section not found')
    INDEX.write_text(re.sub(pat,section,text,count=1,flags=re.S));print(f'Rendered {len(tx)} transactions from both depots.')
if __name__=='__main__':main()
