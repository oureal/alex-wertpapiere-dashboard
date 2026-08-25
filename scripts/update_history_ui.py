#!/usr/bin/env python3
"""Render unified long-term history for Depot 1 + Depot 2."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'

BLOCK = r'''const chartHistory=DATA.history;
const parseHistoryDate=s=>{const [d,m,y]=s.split('.').map(Number);return new Date(Date.UTC(y,m-1,d));};
const firstHistory=chartHistory[0],lastHistory=chartHistory[chartHistory.length-1];
const firstTs=parseHistoryDate(firstHistory.date).getTime(),lastTs=parseHistoryDate(lastHistory.date).getTime();
const startYear=parseHistoryDate(firstHistory.date).getUTCFullYear(),endYear=parseHistoryDate(lastHistory.date).getUTCFullYear();
const netContrib=Number(lastHistory.net_contributions||0),historyGain=Number(lastHistory.gain??(lastHistory.value-netContrib)),historyPct=lastHistory.simple_return==null?null:Number(lastHistory.simple_return);
const historyKpis=[
 ['Gesamtdepot · '+endYear,eur.format(lastHistory.value),'Depot 1 + Depot 2'],
 ['Kumulierter Geldfluss',eur.format(netContrib),'Einzahlungen abzüglich Auszahlungen'],
 ['Wertzuwachs',eur.format(historyGain),historyPct==null?'nicht berechenbar':(historyGain>=0?'+':'')+pct.format(historyPct)],
 ['Dargestellter Zeitraum',startYear+' → '+endYear,'Jahre · Quartale']
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
document.getElementById('historyPeriodBadge').textContent=startYear+' → '+endYear;

function rowAtOrBefore(ts){
 let found=null;
 for(const row of chartHistory){const t=parseHistoryDate(row.date).getTime();if(t<=ts)found=row;else break;}
 return found;
}
function halfYearRows(){
 const out=[];
 for(let year=startYear;year<=endYear;year++){
  for(let half=1;half<=2;half++){
   const periodStart=Date.UTC(year,half===1?0:6,1);
   if(periodStart>lastTs)continue;
   const cutoff=half===1?Date.UTC(year,5,30):Date.UTC(year,11,31);
   if(cutoff<firstTs)continue;
   const row=rowAtOrBefore(Math.min(cutoff,lastTs));
   if(row)out.push({...row,period:`${year} · H${half}`});
  }
 }
 return out;
}
const sample=halfYearRows();
function renderHistoryBars(){
 const maxValue=Math.max(...sample.map(x=>Number(x.value)||0),1);
 document.getElementById('historyBars').innerHTML=sample.map(x=>`<div class="bar-row"><span>${x.period}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0,Math.min(100,100*Number(x.value||0)/maxValue))}%"></div></div><div class="bar-value">${eur.format(Number(x.value||0))}</div></div>`).join('');
}
renderHistoryBars();

function renderHistoryChart(){
 const el=document.getElementById('historyChart'),W=Math.max(520,el.clientWidth||700),H=360,pad={l:70,r:30,t:28,b:72};
 const vals=chartHistory.flatMap(x=>[Number(x.value),Number(x.net_contributions||0)]),rawMin=Math.min(...vals),rawMax=Math.max(...vals),margin=Math.max(1,(rawMax-rawMin)*.04),min=Math.max(0,rawMin-margin),max=rawMax+margin,span=Math.max(1,max-min);
 const xForTs=ts=>pad.l+(ts-firstTs)*(W-pad.l-pad.r)/Math.max(1,lastTs-firstTs);
 const mk=key=>chartHistory.map(x=>({x:xForTs(parseHistoryDate(x.date).getTime()),y:pad.t+(max-Number(x[key]||0))/span*(H-pad.t-pad.b),...x}));
 const pts=mk('value'),cpts=mk('net_contributions'),path=a=>a.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const grid=[0,.25,.5,.75,1].map(f=>{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#2a3656"/><text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#9aa7c2" font-size="11">${eur.format(v)}</text>`}).join('');
 const quarterTicks=[];
 const yearLabels=[];
 for(let year=startYear;year<=endYear;year++){
  const visibleStart=Math.max(firstTs,Date.UTC(year,0,1)),visibleEnd=Math.min(lastTs,Date.UTC(year,11,31));
  if(visibleStart<=visibleEnd){const x=xForTs((visibleStart+visibleEnd)/2);yearLabels.push(`<text class="history-year-label" x="${x}" y="${H-27}" text-anchor="middle" fill="#eef2ff" font-size="11" font-weight="700">${year}</text>`);}
  for(let q=1;q<=4;q++){
   const qStart=Date.UTC(year,(q-1)*3,1),qEnd=Date.UTC(year,q*3,0),mid=(Math.max(qStart,firstTs)+Math.min(qEnd,lastTs))/2;
   if(qEnd<firstTs||qStart>lastTs)continue;
   const x=xForTs(mid),boundary=xForTs(Math.max(qStart,firstTs));
   quarterTicks.push(`<line x1="${boundary}" y1="${pad.t}" x2="${boundary}" y2="${H-pad.b}" stroke="#23304c" stroke-dasharray="3 5"/><text class="history-quarter-label" x="${x}" y="${H-10}" text-anchor="middle" fill="#9aa7c2" font-size="9">Q${q}</text>`);
  }
 }
 const legend=`<g transform="translate(${pad.l+8},12)"><line x1="0" y1="0" x2="24" y2="0" stroke="#60a5fa" stroke-width="3"/><text x="30" y="4" fill="#eef2ff" font-size="11">Gesamtdepot</text><line x1="120" y1="0" x2="144" y2="0" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6 5"/><text x="150" y="4" fill="#eef2ff" font-size="11">Kumulierter Geldfluss</text></g>`;
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="Gesamtdepotentwicklung ${startYear} bis ${endYear} mit Quartalsmarken und kumuliertem Geldfluss">${grid}${quarterTicks.join('')}<path d="${path(cpts)}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="6 5"/><path d="${path(pts)}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>${yearLabels.join('')}${legend}</svg>`;
}
renderHistoryChart();'''

NOTICE = '''Die Historie umfasst <b>Depot 1 und Depot 2</b>. Die Zeitachse ist nach Jahren gegliedert; innerhalb jedes Jahres markieren Q1 bis Q4 die Quartale. Der Stichtagsvergleich verwendet Halbjahresintervalle (H1/H2) statt einzelner, zufälliger Datumsstichtage. Die gelbe Linie zeigt den <b>kumulierten Geldfluss</b>, also Einzahlungen abzüglich Auszahlungen. Werte vor 17.07.2026 werden aus den 439 dokumentierten Onvista-Transaktionen und historischen Kursen rekonstruiert; ab 17.07.2026 werden validierte Dashboard-Stichtage verwendet.'''

def main():
    text = INDEX.read_text(encoding='utf-8')
    text = re.sub(r'/\* dynamic-history-labels-v2 \*/\s*\(function\(\)\{.*?\}\)\(\);\s*', '', text, flags=re.S)
    pat = re.compile(r"(?:const chartHistory=DATA\.history;.*?|const fullHistory=DATA\.history;.*?|const firstHistory=DATA\.history\[0\], lastHistory=DATA\.history\[DATA\.history\.length-1\];.*?)renderHistoryChart\(\);", re.S)
    if not pat.search(text):
        raise ValueError('Could not locate history chart block')
    text = pat.sub(BLOCK, text, count=1)
    text = re.sub(r'<div class="notice small" style="margin-top:18px">.*?</div>', f'<div class="notice small" style="margin-top:18px">{NOTICE}</div>', text, count=1, flags=re.S)
    INDEX.write_text(text, encoding='utf-8')
    print('Updated history UI with year/quarter axis, half-year checkpoints and cumulative cash-flow wording.')

if __name__ == '__main__':
    main()
