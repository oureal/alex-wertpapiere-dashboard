from pathlib import Path

from apply_dashboard_theme import STYLE, SCRIPT

HTML_PATH = Path("index.html")
STYLE_START = "/* dashboard-theme-v1:start */"
STYLE_END = "/* dashboard-theme-v1:end */"
SCRIPT_START = "<!-- dashboard-theme-v2:start -->"
SCRIPT_END = "<!-- dashboard-theme-v2:end -->"
SCRIPT_BLOCK = f'''{SCRIPT_START}\n<script>\n{SCRIPT}\n</script>\n{SCRIPT_END}'''


def replace_block(text: str, start: str, end: str, block: str) -> str:
    left, rest = text.split(start, 1)
    _, right = rest.split(end, 1)
    return left + block + right


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    if STYLE_START in html and STYLE_END in html:
        html = replace_block(html, STYLE_START, STYLE_END, STYLE)
    else:
        if "</style>" not in html:
            raise RuntimeError("Dashboard stylesheet anchor missing")
        html = html.replace("</style>", STYLE + "\n</style>", 1)

    if SCRIPT_START in html and SCRIPT_END in html:
        html = replace_block(html, SCRIPT_START, SCRIPT_END, SCRIPT_BLOCK)
    else:
        if "</body>" not in html:
            raise RuntimeError("Dashboard body anchor missing")
        html = html.replace("</body>", SCRIPT_BLOCK + "\n</body>", 1)

    HTML_PATH.write_text(html, encoding="utf-8")
    print("Applied idempotent persistent light/dark dashboard theme.")


if __name__ == "__main__":
    main()
