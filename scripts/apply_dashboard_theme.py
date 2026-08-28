from pathlib import Path

HTML_PATH = Path("index.html")
STYLE_START = "/* dashboard-theme-v1:start */"
STYLE_END = "/* dashboard-theme-v1:end */"
SCRIPT_START = "// dashboard-theme-v1:start"
SCRIPT_END = "// dashboard-theme-v1:end"

STYLE = r'''/* dashboard-theme-v1:start */
:root{
  color-scheme:dark;
  --theme-bg-a:#08101f;--theme-bg-b:#111827;--theme-bg-c:#0b1327;
  --theme-sidebar:rgba(8,14,28,.94);--theme-panel:rgba(20,27,45,.94);--theme-panel-solid:#141b2d;
  --theme-panel-2:#1b2440;--theme-input:#0e1729;--theme-line:#2a3656;
  --theme-text:#eef2ff;--theme-muted:#9aa7c2;--theme-heading:#ffffff;
  --theme-table-head:#1a2440;--theme-table-row:#19233a;--theme-track:#26314e;
  --theme-badge-bg:#14263c;--theme-badge-border:#284663;--theme-badge-text:#a7d8ff;
  --theme-shadow:0 12px 40px rgba(0,0,0,.16);--theme-tooltip:#07101f;
  --theme-notice:#2b2514;--theme-notice-text:#fde68a;--theme-pill:#24304d;
  --theme-positive:#86efac;--theme-negative:#fda4af;
}
html[data-theme="light"]{
  color-scheme:light;
  --bg:#f4f7fb;--panel:#ffffff;--panel2:#edf3fb;--text:#172033;--muted:#61708a;--line:#d7e0ec;
  --accent:#13a878;--accent2:#3579d6;--warn:#c58300;--danger:#d7475f;
  --theme-bg-a:#f8fbff;--theme-bg-b:#eef4fb;--theme-bg-c:#f6f1ff;
  --theme-sidebar:rgba(255,255,255,.96);--theme-panel:rgba(255,255,255,.96);--theme-panel-solid:#ffffff;
  --theme-panel-2:#e9f1fb;--theme-input:#ffffff;--theme-line:#d7e0ec;
  --theme-text:#172033;--theme-muted:#61708a;--theme-heading:#101827;
  --theme-table-head:#eaf1fb;--theme-table-row:#f2f7fc;--theme-track:#dce6f2;
  --theme-badge-bg:#e7f3ff;--theme-badge-border:#bad8f3;--theme-badge-text:#245b89;
  --theme-shadow:0 12px 32px rgba(49,76,112,.10);--theme-tooltip:#ffffff;
  --theme-notice:#fff7df;--theme-notice-text:#765200;--theme-pill:#e8f0fb;
  --theme-positive:#087f5b;--theme-negative:#c7354d;
}
body{background:linear-gradient(135deg,var(--theme-bg-a),var(--theme-bg-b) 55%,var(--theme-bg-c));color:var(--theme-text);transition:background .2s ease,color .2s ease}
.sidebar{background:var(--theme-sidebar);border-color:var(--theme-line)}
.brand,.header h1,.card h3,.detail h2{color:var(--theme-heading)}
.sub,.muted,.kpi .label,.kpi .note,.mover-range,.mover-empty{color:var(--theme-muted)}
.nav button{color:var(--theme-muted)}
.nav button:hover,.nav button.active{background:var(--theme-panel-2);color:var(--theme-heading)}
.nav .n{background:var(--theme-panel-2);color:var(--theme-text)}
.card{background:var(--theme-panel);border-color:var(--theme-line);box-shadow:var(--theme-shadow)}
.badge{background:var(--theme-badge-bg);border-color:var(--theme-badge-border);color:var(--theme-badge-text)}
.bar-track,.risk-meter,.mover-barbox{background:var(--theme-track)}
.table-wrap,.mover-side{border-color:var(--theme-line)}
th,td,.mover-row{border-color:var(--theme-line)}
th{background:var(--theme-table-head);color:var(--theme-text)}
tr:hover td{background:var(--theme-table-row)}
.controls input,.controls select{background:var(--theme-input);color:var(--theme-text);border-color:var(--theme-line)}
.treemap{background:var(--theme-input)}
.tooltip{background:var(--theme-tooltip);color:var(--theme-text);border-color:var(--theme-line);box-shadow:var(--theme-shadow)}
.donut:after{background:var(--theme-panel-solid)}
.notice{background:var(--theme-notice);color:var(--theme-notice-text)}
.pill{background:var(--theme-pill);color:var(--theme-text)}
.footer{color:var(--theme-muted)}
.manual-update{background:var(--theme-badge-bg);border-color:var(--theme-badge-border);color:var(--theme-text)}
.manual-update:hover{background:var(--theme-panel-2);color:var(--theme-heading)}
.manual-update-note{color:var(--theme-muted)}
.mover-side h4{background:var(--theme-panel-2)}
.mover-side.plus h4,.mover-side.plus .mover-pct,.mover-side.plus .mover-eur{color:var(--theme-positive)}
.mover-side.minus h4,.mover-side.minus .mover-pct,.mover-side.minus .mover-eur{color:var(--theme-negative)}
.donut-callout text{fill:var(--theme-text)}
.donut-callout .name-label{fill:var(--theme-muted)}
.history-switch button{background:var(--theme-input);color:var(--theme-text);border-color:var(--theme-line)}
.history-switch button.active{background:#3579d6;color:#fff}
.theme-toggle{position:fixed;right:18px;top:18px;z-index:1000;display:inline-flex;align-items:center;gap:8px;padding:9px 12px;border:1px solid var(--theme-line);border-radius:999px;background:var(--theme-panel);color:var(--theme-text);box-shadow:var(--theme-shadow);cursor:pointer;font-weight:750;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
.theme-toggle:hover{transform:translateY(-1px)}
.theme-toggle:focus-visible{outline:3px solid rgba(53,121,214,.35);outline-offset:2px}
.theme-toggle-icon{font-size:16px;line-height:1}.theme-toggle-label{font-size:12px;white-space:nowrap}
html[data-theme="light"] .tile{border-color:rgba(255,255,255,.72)}
html[data-theme="light"] .card{box-shadow:0 10px 30px rgba(41,72,112,.09)}
html[data-theme="light"] .kpi .value{color:#13213a}
html[data-theme="light"] a{color:#236bb2}
@media(max-width:1000px){.theme-toggle{top:12px;right:12px}.brand{padding-right:116px}}
@media(max-width:650px){.theme-toggle{top:9px;right:9px;padding:8px 10px}.theme-toggle-label{font-size:11px}.brand{padding-right:108px}}
/* dashboard-theme-v1:end */'''

SCRIPT = r'''// dashboard-theme-v1:start
(function(){
  const STORAGE_KEY = 'alex-wertpapiere-theme';
  const root = document.documentElement;
  const saved = localStorage.getItem(STORAGE_KEY);
  const initial = saved === 'light' || saved === 'dark' ? saved : 'dark';
  root.dataset.theme = initial;

  function label(theme){ return theme === 'light' ? 'Dunkel' : 'Hell'; }
  function icon(theme){ return theme === 'light' ? '☾' : '☀'; }
  function sync(button){
    const theme = root.dataset.theme || 'dark';
    button.setAttribute('aria-label', theme === 'light' ? 'Dunkles Design aktivieren' : 'Helles Design aktivieren');
    button.setAttribute('title', theme === 'light' ? 'Zum dunklen Design wechseln' : 'Zum hellen Design wechseln');
    button.querySelector('.theme-toggle-icon').textContent = icon(theme);
    button.querySelector('.theme-toggle-label').textContent = label(theme);
  }

  function mount(){
    if (document.getElementById('themeToggle')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'themeToggle';
    button.className = 'theme-toggle';
    button.innerHTML = '<span class="theme-toggle-icon" aria-hidden="true"></span><span class="theme-toggle-label"></span>';
    button.addEventListener('click', function(){
      const next = (root.dataset.theme || 'dark') === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      localStorage.setItem(STORAGE_KEY, next);
      sync(button);
      window.dispatchEvent(new CustomEvent('dashboard-theme-change', {detail:{theme:next}}));
    });
    document.body.appendChild(button);
    sync(button);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
// dashboard-theme-v1:end'''


def replace_or_insert(text: str, start: str, end: str, block: str, anchor: str) -> str:
    if start in text and end in text:
        prefix, rest = text.split(start, 1)
        _, suffix = rest.split(end, 1)
        return prefix + block + suffix
    if anchor not in text:
        raise RuntimeError(f"Missing HTML anchor {anchor!r}")
    return text.replace(anchor, block + "\n" + anchor, 1)


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    html = replace_or_insert(html, STYLE_START, STYLE_END, STYLE, "</style>")
    html = replace_or_insert(html, SCRIPT_START, SCRIPT_END, "<script>\n" + SCRIPT + "\n</script>", "</body>")
    HTML_PATH.write_text(html, encoding="utf-8")
    print("Applied persistent light/dark dashboard theme.")


if __name__ == "__main__":
    main()
