#!/usr/bin/env python3
"""Render cash-flow-aware Gesamtdepotentwicklung and keep the production rebuild deterministic."""
from __future__ import annotations
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; INDEX=ROOT/"index.html"
KPI_AND_CHART=r'''const firstHistory=DATA.history[0], lastHistory=DATA.history[DATA.history.length-1];
const historyStartDate=new Date(firstHistory.date.split('.').reverse().join('-')+'T00:00:00');
const historyEndDate=new Date(lastHistory.date.split('.').reverse().join('-')+'T00:00:00');
const historyDays=Math.max(0,Math.round((historyEndDate-historyStartDate)/86400000));
const netContrib=Number(lastHistory.net_contributions||0), historyGain=Number(lastHistory.gain??(lastHistory.value-netContrib)), historyPct=lastHistory.simple_return==null?null:Number(lastHistory.simple_return);
const historyKpis=[
 ['Depotwert · '+lastHistory.date,eur.format(lastHistory.value),'aktueller Depotstand'],
 ['Nettoeinzahlungen',eur.format(netContrib),'Einzahlungen abzüglich Auszahlungen'],
 ['Wertzuwachs',eur.format(historyGain),historyPct==null?'nicht berechenbar':(historyGain>=0?'+':'')+pct.format(historyPct)],
 ['Historie',DATA.history.length+' Stichtage',historyDays+' Kalendertage']
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
document.getElementById('historyPeriodBadge').textContent=firstHistory.date+' → '+lastHistory.date;
const historyBarSample=(()=>{const h=DATA.history;if(h.length<=8)return h;const out=[];for(let i=0;i<8;i++)out.push(h[Math.round(i*(h.length-1)/7)]);return out.filter((x,i,a)=>i===0||x.date!==a[i-1].date)})();
bars('historyBars',historyBarSample.map(x=>({name:x.date,value:x.value})),Math.max(...historyBarSample.map(x=>x.value)),10);
function renderHistoryChart(){
 const el=document.getElementById('historyChart'), W=Math.max(520,el.clientWidth||700), H=340, pad={l:70,r:30,t:28,b:52};
 const vals=DATA.history.flatMap(x=>[Number(x.value),Number(x.net_contributions||0)]), min=Math.min(...vals)*.985, max=Math.max(...vals)*1.015, span=Math.max(1,max-min);
 const mkpts=key=>DATA.history.map((x,i)=>({x:pad.l+i*(W-pad.l-pad.r)/(Math.max(1,DATA.history.length-1)),y:pad.t+(max-Number(x[key]||0))/span*(H-pad.t-pad.b),...x}));
 const pts=mkpts('value'), contribPts=mkpts('net_contributions');
 const grid=[0,.25,.5,.75,1].map(f=>{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#2a3656"/><text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#9aa7c2" font-size="11">${eur.format(v)}</text>`}).join('');
 const line=pts.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' '), contribLine=contribPts.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const area=`M ${pts[0].x} ${H-pad.b} ${pts.map(p=>`L ${p.x} ${p.y}`).join(' ')} L ${pts[pts.length-1].x} ${H-pad.b} Z`;
 const labelCount=Math.min(7,pts.length), labelIdx=new Set(Array.from({length:labelCount},(_,i)=>Math.round(i*(pts.length-1)/Math.max(1,labelCount-1))));
 const labels=pts.map((p,i)=>labelIdx.has(i)?`<circle cx="${p.x}" cy="${p.y}" r="4" fill="#6ee7b7" stroke="#0b1020" stroke-width="2"/><text x="${p.x}" y="${H-20}" text-anchor="middle" fill="#9aa7c2" font-size="10">${p.date}</text>`:'').join('');
 const legend=`<g transform="translate(${pad.l+8},12)"><line x1="0" y1="0" x2="24" y2="0" stroke="#60a5fa" stroke-width="3"/><text x="30" y="4" fill="#eef2ff" font-size="11">Depotwert</text><line x1="105" y1="0" x2="129" y2="0" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6 5"/><text x="135" y="4" fill="#eef2ff" font-size="11">Nettoeinzahlungen</text></g>`;
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="Gesamtdepotentwicklung seit Depotbeginn mit Nettoeinzahlungen">${grid}<path d="${area}" fill="#60a5fa" opacity=".08"/><path d="${contribLine}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="6 5"/><path d="${line}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>${labels}${legend}</svg>`;
}
renderHistoryChart();'''
def main():
 text=INDEX.read_text(encoding='utf-8')
 pattern=re.compile(r"const firstHistory=DATA\.history\[0\], lastHistory=DATA\.history\[DATA\.history\.length-1\];.*?renderHistoryChart\(\);",flags=re.S)
 if not pattern.search(text): raise ValueError('Could not locate existing history KPI/chart block')
 text=pattern.sub(KPI_AND_CHART,text,count=1)
 text=re.sub(r'Die Zeitreihe bis 16\.07\.2026.*?Investment-Performance\.', 'Die blaue Linie zeigt den <b>Depotwert</b>, die gestrichelte Linie die <b>kumulierten Nettoeinzahlungen</b>. Der Wertzuwachs ist Depotwert minus Nettoeinzahlungen; die Prozentangabe bezieht diesen Wertzuwachs auf die Nettoeinzahlungen und ist damit von bloßen Kapitalzuflüssen getrennt. Historische Werte vor 17.07.2026 bleiben rekonstruiert und können von Broker-Stichtagen abweichen.', text)
 INDEX.write_text(text,encoding='utf-8'); print('Updated cash-flow-aware long-term history UI.'); return 0
if __name__=='__main__': raise SystemExit(main())