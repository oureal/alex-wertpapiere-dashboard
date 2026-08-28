#!/usr/bin/env python3
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "index.html"
NOTICE = '<div class="notice">Die Excel-Datei enthält Sektoren, Unternehmen und Quellen, aber keine belastbaren Länder- oder Währungsfelder für sämtliche 1.288 Unternehmen. Daher werden hier keine Länderquoten geschätzt oder erfunden.</div>'

text = INDEX.read_text(encoding="utf-8")
text = text.replace(NOTICE, "")
if "Die Excel-Datei enthält Sektoren, Unternehmen und Quellen" in text:
    raise SystemExit("Regions explanatory notice removal failed")
INDEX.write_text(text, encoding="utf-8")
print("Regions explanatory notice removed.")
