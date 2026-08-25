#!/usr/bin/env python3
"""Render unified long-term history for Depot 1 + Depot 2."""
from __future__ import annotations
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];INDEX=ROOT/'index.html'
BLOCK=r'''const fullHistory=DATA.history;
// The pre-rise reconstructed level is an anchoring artefact and visually misleading.
// Start the chart at the first large upward move in portfolio value (>= 20% of the
// full history value range). Keep the underlying history untouched for auditability.
const fullRange=Math.max(...fullHistory.map(x=>Number(x.value)))-Math.min(...fullHistory.map(x=>Number(x.value)));
let chartStartIndex=0;
for(let i=1;i<fullHistory.length;i++){
 if(Number(fullHistory[i].value)-Number(fullHistory[i-1].value)>=fullRange*.20){chartStartIndex=i;break;}
}
const chartHistory=fullHistory.slice(chartStartIndex);
const firstHistory=chartHistory[0], lastHistory=fullHistory[fullHistory.length-1];
const historyStartDate=new Date(firstHistory.date.split('.').reverse().join('-')+'T00:00:00');
const historyEndDate=new Date(lastHistory.date.split('.').reverse().join('-')+'T00:00:00');
const historyDays=Math.max(0,Math.round((historyEndDate-historyStartDate)/86400000));
const netContrib=Number(lastHistory.net_contributions||0), historyGain=Number(lastHistory.gain??(lastHistory.value-netContrib)), historyPct=lastHistory.simple_return==null?null:Number(lastHistory.simple_return);
const historyKpis=[
 ['Gesamtdepot · '+lastHistory.date,eur.format(lastHistory.value),'Depot 1 + Depot 2'],
 ['Nettoeinzahlungen',eur.format(netContrib),'beide Depots zusammen'],
 ['Wertzuwachs',eur.format(historyGain),historyPct==null?'nicht berechenbar':(historyGain>=0?'+':'')+pct.format(historyPct)],
 ['Dargestellter Zeitraum',firstHistory.date+' → '+lastHistory.date,historyDays+' Kalendertage']
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
document.getElementById('historyPeriodBadge').textContent=firstHistory.date+' → '+lastHistory.date;
const sample=(()=>{const h=chartHistory;if(h.length<=8)return h;return Array.from({length:8},(_,i)=>h[Math.round(i*(h.length-1)/7)]).filter((x,i,a)=>i===0||x.date!==a[i-1].date)})();
bars('historyBars',sample.map(x=>({name:x.date,value:x.value})),Math.max(...sample.map(x=>x.value)),10);
function renderHistoryChart(){
 const el=document.getElementById('historyChart'),W=Math.max(520,el.clientWidth||700),H=340,pad={l:70,r:30,t:28,b:52};
 const vals=chartHistory.flatMap(x=>[Number(x.value),Number(x.net_contributions||0)]),rawMin=Math.min(...vals),rawMax=Math.max(...vals),margin=Math.max(1,(rawMax-rawMin)*.04),min=rawMin-margin,max=rawMax+margin,span=Math.max(1,max-min);
 const mk=key=>chartHistory.map((x,i)=>({x:pad.l+i*(W-pad.l-pad.r)/Math.max(1,chartHistory.length-1),y:pad.t+(max-Number(x[key]||0))/span*(H-pad.t-pad.b),...x}));
 const pts=mk('value'),cpts=mk('net_contributions'),path=a=>a.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const grid=[0,.25,.5,.75,1].map(f=>{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#2a3656"/><text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#9aa7c2" font-size="11">${eur.format(v)}</text>`}).join('');
 const labelCount=Math.min(7,pts.length),idx=new Set(Array.from({length:labelCount},(_,i)=>Math.round(i*(pts.length-1)/Math.max(1,labelCount-1))));
 const labels=pts.map((p,i)=>idx.has(i)?`<text x="${p.x}" y="${H-20}" text-anchor="middle" fill="#9aa7c2" font-size="10">${p.date}</text>`:'').join('');
 const legend=`<g transform="translate(${pad.l+8},12)"><line x1="0" y1="0" x2="24" y2="0" stroke="#60a5fa" stroke-width="3"/><text x="30" y="4" fill="#eef2ff" font-size="11">Gesamtdepot</text><line x1="120" y1="0" x2="144" y2="0" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6 5"/><text x="150" y="4" fill="#eef2ff" font-size="11">Nettoeinzahlungen</text></g>`;
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="Gesamtdepotentwicklung Depot 1 und Depot 2 ab erstem wesentlichen Anstieg am ${firstHistory.date}">${grid}<path d="${path(cpts)}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="6 5"/><path d="${path(pts)}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>${labels}${legend}</svg>`;
}
renderHistoryChart();'''
NOTICE='''Die Historie umfasst <b>Depot 1 und Depot 2</b>. Im Diagramm beginnt die Darstellung beim ersten wesentlichen Anstieg des rekonstruierten Gesamtdepotwerts; ältere rekonstruierte Punkte bleiben in den Daten erhalten, werden aber wegen des künstlichen Niveauankers nicht dargestellt. Werte vor 17.07.2026 sind aus den insgesamt 439 dokumentierten Onvista-Transaktionen und historischen Kursen rekonstruiert und auf den ersten validierten Gesamtdepot-Stichtag abgestimmt; spätere Werte sind validierte Dashboard-Stichtage. Die gelbe Linie zeigt die kumulierten Nettoeinzahlungen beider Depots.'''
def main():
 text=INDEX.read_text(encoding='utf-8')
 text=re.sub(r'/\* dynamic-history-labels-v2 \*/\s*\(function\(\)\{.*?\}\)\(\);\s*', '', text, flags=re.S)
 pat=re.compile(r"(?:const fullHistory=DATA\.history;.*?|const firstHistory=DATA\.history\[0\], lastHistory=DATA\.history\[DATA\.history\.length-1\];.*?)renderHistoryChart\(\);",re.S)
 if not pat.search(text):raise ValueError('Could not locate history chart block')
 text=pat.sub(BLOCK,text,count=1)
 text=re.sub(r'<div class="notice small" style="margin-top:18px">.*?</div>',f'<div class="notice small" style="margin-top:18px">{NOTICE}</div>',text,count=1,flags=re.S)
 INDEX.write_text(text,encoding='utf-8');print('Updated history chart to start at first meaningful portfolio rise and rescale axes.')
if __name__=='__main__':main()
