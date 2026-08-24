# Datenmodell

## Grundsätze

Das neue Datenmodell trennt unveränderliche Legacy-Quellen, Instrumentstammdaten,
Depotbestände, Bargeld, Transaktionen und Look-through-Aliasse. Das sichtbare
Dashboard wird in dieser Phase nicht verändert. JSON ist eine gültige Teilmenge
von YAML; die `.yml`-Dateien sind bewusst als streng validierbares JSON-formatiertes
YAML gespeichert und benötigen deshalb noch keine externe Python-Abhängigkeit.

## Unveränderliche Legacy-Daten

- `dashboard/history/*` und `data/snapshots/*` sind unveränderlich.
- `data/legacy/immutable-history-sha256.json` registriert jede vorhandene Datei
  mit SHA-256.
- `scripts/verify_immutable_history.py` lehnt fehlende, zusätzliche oder
  veränderte Dateien in diesen beiden Verzeichnissen ab.
- `data/legacy/index-data-2026-08-21.json` ist das bytegenau aus `index.html`
  extrahierte JSON-Objekt hinter `const DATA=`. Es wurde weder neu formatiert noch
  fachlich korrigiert.

## Instrumente

`data/portfolio/instruments.yml` enthält pro Instrument:

- stabile interne `id`;
- Name, ISIN und WKN, soweit in der Juli-Arbeitsmappe, in der vorgegebenen
  Siemens-Energy-Transaktion oder durch bestätigte Benutzereingabe belegt;
- Asset-Typ;
- die in der Legacy-Arbeitsmappe ausdrücklich als EUR bezeichnete Kurswährung;
- noch leere Felder für Ticker, Börsenplatz und Kursquelle;
- eine maschinenlesbare Liste `missing_fields`.

Eine EUR-Angabe bedeutet nur, dass der belegte Legacy-Referenzkurs in EUR geführt
wurde. Sie ist keine Behauptung über Heimatbörse oder Original-Handelswährung.

## Depotbestände

`data/portfolio/holdings.csv` bewahrt `Depot 1` und `Depot 2` als getrennte
Bestände. Die Werte stammen aus dem August-Snapshot und dem aktuellen Dashboard.
Die im Juli belegten Gesamtstückzahlen wurden bei Berkshire Hathaway und Allianz
anhand der beiden im August belegten Depotwerte auf die Konten verteilt. Diese
Herkunft ist je Zeile in `quantity_provenance` dokumentiert.

Die Stückzahlen für Xetra-Gold, die fünf Fonds/ETFs, WisdomTree Physical Bitcoin,
Marvell und Broadcom wurden am 24.08.2026 ausdrücklich als Benutzereingabe
bestätigt. `derived_legacy_unit_price_eur` ist für diese Positionen lediglich der
Quotient aus dokumentiertem Legacy-Marktwert und bestätigter Stückzahl. Dieser
Wert prüft die rechnerische Plausibilität, ist aber keine unabhängige Kursquelle.

## Bargeld und Siemens Energy

`cash.csv` führt die Konten getrennt. Der Kauf von vier Siemens-Energy-Aktien zu
154,04 EUR ist in `transactions.csv` als Bruttowert 616,16 EUR und Cash-Effekt
-616,16 EUR modelliert. Er ist somit wertneutral.

Der August-Snapshot belegt 293,21 EUR Cash in Depot 1 und 5.088,70 EUR in Depot 2.
Die Depotzuordnung des Kaufs zu Depot 2 ist inzwischen ausdrücklich vom Benutzer
bestätigt; es ist dasselbe Depot, das auch Broadcom enthält. Der Cashbestand von
Depot 2 wurde deshalb um 616,16 EUR auf 4.472,54 EUR reduziert und die Transaktion
mit `needs_confirmation=false` gekennzeichnet.

## Look-through-Aliasse

`data/lookthrough/aliases.yml` enthält ausschließlich eindeutig belegbare
Namensvarianten zwischen Excel und Dashboard. Die eigentlichen Fonds-Holdings
werden in einer späteren Phase normalisiert; die historischen Excel-Dateien
bleiben ihre unveränderte Quelle.

## Sicher übernommene Angaben

- zwei getrennte Depots und deren Positionen im August-Snapshot;
- 13 ISIN-/WKN-/Stückzahl-Sätze aus dem Juli-Direktbestand;
- neun zusätzlich bestätigte ISIN-/WKN-/Stückzahl-Sätze vom 24.08.2026;
- aktuelle konsolidierte Unternehmens-, Asset- und Cashwerte aus `index.html`;
- Siemens-Energy-ISIN, Stückzahl, Preis, Wert, Datum und Cash-Finanzierung aus der
  vorgegebenen Transaktion;
- die Look-through-Aggregate und historischen Depotwerte exakt und ohne
  Korrektur als Legacy-Referenz.

## Noch fehlende Angaben

Für eine automatische Kursversorgung fehlen derzeit bei allen Instrumenten
Ticker, Börsenplatz und Kursquelle. Der jeweils aktuelle vollständige Stand ist
maschinenlesbar in
`data/legacy/validation-report.json` enthalten.

Außerdem zu bestätigen sind:

- unveränderte Stückzahlen zwischen Juli- und August-Stichtag;
- tatsächliche Handelsplätze und gewünschte Kursreferenzen;
- Original-Handelswährungen, sofern nicht der belegte EUR-Referenzkurs verwendet
  werden soll.
