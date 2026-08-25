#!/usr/bin/env python3
"""Keep dashboard navigation, history view, manual update link and responsive layout synchronized."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

STYLE = """
.manual-update{display:block;margin:18px 4px 0;padding:11px 12px;border:1px solid #36527a;border-radius:10px;background:#14263c;color:#dbeafe;text-decoration:none;font-weight:700;text-align:center}.manual-update:hover{background:#1b3554;color:white}.manual-update-note{display:block;margin:6px 8px 0;color:#71809e;font-size:10px;text-align:center}
""".strip()

RESPONSIVE_STYLE = """
/* responsive-dashboard-v2 */
@media(max-width:1000px){
  .app{display:block;min-height:0}.sidebar{position:static;height:auto;padding:14px 12px;border-right:0;border-bottom:1px solid var(--line)}
  .brand{margin:0 4px 2px}.sub{margin:0 4px 12px}.nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;overflow:visible}
  .nav button{min-width:0;margin:0;padding:10px 9px;white-space:normal;line-height:1.25}.nav .n{margin-right:5px}
  .manual-update{margin:10px 0 0}.manual-update-note{margin-top:4px}.main{padding:18px 14px}.header{align-items:center}.kpis,.two,.equal{grid-template-columns:1fr 1fr}
}
@media(max-width:650px){
  body{font-size:14px}.sidebar{padding:12px 10px}.brand{font-size:18px}.sub{font-size:11px}.nav{grid-template-columns:1fr 1fr;gap:6px}
  .nav button{min-height:46px;font-size:12px;padding:8px 7px}.nav .n{width:22px;height:22px}.main{padding:12px 10px}.header{display:block;margin-bottom:14px}.header h1{font-size:24px;line-height:1.15}
  .header .badge{display:inline-block;margin-top:8px}.kpis,.two,.equal{grid-template-columns:1fr}.card{padding:13px;border-radius:12px}.kpi .value{font-size:22px}
  .notice{padding:11px 12px;line-height:1.5}.chart{height:300px}.chart.tall{height:420px}.treemap{height:420px}.pie{min-height:280px}.donut{width:210px;height:210px}.donut:after{inset:46px}
  .bar-row{grid-template-columns:minmax(90px,1.15fr) 2fr 74px;gap:7px;font-size:12px}.bar-value{font-size:11px}.controls{display:grid;grid-template-columns:1fr;gap:8px}.controls input,.controls select{width:100%;min-height:44px;font-size:16px}
  .table-wrap{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}table{font-size:12px}th,td{padding:8px 9px}.risk{grid-template-columns:1fr;gap:6px}.source-line{grid-template-columns:1fr;gap:3px}.legend{font-size:12px}.footer{padding:20px 4px 6px;line-height:1.45}
}
@media(max-width:390px){
  .nav{grid-template-columns:1fr}.nav button{min-height:44px}.header h1{font-size:22px}.main{padding:10px 8px}.card{padding:11px}.bar-row{grid-template-columns:1fr 1.5fr 66px}
}
""".strip()

BUTTON = """
<a class="manual-update" id="manualUpdateLink" href="https://github.com/oureal/dashboard-wp/actions/workflows/update-portfolio-dashboard.yml" target="_blank" rel="noopener noreferrer">↻ Kurse jetzt aktualisieren</a>
<span class="manual-update-note">öffnet GitHub Actions</span>
""".strip()

NAV = """<nav class="nav" id="nav">
    <button class="active" data-page="history"><span class="n">1</span>Gesamtdepotentwicklung</button>
    <button data-page="dashboard"><span class="n">2</span>Dashboard</button>
    <button data-page="treemap"><span class="n">3</span>Look-through-Treemap</button>
    <button data-page="sectors"><span class="n">4</span>Branchen</button>
    <button data-page="regions"><span class="n">5</span>Länder & Währungen</button>
    <button data-page="risk"><span class="n">6</span>Risiko</button>
  </nav>"""

HISTORY_HEADER = """<div class="header"><div><h1>Gesamtdepotentwicklung</h1><div class="muted">Fortlaufende Zeitreihe aller erfolgreich gespeicherten Depot-Stichtage</div></div><div class="badge" id="historyPeriodBadge"></div></div>"""

HISTORY_JS = r"""
const parseHistoryDate=s=>{const [d,m,y]=s.split('.').map(Number);return new Date(Date.UTC(y,m-1,d));};
const historyFirst=DATA.history[0], historyLast=DATA.history[DATA.history.length-1];
const historyDelta=historyLast.value-historyFirst.value;
const historyPct=historyFirst.value?historyDelta/historyFirst.value:0;
const historyDays=Math.round((parseHistoryDate(historyLast.date)-parseHistoryDate(historyFirst.date))/86400000);
document.getElementById('historyPeriodBadge').textContent=`${historyFirst.date} → ${historyLast.date}`;
const historyKpis=[
 [`Erster Stichtag · ${historyFirst.date}`,eur.format(historyFirst.value),'Beginn der gespeicherten Zeitreihe'],
 [`Aktueller Stichtag · ${historyLast.date}`,eur.format(historyLast.value),'letzter erfolgreicher Depotstand'],
 ['Veränderung seit Beginn',eur.format(historyDelta),(historyDelta>=0?'+':'')+pct.format(historyPct)],
 ['Historie',`${DATA.history.length} Stichtage`,`${historyDays} Kalendertage`]
];
document.getElementById('historyKpis').innerHTML=historyKpis.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
bars('historyBars',DATA.history.map(x=>({name:x.date,value:x.value})),Math.max(...DATA.history.map(x=>x.value)),Math.min(12,DATA.history.length));
function renderHistoryChart(){
 const el=document.getElementById('historyChart'), W=Math.max(520,el.clientWidth||700), H=340, pad={l:70,r:30,t:28,b:52};
 const vals=DATA.history.map(x=>x.value), min=Math.min(...vals)*.985, max=Math.max(...vals)*1.015, span=Math.max(1,max-min);
 const pts=DATA.history.map((x,i)=>({x:pad.l+i*(W-pad.l-pad.r)/(Math.max(1,DATA.history.length-1)),y:pad.t+(max-x.value)/span*(H-pad.t-pad.b),...x}));
 const grid=[0,.25,.5,.75,1].map(f=>{const v=min+(max-min)*(1-f),y=pad.t+f*(H-pad.t-pad.b);return `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#2a3656"/><text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#9aa7c2" font-size="11">${eur.format(v)}</text>`}).join('');
 const line=pts.map((p,i)=>(i?'L':'M')+p.x+' '+p.y).join(' ');
 const area=`M ${pts[0].x} ${H-pad.b} ${pts.map(p=>`L ${p.x} ${p.y}`).join(' ')} L ${pts[pts.length-1].x} ${H-pad.b} Z`;
 const labelEvery=Math.max(1,Math.ceil(pts.length/6));
 const dots=pts.map((p,i)=>`<circle cx="${p.x}" cy="${p.y}" r="5" fill="#6ee7b7" stroke="#0b1020" stroke-width="3"/>${(i%labelEvery===0||i===pts.length-1)?`<text x="${p.x}" y="${p.y-13}" text-anchor="middle" fill="#eef2ff" font-size="11" font-weight="700">${eur.format(p.value)}</text><text x="${p.x}" y="${H-20}" text-anchor="middle" fill="#9aa7c2" font-size="10">${p.date}</text>`:''}`).join('');
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="Gesamtdepotentwicklung">${grid}<path d="${area}" fill="#60a5fa" opacity=".10"/><path d="${line}" fill="none" stroke="#60a5fa" stroke-width="4" stroke-linecap="round"/>${dots}</svg>`;
}
renderHistoryChart();
document.getElementById('historyNotes').innerHTML=`
 <p><b>Gesamtwert:</b> von ${eur.format(historyFirst.value)} am ${historyFirst.date} auf ${eur.format(historyLast.value)} am ${historyLast.date} – eine Veränderung von <b>${eur.format(historyDelta)} (${historyDelta>=0?'+':''}${pct.format(historyPct)})</b>.</p>
 <p><b>Aktuelle Struktur:</b> direkte Aktien ${eur.format(DATA.meta.directTotal)}, indirekt aufgelöste Aktien ${eur.format(DATA.meta.indirectTotal)} und ${eur.format(DATA.meta.unresolved)} nicht aufgelöste bzw. Nicht-Aktien-Bausteine.</p>
 <p class="muted small"><b>Hinweis:</b> Jeder erfolgreiche tägliche oder manuelle Aktualisierungslauf speichert maximal einen Depotwert pro Kalendertag. Die Zeitreihe zeigt Depotwerte, keine um Käufe, Verkäufe oder Ein-/Auszahlungen bereinigte Investment-Performance.</p>`;
""".strip()


def main() -> int:
    text = INDEX.read_text()
    original = text

    if ".manual-update{" not in text:
        text = text.replace("</style>", STYLE + "\n</style>", 1)

    if "/* responsive-dashboard-v2 */" not in text:
        text = text.replace("</style>", RESPONSIVE_STYLE + "\n</style>", 1)

    nav_pattern = r'<nav class="nav" id="nav">.*?</nav>'
    if re.search(nav_pattern, text, flags=re.S):
        text = re.sub(nav_pattern, NAV, text, count=1, flags=re.S)
    else:
        raise SystemExit("Dashboard navigation block not found")

    text = re.sub(r'<section id="dashboard" class="page(?: active)?">', '<section id="dashboard" class="page">', text, count=1)
    text = re.sub(r'<section id="history" class="page(?: active)?">', '<section id="history" class="page active">', text, count=1)

    history_header_pattern = r'(<section id="history" class="page active">\s*)<div class="header">.*?</div>\s*(?=<div class="grid kpis" id="historyKpis">)'
    if re.search(history_header_pattern, text, flags=re.S):
        text = re.sub(history_header_pattern, r'\1' + HISTORY_HEADER + "\n ", text, count=1, flags=re.S)
    else:
        raise SystemExit("History header block not found")

    history_js_pattern = r'const historyDelta=.*?(?=const directCountries=)'
    if re.search(history_js_pattern, text, flags=re.S):
        text = re.sub(history_js_pattern, HISTORY_JS + "\n", text, count=1, flags=re.S)
    else:
        raise SystemExit("History JavaScript block not found")

    button_pattern = r'<a class="manual-update" id="manualUpdateLink".*?</a>\s*<span class="manual-update-note">.*?</span>'
    if re.search(button_pattern, text, flags=re.S):
        text = re.sub(button_pattern, BUTTON, text, count=1, flags=re.S)
    else:
        marker = "</nav>"
        if marker not in text:
            raise SystemExit("Dashboard navigation marker not found")
        text = text.replace(marker, marker + "\n" + BUTTON, 1)

    if text != original:
        INDEX.write_text(text)
        print("Dashboard shell synchronized: dynamic history, history start page, navigation, manual update link and responsive layout.")
    else:
        print("Dashboard shell already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
