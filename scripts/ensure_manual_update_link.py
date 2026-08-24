#!/usr/bin/env python3
"""Ensure the dashboard contains a safe link to the manual GitHub Actions update."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

STYLE = """
.manual-update{display:block;margin:18px 4px 0;padding:11px 12px;border:1px solid #36527a;border-radius:10px;background:#14263c;color:#dbeafe;text-decoration:none;font-weight:700;text-align:center}.manual-update:hover{background:#1b3554;color:white}.manual-update-note{display:block;margin:6px 8px 0;color:#71809e;font-size:10px;text-align:center}
""".strip()

BUTTON = """
<a class="manual-update" id="manualUpdateLink" href="https://github.com/oureal/alex-wertpapiere-dashboard/actions/workflows/update-portfolio-dashboard.yml" target="_blank" rel="noopener noreferrer">↻ Kurse jetzt aktualisieren</a>
<span class="manual-update-note">öffnet GitHub Actions</span>
""".strip()


def main() -> int:
    text = INDEX.read_text()
    changed = False

    if ".manual-update{" not in text:
        text = text.replace("</style>", STYLE + "\n</style>", 1)
        changed = True

    if 'id="manualUpdateLink"' not in text:
        marker = "</nav>"
        if marker not in text:
            raise SystemExit("Dashboard navigation marker not found")
        text = text.replace(marker, marker + "\n" + BUTTON, 1)
        changed = True

    if changed:
        INDEX.write_text(text)
        print("Manual update link added to dashboard.")
    else:
        print("Manual update link already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
