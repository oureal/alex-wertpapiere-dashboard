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


def main() -> int:
    text = INDEX.read_text()
    original = text

    text = text.replace("Portfolio Lens", "Portfolio")
    if ".manual-update{" not in text:
        text = text.replace("</style>", STYLE + "\n</style>", 1)
    if "/* responsive-dashboard-v2 */" not in text:
        text = text.replace("</style>", RESPONSIVE_STYLE + "\n</style>", 1)

    text = re.sub(r'<nav class="nav" id="nav">.*?</nav>', NAV, text, count=1, flags=re.S)
    text = re.sub(r'<section id="dashboard" class="page(?: active)?">', '<section id="dashboard" class="page">', text, count=1)
    text = re.sub(r'<section id="history" class="page(?: active)?">', '<section id="history" class="page active">', text, count=1)

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
    if "</script>" not in text:
        raise SystemExit("Closing script tag not found")
    text = text.replace("</script>", DYNAMIC_HISTORY_JS + "\n</script>", 1)

    if text != original:
        INDEX.write_text(text)
        print("Dashboard shell synchronized with dynamic history labels.")
    else:
        print("Dashboard shell already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
