#!/usr/bin/env python3
"""Keep dashboard navigation, movers/history views, manual update link and responsive layout synchronized."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

STYLE = """
.manual-update{display:block;margin:18px 4px 0;padding:11px 12px;border:1px solid #36527a;border-radius:10px;background:#14263c;color:#dbeafe;text-decoration:none;font-weight:700;text-align:center}.manual-update:hover{background:#1b3554;color:white}.manual-update-note{display:block;margin:6px 8px 0;color:#71809e;font-size:10px;text-align:center}
""".strip()

MOVERS_STYLE = """
/* movers-dashboard-v1 */
.movers-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.mover-card{min-width:0}.mover-period{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}.mover-period h3{margin:0;font-size:17px}.mover-range{font-size:11px;color:var(--muted);text-align:right}.mover-columns{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mover-side{border:1px solid var(--line);border-radius:11px;overflow:hidden}.mover-side h4{margin:0;padding:9px 10px;background:#17213a;font-size:12px}.mover-side.plus h4{color:#86efac}.mover-side.minus h4{color:#fda4af}.mover-row{display:grid;grid-template-columns:minmax(105px,1fr) 62px 88px;gap:7px;align-items:center;padding:9px 10px;border-top:1px solid #26314a;font-size:12px}.mover-row:first-of-type{border-top:0}.mover-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mover-pct,.mover-eur{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}.mover-side.plus .mover-pct,.mover-side.plus .mover-eur{color:#86efac}.mover-side.minus .mover-pct,.mover-side.minus .mover-eur{color:#fda4af}.mover-barbox{grid-column:1/-1;height:5px;background:#26314e;border-radius:99px;overflow:hidden;margin-top:-2px}.mover-bar{height:100%;border-radius:99px}.mover-side.plus .mover-bar{background:#34d399}.mover-side.minus .mover-bar{background:#fb7185}.mover-empty{padding:13px 10px;color:var(--muted);font-size:12px}
""".strip()

RESPONSIVE_STYLE = """
/* responsive-dashboard-v2 */
@media(max-width:1000px){
  .app{display:block;min-height:0}.sidebar{position:static;height:auto;padding:14px 12px;border-right:0;border-bottom:1px solid var(--line)}
  .brand{margin:0 4px 2px}.sub{margin:0 4px 12px}.nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;overflow:visible}
  .nav button{min-width:0;margin:0;padding:10px 9px;white-space:normal;line-height:1.25}.nav .n{margin-right:5px}
  .manual-update{margin:10px 0 0}.manual-update-note{margin-top:4px}.main{padding:18px 14px}.header{align-items:center}.kpis,.two,.equal{grid-template-columns:1fr 1fr}
}
@media(max-width:760px){.movers-grid{grid-template-columns:1fr}.mover-columns{grid-template-columns:1fr 1fr}}
@media(max-width:650px){
  body{font-size:14px}.sidebar{padding:12px 10px}.brand{font-size:18px}.sub{font-size:11px}.nav{grid-template-columns:1fr 1fr;gap:6px}
  .nav button{min-height:46px;font-size:12px;padding:8px 7px}.nav .n{width:22px;height:22px}.main{padding:12px 10px}.header{display:block;margin-bottom:14px}.header h1{font-size:24px;line-height:1.15}
  .header .badge{display:inline-block;margin-top:8px}.kpis,.two,.equal{grid-template-columns:1fr}.card{padding:13px;border-radius:12px}.kpi .value{font-size:22px}
  .notice{padding:11px 12px;line-height:1.5}.chart{height:300px}.chart.tall{height:420px}.treemap{height:420px}.pie{min-height:280px}.donut{width:210px;height:210px}.donut:after{inset:46px}
  .bar-row{grid-template-columns:minmax(90px,1.15fr) 2fr 74px;gap:7px;font-size:12px}.bar-value{font-size:11px}.controls{display:grid;grid-template-columns:1fr;gap:8px}.controls input,.controls select{width:100%;min-height:44px;font-size:16px}
  .table-wrap{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}table{font-size:12px}th,td{padding:8px 9px}.risk{grid-template-columns:1fr;gap:6px}.source-line{grid-template-columns:1fr;gap:3px}.legend{font-size:12px}.footer{padding:20px 4px 6px;line-height:1.45}
  .mover-columns{grid-template-columns:1fr}.mover-row{grid-template-columns:minmax(100px,1fr) 58px 82px}.mover-period{display:block}.mover-range{text-align:left;margin-top:3px}
}
@media(max-width:390px){
  .nav{grid-template-columns:1fr}.nav button{min-height:44px}.header h1{font-size:22px}.main{padding:10px 8px}.card{padding:11px}.bar-row{grid-template-columns:1fr 1.5fr 66px}.mover-row{grid-template-columns:minmax(90px,1fr) 54px 76px;padding:8px}
}
""".strip()

BUTTON = """
<a class="manual-update" id="manualUpdateLink" href="https://github.com/oureal/dashboard-wp/actions/workflows/update-portfolio-dashboard.yml" target="_blank" rel="noopener noreferrer">↻ Kurse jetzt aktualisieren</a>
<span class="manual-update-note">öffnet GitHub Actions</span>
""".strip()

NAV = """<nav class="nav" id="nav">
    <button class="active" data-page="history"><span class="n">1</span>Gesamtdepotentwicklung</button>
    <button data-page="movers"><span class="n">2</span>Gewinner & Verlierer</button>
    <button data-page="dashboard"><span class="n">3</span>Dashboard</button>
    <button data-page="treemap"><span class="n">4</span>Look-through-Treemap</button>
    <button data-page="sectors"><span class="n">5</span>Branchen</button>
    <button data-page="regions"><span class="n">6</span>Länder & Währungen</button>
    <button data-page="risk"><span class="n">7</span>Risiko</button>
  </nav>"""

MOVERS_SECTION = """<section id="movers" class="page">
 <div class="header"><div><h1>Gewinner & Verlierer</h1><div class="muted">Top 3 PLUS und Top 3 MINUS nach Veränderung des Positionswerts</div></div><div class="badge" id="moversAsOf"></div></div>
 <div class="movers-grid" id="moversGrid"></div>
 <div class="notice small" style="margin-top:16px">Die Rangfolge basiert auf der Veränderung des Positionswerts in EUR und Prozent zwischen zwei gespeicherten Stichtagen. Käufe, Verkäufe oder Stückzahländerungen können den Wertbeitrag beeinflussen; die Anzeige ist daher keine bereinigte Kursperformance.</div>
</section>"""

HISTORY_HEADER = """<div class="header"><div><h1>Gesamtdepotentwicklung</h1><div class="muted">Fortlaufende Entwicklung des Depotwerts über alle dokumentierten Stichtage</div></div><div class="badge" id="historyPeriodBadge"></div></div>"""

DYNAMIC_HISTORY_JS = r"""
/* dynamic-history-labels-v2 */
(function(){
  if(!Array.isArray(DATA.history)||!DATA.history.length)return;
  const parseD=s=>{const [d,m,y]=s.split('.').map(Number);return new Date(Date.UTC(y,m-1,d));};
  const first=DATA.history[0], last=DATA.history[DATA.history.length-1];
  const delta=last.value-first.value;
  const deltaPct=first.value?delta/first.value:0;
  const days=Math.round((parseD(last.date)-parseD(first.date))/86400000);
  const badge=document.getElementById('historyPeriodBadge');
  if(badge)badge.textContent=`${first.date} → ${last.date}`;
  const el=document.getElementById('historyKpis');
  if(el){
    const rows=[
      [`Erster Stichtag · ${first.date}`,eur.format(first.value),'Beginn der gespeicherten Zeitreihe'],
      [`Aktueller Stichtag · ${last.date}`,eur.format(last.value),'letzter erfolgreicher Depotstand'],
      ['Veränderung seit Beginn',eur.format(delta),(delta>=0?'+':'')+pct.format(deltaPct)],
      ['Historie',`${DATA.history.length} Stichtage`,`${days} Kalendertage`]
    ];
    el.innerHTML=rows.map(x=>`<div class="card kpi"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="note">${x[2]}</div></div>`).join('');
  }
})();
""".strip()

MOVERS_JS = r"""
/* movers-dashboard-v1 */
(function(){
  const m=DATA.movers, grid=document.getElementById('moversGrid');
  if(!m||!grid){return;}
  const badge=document.getElementById('moversAsOf');
  if(badge)badge.textContent=`Stand ${m.asof}${m.time?', '+m.time+' Uhr':''}`;
  const defs=[['day','Aktueller Tag'],['week','Aktuelle Woche'],['month','Aktueller Monat'],['total','Gesamt']];
  const signedPct=v=>(v>=0?'+':'')+pct.format(v);
  const signedEur=v=>(v>=0?'+':'')+eur.format(v);
  const side=(rows,kind)=>{
    if(!rows||!rows.length)return `<div class="mover-side ${kind}"><h4>${kind==='plus'?'Top 3 PLUS':'Top 3 MINUS'}</h4><div class="mover-empty">Noch nicht genügend Vergleichsdaten.</div></div>`;
    const max=Math.max(...rows.map(r=>Math.abs(r.pct)),.000001);
    return `<div class="mover-side ${kind}"><h4>${kind==='plus'?'Top 3 PLUS':'Top 3 MINUS'}</h4>${rows.map(r=>`<div class="mover-row"><div class="mover-name" title="${r.name}">${r.name}</div><div class="mover-pct">${signedPct(r.pct)}</div><div class="mover-eur">${signedEur(r.value)}</div><div class="mover-barbox"><div class="mover-bar" style="width:${Math.max(3,100*Math.abs(r.pct)/max)}%"></div></div></div>`).join('')}</div>`;
  };
  grid.innerHTML=defs.map(([key,title])=>{const p=m.periods[key]||{};const range=p.from?`${p.from} → ${p.to}`:'Vergleich noch nicht verfügbar';return `<div class="card mover-card"><div class="mover-period"><h3>${title}</h3><div class="mover-range">${range}</div></div><div class="mover-columns">${side(p.gainers,'plus')}${side(p.losers,'minus')}</div></div>`}).join('');
})();
""".strip()


def main() -> int:
    text = INDEX.read_text()
    original = text

    text = text.replace("Portfolio Lens", "Portfolio")
    prices_path = ROOT / "data/prices/latest.json"
    if prices_path.exists():
        prices = json.loads(prices_path.read_text())
        stamps = [x.get("fetched_at") for x in prices.get("prices", []) if x.get("fetched_at")]
        if stamps:
            newest = max(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
            local = newest.astimezone(ZoneInfo("Europe/Vienna"))
            stamp = local.strftime("%d.%m.%Y, %H:%M Uhr")
            text = re.sub(r"Look-through Dashboard · Stand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?", f"Look-through Dashboard · Stand {stamp}", text)
            text = re.sub(r"Datenstand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?", f"Datenstand {stamp}", text)

    if ".manual-update{" not in text:
        text = text.replace("</style>", STYLE + "\n</style>", 1)
    if "/* movers-dashboard-v1 */" not in text.split("</style>",1)[0]:
        text = text.replace("</style>", MOVERS_STYLE + "\n</style>", 1)
    if "/* responsive-dashboard-v2 */" not in text:
        text = text.replace("</style>", RESPONSIVE_STYLE + "\n</style>", 1)

    text = re.sub(r'<nav class="nav" id="nav">.*?</nav>', NAV, text, count=1, flags=re.S)
    text = re.sub(r'<section id="dashboard" class="page(?: active)?">', '<section id="dashboard" class="page">', text, count=1)
    text = re.sub(r'<section id="history" class="page(?: active)?">', '<section id="history" class="page active">', text, count=1)

    if re.search(r'<section id="movers" class="page(?: active)?">.*?</section>', text, flags=re.S):
        text = re.sub(r'<section id="movers" class="page(?: active)?">.*?</section>', MOVERS_SECTION, text, count=1, flags=re.S)
    else:
        marker = '<section id="dashboard" class="page">'
        if marker not in text:
            raise SystemExit("Dashboard section marker not found")
        text = text.replace(marker, MOVERS_SECTION + "\n\n" + marker, 1)

    history_section = re.search(r'<section id="history" class="page active">(.*?)<div class="grid kpis" id="historyKpis">', text, flags=re.S)
    if not history_section:
        raise SystemExit("History section/header not found")
    prefix = history_section.group(1)
    header_match = re.search(r'<div class="header">.*?</div>\s*$', prefix, flags=re.S)
    if not header_match:
        raise SystemExit("History header not found")
    new_prefix = prefix[:header_match.start()] + "\n " + HISTORY_HEADER + "\n "
    text = text[:history_section.start(1)] + new_prefix + text[history_section.end(1):]

    button_pattern = r'<a class="manual-update" id="manualUpdateLink".*?</a>\s*<span class="manual-update-note">.*?</span>'
    if re.search(button_pattern, text, flags=re.S):
        text = re.sub(button_pattern, BUTTON, text, count=1, flags=re.S)
    else:
        text = text.replace("</nav>", "</nav>\n" + BUTTON, 1)

    text = re.sub(r'/\* dynamic-history-labels-v2 \*/.*?\}\)\(\);\s*', '', text, flags=re.S)
    text = re.sub(r'/\* movers-dashboard-v1 \*/.*?\}\)\(\);\s*', '', text, flags=re.S)
    if "</script>" not in text:
        raise SystemExit("Closing script tag not found")
    text = text.replace("</script>", DYNAMIC_HISTORY_JS + "\n" + MOVERS_JS + "\n</script>", 1)

    if text != original:
        INDEX.write_text(text)
        print("Dashboard shell synchronized with movers and dynamic history labels.")
    else:
        print("Dashboard shell already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
