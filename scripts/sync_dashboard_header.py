#!/usr/bin/env python3
# This script is intentionally the single safe header synchronizer used by the production workflow.
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PRICES = ROOT / "data/prices/latest.json"


def latest_stamp() -> str | None:
    if not PRICES.exists():
        return None
    doc = json.loads(PRICES.read_text())
    stamps = [x.get("fetched_at") for x in doc.get("prices", []) if x.get("fetched_at")]
    if not stamps:
        return None
    newest = max(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
    local = newest.astimezone(ZoneInfo("Europe/Vienna"))
    return local.strftime("%d.%m.%Y, %H:%M Uhr")


def main() -> int:
    text = INDEX.read_text()
    original = text
    text = text.replace("Portfolio Lens", "Portfolio")
    stamp = latest_stamp()
    if stamp:
        text = re.sub(r'<div class="sub">.*?</div>', f'<div class="sub">Stand {stamp}</div>', text, count=1, flags=re.S)
        text = re.sub(r'Datenstand \d{2}\.\d{2}\.\d{4}(?:, \d{2}:\d{2} Uhr)?', f'Datenstand {stamp}', text)
    else:
        text = re.sub(r'<div class="sub">\s*Look-through Dashboard\s*·?\s*(.*?)</div>', r'<div class="sub">\1</div>', text, count=1, flags=re.S)

    sidebar = re.search(r'<div class="sub">.*?</div>', text, flags=re.S)
    if not sidebar:
        raise SystemExit("Sidebar status element missing")
    if "Look-through Dashboard" in sidebar.group(0):
        raise SystemExit("Sidebar label removal failed")

    if text != original:
        INDEX.write_text(text)
        print("Dashboard header synchronized.")
    else:
        print("Dashboard header already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
