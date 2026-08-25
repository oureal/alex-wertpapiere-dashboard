#!/usr/bin/env python3
"""Render scope-aware long-term history without a false performance jump."""
from __future__ import annotations
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"index.html"
BOUNDARY='17.07.2026'
KPI_AND_CHART=r'''const firstHistory=DATA.history[0], lastHistory=DATA.history[DATA.history.length-1];
const fullStartIndex=DATA.history.findIndex(x=>x.date==='17.07.2026');
const preHistory=fullStartIndex>0?DATA.history.slice(0,fullStartIndex):[];
const fullHistory=fullStartIndex>=0?DATA.history.slice(fullStartIndex):DATA.history;
const firstFull=fullHistory[0], lastFull=fullHistory[fullHistory.length-1];
const fullChange=firstFull&&lastFull?Number(lastFull.value)-Number(firstFull.value):0;
const fullChangePct=firstFull&&Number(firstFull.value)?fullChange/Number(firstFull.value):0;
const historyKpis=[
 ['Gesamtdepot · '+lastHistory.date,eur.format(lastHistory.value),'Depot 1 + Depot 2'],
 ['Rekonstruierte Historie',preHistory.length?preHistory[0].date+' → '+preHistory[preHistory.length-1].date:'—','Onvista-Transaktionen · Depot 2'],
 ['Gesamtdepot seit '+(firstFull?firstFull.date:'—'),eur.format(fullChange),(fullChange>=0?'+':'')+pct.format(fullChangePct)],
 ['Datenbereiche','2','vor 17.07.2026 Depot 2 · danach Gesamtdepot']
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
document.getElementById('historyPeriodBadge').textContent=firstHistory.date+' → '+lastHistory.date;
const historyBarSample=fullHistory.length?fullHistory:DATA.history;
bars('historyBars',historyBarSample.map(x=>({name:x.date,value:x.value})),Math.max(...historyBarSample.map(x=>x.value)),10);
function renderHistoryChart(){
 const el=document.getElementById('historyChart'), W=Math.max(520,el.clientWidth||700), H=340, pad={l:70,r:30,t:36,b:52};
 const vals=DATA.history.map(x=>Number(x.value));
 const contribVals=preHistory.map(x=>Number(x.net_contributions||0));
 const allVals=vals.concat(contribVals.length?contribVals:[0]);
 const min=Math.min(...allVals)*.985, max=Math.max(...allVals)*1.015, span=Math.max(1,max-min);
 const point=(x,i,key='value')=>({x:pad.l+i*(W-pad.l-pad.r)/(Math.max(1,DATA.history.length-1)),y:pad.t+(max-Number(x[key]||0))/span*(H-pad.t-pad.b),...x});
 const pts=DATA.history.map((x,i)=>point(x,i));
 const prePts=pts.slice(0,Math.max(0,fullStartIndex));
 const fullPts=fullStartIndex>=0?pts.slice(fullStartIndex):pts;
 const contribPts=preHistory.map((x,i)=>point(x,i,'net_contributions'));
 const path=arr=>arr.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const grid=[0,.25,.5,.75,1].map(f=>{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#2a3656"/><text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#9aa7c2" font-size="11">${eur.format(v)}</text>`}).join('');
 const boundaryPoint=fullStartIndex>=0?pts[fullStartIndex]:null;
 const boundary=boundaryPoint?`<line x1="${boundaryPoint.x}" y1="${pad.t}" x2="${boundaryPoint.x}" y2="${H-pad.b}" stroke="#94a3b8" stroke-dasharray="4 5"/><text x="${Math.max(pad.l+120,boundaryPoint.x-8)}" y="${pad.t+12}" text-anchor="end" fill="#cbd5e1" font-size="10">ab 17.07.2026: Depot 1 + Depot 2</text>`:'';
 const labelCount=Math.min(7,pts.length), labelIdx=new Set(Array.from({length:labelCount},(_,i)=>Math.round(i*(pts.length-1)/Math.max(1,labelCount-1))));
 const labels=pts.map((p,i)=>labelIdx.has(i)?`<text x="${p.x}" y="${H-20}" text-anchor="middle" fill="#9aa7c2" font-size="10">${p.date}</text>`:'').join('');
 const legend=`<g transform="translate(${pad.l+8},15)"><line x1="0" y1="0" x2="24" y2="0" stroke="#60a5fa" stroke-width="3"/><text x="30" y="4" fill="#eef2ff" font-size="11">Depot 2 rekonstruiert</text><line x1="145" y1="0" x2="169" y2="0" stroke="#6ee7b7" stroke-width="3"/><text x="175" y="4" fill="#eef2ff" font-size="11">Gesamtdepot validiert</text><line x1="310" y1="0" x2="334" y2="0" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6 5"/><text x="340" y="4" fill="#eef2ff" font-size="11">Nettoeinzahlungen Depot 2</text></g>`;
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="Historie mit getrennten Datenbereichen für Depot 2 und Gesamtdepot">${grid}${prePts.length?`<path d="${path(prePts)}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>`:''}${contribPts.length?`<path d="${path(contribPts)}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="6 5"/>`:''}${fullPts.length?`<path d="${path(fullPts)}" fill="none" stroke="#6ee7b7" stroke-width="3.5" stroke-linecap="round"/>`:''}${boundary}${labels}${legend}</svg>`;
}
renderHistoryChart();'''
NOTICE='''Die historischen Onvista-Transaktionen bilden <b>Depot 2</b> ab. Daher zeigt die blaue Linie bis 16.07.2026 nur den rekonstruierten Verlauf von Depot 2. Ab 17.07.2026 liegen erstmals validierte Werte für <b>Depot 1 + Depot 2</b> vor; dieser Scope-Wechsel wird bewusst als Unterbrechung dargestellt und <b>nicht als Wertzuwachs</b> gerechnet. Die gelbe Linie zeigt nur die dokumentierten Nettoeinzahlungen von Depot 2.'''
def main():
 text=INDEX.read_text(encoding='utf-8')
 pattern=re.compile(r"const firstHistory=DATA\.history\[0\], lastHistory=DATA\.history\[DATA\.history\.length-1\];.*?renderHistoryChart\(\);",flags=re.S)
 if not pattern.search(text): raise ValueError('Could not locate existing history KPI/chart block')
 text=pattern.sub(KPI_AND_CHART,text,count=1)
 text=re.sub(r'Die blaue Linie zeigt den <b>Depotwert</b>.*?Broker-Stichtagen abweichen\.',NOTICE,text,flags=re.S)
 INDEX.write_text(text,encoding='utf-8')
 print('Updated history UI with explicit Depot 2 / full-portfolio scope break.')
 return 0
if __name__=='__main__': raise SystemExit(main())