#!/usr/bin/env python3
"""Render unified long-term history for Depot 1 + Depot 2.

This renderer is intentionally idempotent: running it repeatedly replaces one
complete, explicitly marked JavaScript block instead of matching a partial
renderHistoryChart() call inside an event handler.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'

SCRIPT_START = '/* history-ui-script-v3:start */'
SCRIPT_END = '/* history-ui-script-v3:end */'

BLOCK = rf'''{SCRIPT_START}
const chartHistory=DATA.history;
const parseHistoryDate=s=>{{const [d,m,y]=s.split('.').map(Number);return new Date(Date.UTC(y,m-1,d));}};
const firstHistory=chartHistory[0],lastHistory=chartHistory[chartHistory.length-1];
const firstTs=parseHistoryDate(firstHistory.date).getTime(),lastTs=parseHistoryDate(lastHistory.date).getTime();
const startYear=parseHistoryDate(firstHistory.date).getUTCFullYear(),endYear=parseHistoryDate(lastHistory.date).getUTCFullYear();
const netContrib=Number(lastHistory.net_contributions||0),historyGain=Number(lastHistory.gain??(lastHistory.value-netContrib)),historyPct=lastHistory.simple_return==null?null:Number(lastHistory.simple_return);
let activeHistoryRange='max',activeCheckpointMode='half';
const historyKpis=[
 ['Gesamtdepot · '+endYear,eur.format(lastHistory.value),'Depot 1 + Depot 2'],
 ['Kumulierter Geldfluss',eur.format(netContrib),'Einzahlungen abzüglich Auszahlungen'],
 ['Wertzuwachs',eur.format(historyGain),historyPct==null?'nicht berechenbar':(historyGain>=0?'+':'')+pct.format(historyPct)],
 ['Dargestellter Zeitraum',startYear+' → '+endYear,'Jahre · Quartale']
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${{x[0]}}</div><div class="value">${{x[1]}}</div><div class="note">${{x[2]}}</div></div>`).join('');
document.getElementById('historyPeriodBadge').textContent=startYear+' → '+endYear;

function rowAtOrBefore(ts){{
 let found=null;
 for(const row of chartHistory){{const t=parseHistoryDate(row.date).getTime();if(t<=ts)found=row;else break;}}
 return found;
}}
function checkpointRows(mode='half'){{
 const out=[];
 for(let year=startYear;year<=endYear;year++){{
  if(mode==='year'){{
   const cutoff=Date.UTC(year,11,31);if(cutoff<firstTs)continue;
   const row=rowAtOrBefore(Math.min(cutoff,lastTs));if(row)out.push({{...row,period:`${{year}}`}});
  }}else{{
   for(let half=1;half<=2;half++){{
    const periodStart=Date.UTC(year,half===1?0:6,1);if(periodStart>lastTs)continue;
    const cutoff=half===1?Date.UTC(year,5,30):Date.UTC(year,11,31);if(cutoff<firstTs)continue;
    const row=rowAtOrBefore(Math.min(cutoff,lastTs));if(row)out.push({{...row,period:`${{year}} · H${{half}}`}});
   }}
  }}
 }}
 return out;
}}
function renderHistoryBars(){{
 const sample=checkpointRows(activeCheckpointMode),maxValue=Math.max(...sample.map(x=>Number(x.value)||0),1);
 document.getElementById('historyBars').innerHTML=sample.map(x=>`<div class="bar-row"><span>${{x.period}}</span><div class="bar-track"><div class="bar-fill" style="width:${{Math.max(0,Math.min(100,100*Number(x.value||0)/maxValue))}}%"></div></div><div class="bar-value">${{eur.format(Number(x.value||0))}}</div></div>`).join('');
}}
function visibleHistory(){{
 if(activeHistoryRange==='max')return chartHistory;
 const months={{m1:1,m6:6,y1:12,y3:36,y5:60}}[activeHistoryRange]||0;
 const cutoff=new Date(lastTs);cutoff.setUTCMonth(cutoff.getUTCMonth()-months);
 const rows=chartHistory.filter(x=>parseHistoryDate(x.date).getTime()>=cutoff.getTime());
 const before=rowAtOrBefore(cutoff.getTime());
 if(before&&(!rows.length||rows[0]!==before))rows.unshift(before);
 return rows.length>1?rows:chartHistory.slice(-2);
}}
function renderHistoryChart(){{
 const visible=visibleHistory(),visibleFirstTs=parseHistoryDate(visible[0].date).getTime(),visibleLastTs=parseHistoryDate(visible[visible.length-1].date).getTime();
 const visibleStartYear=parseHistoryDate(visible[0].date).getUTCFullYear(),visibleEndYear=parseHistoryDate(visible[visible.length-1].date).getUTCFullYear();
 const el=document.getElementById('historyChart'),W=Math.max(520,el.clientWidth||700),H=360,pad={{l:70,r:30,t:28,b:72}};
 const vals=visible.flatMap(x=>[Number(x.value),Number(x.net_contributions||0)]),rawMin=Math.min(...vals),rawMax=Math.max(...vals),margin=Math.max(1,(rawMax-rawMin)*.04),min=Math.max(0,rawMin-margin),max=rawMax+margin,span=Math.max(1,max-min);
 const xForTs=ts=>pad.l+(ts-visibleFirstTs)*(W-pad.l-pad.r)/Math.max(1,visibleLastTs-visibleFirstTs);
 const mk=key=>visible.map(x=>({{x:xForTs(parseHistoryDate(x.date).getTime()),y:pad.t+(max-Number(x[key]||0))/span*(H-pad.t-pad.b),...x}}));
 const pts=mk('value'),cpts=mk('net_contributions'),path=a=>a.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const grid=[0,.25,.5,.75,1].map(f=>{{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${{pad.l}}" y1="${{y}}" x2="${{W-pad.r}}" y2="${{y}}" stroke="#2a3656"/><text x="${{pad.l-10}}" y="${{y+4}}" text-anchor="end" fill="#9aa7c2" font-size="11">${{eur.format(v)}}</text>`}}).join('');
 const quarterTicks=[],yearLabels=[];
 for(let year=visibleStartYear;year<=visibleEndYear;year++){{
  const rangeStart=Math.max(visibleFirstTs,Date.UTC(year,0,1)),rangeEnd=Math.min(visibleLastTs,Date.UTC(year,11,31));
  if(rangeStart<=rangeEnd)yearLabels.push(`<text class="history-year-label" x="${{xForTs((rangeStart+rangeEnd)/2)}}" y="${{H-27}}" text-anchor="middle" fill="#eef2ff" font-size="11" font-weight="700">${{year}}</text>`);
  for(let q=1;q<=4;q++){{
   const qStart=Date.UTC(year,(q-1)*3,1),qEnd=Date.UTC(year,q*3,0);if(qEnd<visibleFirstTs||qStart>visibleLastTs)continue;
   const mid=(Math.max(qStart,visibleFirstTs)+Math.min(qEnd,visibleLastTs))/2,boundary=xForTs(Math.max(qStart,visibleFirstTs));
   quarterTicks.push(`<line x1="${{boundary}}" y1="${{pad.t}}" x2="${{boundary}}" y2="${{H-pad.b}}" stroke="#23304c" stroke-dasharray="3 5"/><text class="history-quarter-label" x="${{xForTs(mid)}}" y="${{H-10}}" text-anchor="middle" fill="#9aa7c2" font-size="9">Q${{q}}</text>`);
  }}
 }}
 const legend=`<g transform="translate(${{pad.l+8}},12)"><line x1="0" y1="0" x2="24" y2="0" stroke="#60a5fa" stroke-width="3"/><text x="30" y="4" fill="#eef2ff" font-size="11">Gesamtdepot</text><line x1="120" y1="0" x2="144" y2="0" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6 5"/><text x="150" y="4" fill="#eef2ff" font-size="11">Kumulierter Geldfluss</text></g>`;
 el.innerHTML=`<svg viewBox="0 0 ${{W}} ${{H}}" width="100%" height="100%" role="img" aria-label="Gesamtdepotentwicklung ${{visibleStartYear}} bis ${{visibleEndYear}} mit Quartalsmarken und kumuliertem Geldfluss">${{grid}}${{quarterTicks.join('')}}<path d="${{path(cpts)}}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="6 5"/><path d="${{path(pts)}}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/>${{yearLabels.join('')}}${{legend}}</svg>`;
}}
function bindHistoryControls(){{
 document.querySelectorAll('#historyRangeControls button').forEach(btn=>btn.addEventListener('click',()=>{{activeHistoryRange=btn.dataset.range;document.querySelectorAll('#historyRangeControls button').forEach(b=>b.classList.toggle('active',b===btn));renderHistoryChart();}}));
 document.querySelectorAll('#checkpointControls button').forEach(btn=>btn.addEventListener('click',()=>{{activeCheckpointMode=btn.dataset.mode;document.querySelectorAll('#checkpointControls button').forEach(b=>b.classList.toggle('active',b===btn));renderHistoryBars();}}));
}}
renderHistoryBars();renderHistoryChart();bindHistoryControls();
{SCRIPT_END}'''

NOTICE = '''Die Historie umfasst <b>Depot 1 und Depot 2</b>. Die Zeitachse ist nach Jahren gegliedert; innerhalb jedes Jahres markieren Q1 bis Q4 die Quartale. Mit 1M, 6M, 1J, 3J, 5J und Max lässt sich der Chartzeitraum direkt umschalten. Der Stichtagsvergleich kann jährlich oder halbjährlich angezeigt werden. Die gelbe Linie zeigt den <b>kumulierten Geldfluss</b>, also Einzahlungen abzüglich Auszahlungen. Werte vor 17.07.2026 werden aus den 439 dokumentierten Onvista-Transaktionen und historischen Kursen rekonstruiert; ab 17.07.2026 werden validierte Dashboard-Stichtage verwendet.'''

CONTROLS_CSS = '''
/* history-period-controls-v1 */
.history-switch{display:flex;gap:0;flex-wrap:wrap;margin:0 0 14px}.history-switch button{border:1px solid var(--line);border-right:0;background:#0e1729;color:#eef2ff;padding:9px 16px;cursor:pointer;min-width:58px}.history-switch button:first-child{border-radius:9px 0 0 9px}.history-switch button:last-child{border-right:1px solid var(--line);border-radius:0 9px 9px 0}.history-switch button.active{background:#24599a;color:white}.history-card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:4px}.history-card-head h3{margin:0}.history-card-head .history-switch{margin:0 0 8px}
'''

LEFT_CONTROLS = '''<div class="history-card-head"><h3>Depotwert im Zeitverlauf</h3><div id="historyRangeControls" class="history-switch" aria-label="Chartzeitraum"><button data-range="m1">1M</button><button data-range="m6">6M</button><button data-range="y1">1J</button><button data-range="y3">3J</button><button data-range="y5">5J</button><button data-range="max" class="active">Max</button></div></div>'''
RIGHT_CONTROLS = '''<div class="history-card-head"><h3>Stichtagsvergleich</h3><div id="checkpointControls" class="history-switch" aria-label="Stichtagsintervall"><button data-mode="year">Jährlich</button><button data-mode="half" class="active">Halbjährlich</button></div></div>'''


def replace_script_block(text: str) -> str:
    """Replace exactly one complete history JS block, safely on repeated runs."""
    marked = re.compile(
        re.escape(SCRIPT_START) + r'.*?' + re.escape(SCRIPT_END),
        flags=re.S,
    )
    if marked.search(text):
        return marked.sub(BLOCK, text, count=1)

    interactive = re.compile(
        r"const chartHistory=DATA\.history;.*?"
        r"renderHistoryBars\(\);renderHistoryChart\(\);bindHistoryControls\(\);",
        flags=re.S,
    )
    if interactive.search(text):
        return interactive.sub(BLOCK, text, count=1)

    legacy = re.compile(
        r"(?:const fullHistory=DATA\.history;.*?|"
        r"const firstHistory=DATA\.history\[0\], lastHistory=DATA\.history\[DATA\.history\.length-1\];.*?)"
        r"renderHistoryChart\(\);",
        flags=re.S,
    )
    if legacy.search(text):
        return legacy.sub(BLOCK, text, count=1)

    raise ValueError('Could not locate a complete history chart block')


def main():
    text = INDEX.read_text(encoding='utf-8')
    text = re.sub(r'/\* dynamic-history-labels-v2 \*/\s*\(function\(\)\{.*?\}\)\(\);\s*', '', text, flags=re.S)
    text = replace_script_block(text)
    text = re.sub(r'<div class="notice small" style="margin-top:18px">.*?</div>', f'<div class="notice small" style="margin-top:18px">{NOTICE}</div>', text, count=1, flags=re.S)
    text = re.sub(r'/\* history-period-controls-v1 \*/.*?(?=</style>)', '', text, flags=re.S)
    text = text.replace('</style>', CONTROLS_CSS + '</style>', 1)
    text = re.sub(r'<div class="history-card-head"><h3>Depotwert im Zeitverlauf</h3>.*?</div></div>|<h3>Depotwert im Zeitverlauf</h3>', LEFT_CONTROLS, text, count=1, flags=re.S)
    text = re.sub(r'<div class="history-card-head"><h3>Stichtagsvergleich</h3>.*?</div></div>|<h3>Stichtagsvergleich</h3>', RIGHT_CONTROLS, text, count=1, flags=re.S)

    old_note = "<p><b>Gesamtwert:</b> von ${eur.format(oldTotal)} auf ${eur.format(newTotal)} – eine Veränderung von <b>${eur.format(historyGain)} (${historyGain>=0?'+':''}${pct.format(historyPct)})</b>.</p>"
    new_note = "<p><b>Änderung zum letzten Tag:</b> von ${eur.format(oldTotal)} auf ${eur.format(newTotal)} – <b>${eur.format(newTotal-oldTotal)} (${oldTotal?((newTotal-oldTotal)>=0?'+':'')+pct.format((newTotal-oldTotal)/oldTotal):'–'})</b>. &nbsp; <b>Gesamte Änderung seit Beginn:</b> <b>${eur.format(historyGain)} (${historyPct==null?'–':(historyGain>=0?'+':'')+pct.format(historyPct)})</b>.</p>"
    if old_note in text:
        text = text.replace(old_note, new_note, 1)
    elif new_note not in text:
        raise ValueError('Could not locate portfolio change summary')

    if text.count(SCRIPT_START) != 1 or text.count(SCRIPT_END) != 1:
        raise ValueError('History UI script markers are not unique')
    if text.count("const chartHistory=DATA.history;") != 1:
        raise ValueError('History UI JavaScript block duplicated')

    INDEX.write_text(text, encoding='utf-8')
    print('Updated history UI and clarified daily versus total portfolio change.')


if __name__ == '__main__':
    main()
