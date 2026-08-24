# Kostenlose Marktdatenabdeckung

## Sicherheitsstatus dieser Entwicklungsstufe

Die Marktdatenlogik ist providerunabhängig, aber es wurde **kein** Symbol geraten
und keine kostenpflichtige Funktion aktiviert. In der Ausführungsumgebung standen
weder `ALPHAVANTAGE_API_KEY` noch ausgehender Netzwerkzugriff zur Verfügung.
Deshalb ist die eingecheckte Coverage ein reproduzierbarer Offline-Bericht mit
Status `needs_review` für alle 23 Instrumente und null externen Requests.

Die geforderte Live-Recherche wurde gegen Websuche, Alpha Vantage, Börse
Frankfurt, iShares, boerse.de und WisdomTree versucht. Die Websuche antwortete mit
HTTP 401; sämtliche direkten HTTPS-Verbindungen wurden vom Umgebungsproxy mit
HTTP 403 abgewiesen. `data/market-data/research.json` protokolliert diese
Einschränkung. Ohne abrufbare Antwort konnten weder Aktualität noch Selektoren,
Feldsemantik oder Nutzbarkeit einer Quelle seriös getestet werden. Deshalb wurde
kein keyloser Adapter auf Basis einer unbestätigten URL implementiert.

`data/market-data/provider-mappings.yml` und die providerbezogene Prüftabelle
`data/market-data/yahoo-mappings.yml` sind die einzigen Stellen für
provider-spezifische Symbole. Portfolio- und Look-through-Berechnung enthalten
keine Yahoo- oder Alpha-Vantage-Symbole.

## Yahoo Finance / yfinance als primärer Testprovider

`data/market-data/yahoo-mappings.yml` enthält explizite Kandidaten. Ein Kandidat
ist noch keine statisch akzeptierte Zuordnung: Der GitHub-Actions-Test lädt über
`yfinance` Metadaten und akzeptiert einen Kurs nur, wenn Name, Quote-Typ, Währung
und Börse vorhanden und mit der Mapping-Erwartung vereinbar sind. Danach wird der
letzte positive `Close` verwendet; nur bei leerer Historie darf ein positiver
`regularMarketPrice` mit belegtem `regularMarketTime` einspringen.

Für Kurse ungleich EUR lädt dieselbe providerneutrale Teststufe einen
Yahoo-FX-Kurs `<WÄHRUNG>EUR=X` und speichert neben dem nativen Kurs einen
`valuation_price_eur`. Ohne positiven FX-Kurs wird der Livekurs nicht für die
EUR-Depotbewertung verwendet und der positive Legacy-Fallback bleibt aktiv.

Die beiden boerse.de-Fonds besitzen bewusst keinen Yahoo-Kandidaten. Ihre Kette
lautet `official_nav → manual_or_legacy_fallback`, bis ein stabiler offizieller
NAV-Endpunkt bestätigt ist. Alpha Vantage bleibt optionale Reserve und wird für
den manuellen Yahoo-Testworkflow nicht benötigt.

## Provider-Kaskade

1. `primary_provider`: bevorzugter kostenloser Adapter;
2. `fallback_provider`: später ergänzbarer zweiter kostenloser Adapter;
3. `manual_or_legacy_fallback`: letzter positiver, belegter Kurs.

Ein positiver Kurs vom selben UTC-Tag mit Status `fresh` wird aus dem Cache
verwendet. Bei Providerfehlern wird ein letzter positiver Kurs als `stale`
gekennzeichnet und eine Warnung erzeugt. Ohne positiven Kurs bricht die
Berechnung ab; ein Nullkurs wird niemals erzeugt.

## Alpha Vantage Free

- API-Key ausschließlich aus `ALPHAVANTAGE_API_KEY`;
- festes lokales Tageslimit: 25 Requests;
- lokale, nicht versionierte Verbrauchszählung unter `.cache/market-data/`;
- `SYMBOL_SEARCH` dient nur der Kandidatensuche;
- mehrere Kandidaten bleiben `ambiguous` und benötigen Prüfung;
- `GLOBAL_QUOTE` wird nur für ein explizit bestätigtes Mapping aufgerufen;
- keine Premium-Endpunkte und keine automatische kostenpflichtige Option.

Für eine kontrollierte, fortsetzbare Discovery steht zusätzlich bereit:

```bash
ALPHAVANTAGE_API_KEY=... python scripts/discover_market_data.py --max-requests 23
```

Mit wiederholtem `--instrument <interne-id>` kann die Suche begrenzt werden. Das
Ergebnis landet in einer ignorierten lokalen Datei, überspringt bereits
abgeschlossene Suchen und aktiviert niemals selbstständig ein Mapping.

Eine vollständige erstmalige Suche für 23 Instrumente benötigt 23 Requests. Sie
sollte deshalb an einem eigenen Tag durchgeführt werden: Für 23 zusätzliche
Kursabfragen blieben am selben Tag nur zwei Requests übrig. Nach Bestätigung aller
Mappings würde ein Kursabruf ohne Cache höchstens 23 Requests benötigen und damit
formal in das Limit von 25 passen, hätte aber nur zwei Requests Reserve. Instrumente,
die Alpha Vantage im kostenlosen Angebot nicht eindeutig abdeckt, müssen vor
einem produktiven Lauf auf einen weiteren kostenlosen Adapter umgestellt werden.

## Aktuelle Coverage und Empfehlung

| Instrument | ISIN | kostenlose Quelle/Kandidat | Provider | Symbol | Währung | letzter lokaler Kurs | Kurszeitpunkt | Status | automatisch |
|---|---|---|---|---|---|---:|---|---|---|
| Berkshire Hathaway B | US0846707026 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | BRK-B | EUR | 428.100000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Xetra-Gold | DE000A0S9GB0 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | 4GLD.DE | EUR | 124.420000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Allianz | DE0008404005 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | ALV.DE | EUR | 436.850000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Microsoft | US5949181045 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | MSFT | EUR | 411.800000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Eli Lilly and Company | US5324571083 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | LLY | EUR | 1091.800000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Siemens | DE0007236101 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | SIE.DE | EUR | 275.950000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| HSBC | GB0005405286 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | HBC1.DE | EUR | 17.670000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Apple | US0378331005 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | AAPL | EUR | 271.100000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Linde | IE000S9YS762 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | LIN | EUR | 418.600000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| boerse.de-Aktienfonds - V EUR ACC | LU2115464500 | offizieller NAV noch unbestätigt; Legacy-Fallback | official_nav | – | EUR | 137.540000 | 2026-08-21 | official_nav_required / fallback | nein |
| iShares Dow Jones Global Titans 50 UCITS ETF EUR Dis. (DE) | DE0006289382 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | EXI2.DE | EUR | 111.880000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| boerse.de-Technologiefonds - T EUR ACC | LU2479335734 | offizieller NAV noch unbestätigt; Legacy-Fallback | official_nav | – | EUR | 152.630000 | 2026-08-21 | official_nav_required / fallback | nein |
| Nvidia | US67066G1040 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | NVDA | EUR | 185.600000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| AMD | US0079031078 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | AMD | EUR | 400.300000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| iShares Core MSCI World UCITS ETF USD Acc. | IE00B4L5Y983 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | EUNL.DE | EUR | 126.185185 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Alphabet C (Google) | US02079K1079 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | GOOG | EUR | 288.300000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Micron Technology | US5951121038 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | MU | EUR | 817.500000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| iShares Edge MSCI World Value Factor UCITS ETF USD Acc. | IE00BP3QZB59 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | IS3S.DE | EUR | 69.840000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| WisdomTree Physical Bitcoin | GB00BJYDH287 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | WBIT.DE | EUR | 14.726000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Marvell Technology | US5738741041 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | MRVL | EUR | 206.700000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| TSMC Taiwan Semiconductor (ADR) | US8740391003 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | TSM | EUR | 355.000000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Broadcom | US11135F1012 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | AVGO | EUR | 310.850000 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
| Siemens Energy AG NA O.N. | DE000ENER6Y0 | Yahoo Finance, Live-Validierung im Workflow ausstehend | yfinance | ENR.DE | EUR | 154.04 | 2026-08-21 | candidate_live_validation / fallback | nach erfolgreichem Workflow-Test |
**Nächster kostenloser Prüfpfad:** Der manuelle GitHub-Actions-Lauf validiert die
21 Yahoo-Kandidaten und erzeugt eine run-spezifische Coverage. Für die beiden
boerse.de-Fonds bleibt ein offizieller NAV-Endpunkt vor einem Adapter zu
bestätigen; Alpha Vantage ist lediglich eine spätere optionale Reserve.
Insbesondere Xetra-Gold und WisdomTree Physical Bitcoin werden als gehaltene
Wertpapiere behandelt. Gold-Spot und Bitcoin-Spot sind unzulässige Ersatzpreise.
Dasselbe Prinzip gilt für Fonds und ETFs: Der Indexstand oder ein enthaltenes
Asset ist kein Preis des gehaltenen Instruments.

## Zwei boerse.de-Fonds

Der praktikabelste kostenlose Kandidat ist der offizielle, öffentlich zugängliche
Fonds-NAV beziehungsweise Anteilspreis des jeweiligen Emittenten. Die vorhandenen
Legacy-Unterlagen nennen offizielle Fondsseiten für Look-through-Daten; sie
belegen aber noch keinen stabilen maschinenlesbaren Preisendpunkt. Daher wurde
noch kein Scraper und kein Symbol eingetragen. Vor einem Adapter sind URL,
Aktualisierungszeit, Anteilsklasse, Währung, Nutzungsbedingungen und stabiler
Abruf technisch und fachlich zu bestätigen.

## Dry Run

`data/prices/latest.json` enthält für jedes Instrument einen positiven
Legacy-Fallback. `data/generated/dry-run-portfolio.json` wird ausschließlich aus
Stückzahlen, diesen Preisen, Cash und den Look-through-Quellgewichten berechnet.
Es überschreibt weder `index.html` noch historische Dateien.

Aktueller Dry-Run-Gesamtwert: **113.578,029995 EUR**. Sämtliche sechs
Summeninvarianten sind erfüllt. Die Preiswarnungen zeigen transparent, dass noch
keiner der 23 Kurse live aktualisiert wurde.
