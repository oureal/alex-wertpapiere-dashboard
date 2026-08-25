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
SOURCE_FIELDS = {"boerse-de-aktienfonds": ("boerse", "boerse.de-Aktienfonds"), "ishares-global-titans-50": ("titans", "Global Titans 50"), "boerse-de-technologiefonds": ("tech", "boerse.de-Technologiefonds"), "ishares-core-msci-world": ("world", "MSCI World"), "ishares-msci-world-value-factor": ("value", "World Value")}
ASSET_NAMES = {"berkshire-hathaway-b":"Berkshire Hathaway","xetra-gold":"Xetra Gold","allianz":"Allianz","microsoft":"Microsoft","eli-lilly":"Eli Lilly","siemens":"Siemens","hsbc":"HSBC","apple":"Apple","linde":"Linde","boerse-de-aktienfonds":"boerse.de-Aktienfonds","ishares-global-titans-50":"Global Titans 50","boerse-de-technologiefonds":"boerse.de-Technologiefonds","nvidia":"Nvidia","amd":"AMD","ishares-core-msci-world":"MSCI World","alphabet-c":"Alphabet","micron-technology":"Micron Technology","ishares-msci-world-value-factor":"World Value","wisdomtree-physical-bitcoin":"WisdomTree Physical Bitcoin","marvell-technology":"Marvell Technology","tsmc-adr":"TSMC","broadcom":"Broadcom","siemens-energy":"Siemens Energy","cash":"Bargeld"}

def _asof(prices):
    stamps=[i.get("fetched_at") for i in prices.get("prices",[]) if i.get("fetched_at")]
    if not stamps:return datetime.now(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y")
    newest=max(datetime.fromisoformat(s.replace("Z","+00:00")) for s in stamps)
    return newest.astimezone(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y")

def _update_notice(prices):
    rows=prices.get("prices",[]); stamps=[i.get("fetched_at") for i in rows if i.get("fetched_at")]
    newest=max((datetime.fromisoformat(s.replace("Z","+00:00")) for s in stamps),default=datetime.now(ZoneInfo("Europe/Vienna")))
    when=newest.astimezone(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y, %H:%M Uhr")
    positive=sum(float(i.get("price",0) or 0)>0 for i in rows); fresh=sum(i.get("status")=="fresh" for i in rows); stale=sum(i.get("status")=="stale" for i in rows); fallback=sum(i.get("status")=="fallback" for i in rows); warnings=len(prices.get("warnings",[]))
    return f"Letzte Kursaktualisierung: {when} · {positive}/{len(rows)} Kurse verfügbar · {fresh} frisch · {stale} veraltet · {fallback} fallback · " + ("keine Warnungen" if not warnings else f"{warnings} Warnung(en)")

def _date_key(v):return datetime.strptime(v,"%d.%m.%Y")
def _normalize_history(points):
    by={}
    for p in points:
        try:_date_key(str(p.get("date",""))); by[str(p["date"])]=float(p["value"])
        except (ValueError,TypeError,KeyError):pass
    return [{"date":d,"value":by[d]} for d in sorted(by,key=_date_key)]
def _load_inline_data(text):
    m=re.search(r"const DATA=(\{.*?\});\n",text,flags=re.S)
    if not m:raise ValueError("Could not find inline dashboard DATA object")
    return m,json.loads(m.group(1))
def _load_history(path,inline):
    if path.exists():
        doc=json.loads(path.read_text()); return _normalize_history(doc.get("history",[]) if isinstance(doc,dict) else doc if isinstance(doc,list) else [])
    return _normalize_history(inline)
def _store_history(path,history):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps({"schema_version":1,"description":"Daily validated total portfolio values used by the Gesamtdepotentwicklung dashboard.","history":history},ensure_ascii=False,indent=2)+"\n")
def _previous_total(history,asof,fallback):
    for p in reversed(history):
        if p.get("date")!=asof:return float(p["value"])
    return float(fallback)

def refresh_document(index_text,portfolio,prices,history=None):
    match,data=_load_inline_data(index_text); total=float(portfolio["total"]); direct=float(portfolio["direct_total"]); resolved=float(portfolio["resolved"]); unresolved=float(portfolio["unresolved"]); asof=_asof(prices)
    if history is None: history=data.get("history",[])
    history=_normalize_history(history); previous=_previous_total(history,asof,data.get("meta",{}).get("previousTotal",data.get("meta",{}).get("total",total)))
    by={p["date"]:float(p["value"]) for p in history}; by[asof]=total; history=_normalize_history([{"date":d,"value":v} for d,v in by.items()])
    meta=data.setdefault("meta",{}); meta.update({"asof":asof,"total":total,"resolved":resolved,"unresolved":unresolved,"directTotal":direct,"indirectTotal":resolved-direct,"top10":float(portfolio["top10"]),"top20":float(portfolio["top20"]),"hhi":float(portfolio["hhi"]),"effectiveN":10000.0/float(portfolio["hhi"]) if float(portfolio["hhi"]) else 0.0,"previousTotal":previous,"change":total-previous,"changePct":(total-previous)/previous if previous else 0.0,"cash":float(portfolio["cash"]),"gold":float(portfolio["gold"]),"bitcoin":float(portfolio["bitcoin_etp"]),"unresolvedLookthroughTail":max(0.0,unresolved-float(portfolio["cash"])-float(portfolio["gold"])-float(portfolio["bitcoin_etp"]))})
    companies=[]
    for rank,c in enumerate(portfolio["companies"],1):
        row={"name":c["name"],"sector":c["sector"],"direct":float(c["direct"]),"boerse":0.0,"titans":0.0,"tech":0.0,"world":0.0,"value":0.0,"indirect":float(c["indirect"]),"total":float(c["total"]),"share":float(c["total"])/total if total else 0.0,"rank":rank}; contained=[]
        if row["direct"]>0:contained.append("Direkt")
        for sid,amount in c.get("sources",{}).items():
            if sid=="direct":continue
            field=SOURCE_FIELDS.get(sid)
            if field:row[field[0]]=float(amount); contained.append(field[1]) if float(amount)>0 else None
        row["contained"]="; ".join(contained); companies.append(row)
    data["companies"]=companies; data["sectors"]=[{"name":r["name"],"value":float(r["value"])} for r in portfolio["sectors"]]; data["assets"]=[{"name":ASSET_NAMES.get(r["name"],r["name"]),"value":float(r["value"])} for r in portfolio["assets"]]; data["history"]=history
    encoded=json.dumps(data,ensure_ascii=False,separators=(",",":")); updated=index_text[:match.start(1)]+encoded+index_text[match.end(1):]
    updated=re.sub(r"<title>Depot Look-through Dashboard · [^<]+</title>",f"<title>Depot Look-through Dashboard · {asof}</title>",updated)
    updated=re.sub(r"Look-through Dashboard · Stand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?",f"Look-through Dashboard · Stand {asof}",updated)
    updated=re.sub(r"Datenstand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?",f"Datenstand {asof}",updated)
    updated=re.sub(r"Depotwerte \d{2}\.\d{2}\.\d{4}",f"Depotwerte {asof}",updated)
    updated=re.sub(r'<div class="notice small" style="margin-bottom:16px">.*?</div>',f'<div class="notice small" style="margin-bottom:16px">{_update_notice(prices)}</div>',updated,count=1,flags=re.S)
    return updated

def main():
    p=argparse.ArgumentParser(); p.add_argument("--index",type=Path,default=ROOT/"index.html"); p.add_argument("--portfolio",type=Path,default=ROOT/"data/generated/dry-run-portfolio.json"); p.add_argument("--prices",type=Path,default=ROOT/"data/prices/latest.json"); p.add_argument("--history",type=Path,default=DEFAULT_HISTORY); a=p.parse_args()
    text=a.index.read_text(); _,inline=_load_inline_data(text); history=_load_history(a.history,inline.get("history",[])); portfolio=json.loads(a.portfolio.read_text()); prices=json.loads(a.prices.read_text()); updated=refresh_document(text,portfolio,prices,history); _,d=_load_inline_data(updated); _store_history(a.history,d["history"]); a.index.write_text(updated); print(f"Stored {len(d['history'])} portfolio history points in {a.history}."); return 0
if __name__=="__main__":raise SystemExit(main())
