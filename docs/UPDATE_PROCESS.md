# Update-Prozess

## Aktueller Umfang

Diese Migrationsphase schützt und extrahiert Legacy-Daten und führt ein erstes
Stammdatenmodell ein. Es gibt ausdrücklich noch keine Kurs-, FX- oder sonstige
externe API, keinen automatischen GitHub-Workflow und keine Veröffentlichung.

## Lokale Prüfung

Vom Repository-Wurzelverzeichnis aus:

```bash
python scripts/verify_immutable_history.py
python scripts/extract_legacy_data.py --check
python scripts/validate_data.py --check-report
pytest -q
```

Jeder dieser Befehle muss vor einer Änderung am Datenmodell erfolgreich sein.

Die kostenlose Marktdatenstufe wird offline reproduziert mit:

```bash
python scripts/market_data.py
python scripts/calculate_dry_run.py
```

Eine Alpha-Vantage-Kandidatensuche bleibt als optionale Reserve ausschließlich
explizit zulässig:

```bash
ALPHAVANTAGE_API_KEY=... python scripts/discover_market_data.py --max-requests 23
```

Sie verbraucht für 23 Instrumente 23 der maximal 25 kostenlosen Tagesrequests.
Der Key darf nur als Umgebungsvariable gesetzt und niemals committed werden.

## Manueller GitHub-Actions-Marktdatentest

`.github/workflows/market-data-test.yml` läuft ausschließlich über
`workflow_dispatch`. In GitHub unter **Actions → Private market-data test → Run
workflow** den gewünschten privaten Branch wählen und den Lauf starten. Es gibt
keinen Zeitplan, keinen Push-Trigger und keine Schreibberechtigung auf Repository-
Inhalte.

Der Workflow benötigt kein Secret. Er installiert `yfinance`, validiert die
expliziten Yahoo-Kandidaten zur Laufzeit gegen Name, Instrumenttyp, Währung und
Börse und verwendet nur positive, zeitgestempelte Kurse. Alpha Vantage ist in
diesem Workflow nicht erforderlich und bleibt lediglich eine spätere Reserve.

Nach dem Lauf befindet sich auf dessen Übersichtsseite unter **Artifacts** das
private Archiv `market-data-test-<run-id>`. Es enthält Yahoo-Coverage, geprüfte Mapping-Kandidaten,
Netzwerkdiagnose, Preiscache, Dry-Run-Portfolio und Validierungsbericht und wird
nach sieben Tagen gelöscht.

Der Workflow arbeitet nur in `.artifacts/`, prüft zum Schluss `git diff
--exit-code` und führt weder Commit, Push, Mapping-Akzeptanz, Snapshot-Erzeugung
noch Änderung von `index.html` durch.

## Legacy-Regel

Bestehende Dateien unter `dashboard/history/` und `data/snapshots/` dürfen nie
geändert, umbenannt oder gelöscht werden. Auch das Hinzufügen einer Datei in
diese Verzeichnisse erfordert in einer späteren Snapshot-Phase eine explizite
Manifest-Erweiterung. Der Prüfer behandelt nicht registrierte Dateien derzeit
absichtlich als Fehler.

Das Hash-Manifest darf nicht verwendet werden, um eine unbeabsichtigte Änderung
nachträglich zu legitimieren. Bei einem Hashfehler ist die Legacy-Datei aus Git
wiederherzustellen, nicht der erwartete Hash zu ersetzen.

## Reproduzierbare Extraktion

Die gespeicherte Referenz wird nur dann neu erzeugt, wenn bewusst ein neuer
Legacy-Ausgangspunkt beschlossen wurde:

```bash
python scripts/extract_legacy_data.py
```

Im normalen Prüfprozess ist ausschließlich `--check` zu verwenden. Dieser Modus
vergleicht die gespeicherten Bytes mit dem unverändert eingebetteten Objekt aus
`index.html`.

## Datenänderungen

1. Beleg (Abrechnung, Depotexport oder offizielles Fondsdokument) sichern.
2. Instrumentstammdaten ergänzen, ohne fehlende Werte zu schätzen.
3. Bestand und Transaktion depotgetrennt eintragen.
4. Cash-Effekt derselben Transaktion erfassen.
5. Alias nur ergänzen, wenn die Identität eindeutig ist.
6. Validierungsbericht neu erzeugen:

   ```bash
   python scripts/validate_data.py
   ```

7. Tests ausführen und den Bericht prüfen.

## Bekannte Legacy-Abweichungen

`validate_data.py` unterscheidet harte Fehler von bereits vorhandenen Warnungen.
Die Abweichungen zwischen `meta`, `assets`, `sectors` und `sources` werden unter
`known_legacy_inconsistencies` mit `corrected=false` protokolliert. Sie werden
weder in der Referenz noch in historischen Dateien korrigiert. Auch die kleine
Abweichung der aus verschiedenen Legacy-Abschnitten übernommenen Marktwerte zur
Meta-Gesamtsumme bleibt sichtbar.

Der Bericht enthält außerdem `legacy_value_plausibility`. Für bestätigte
Stückzahlen wird dort geprüft, ob Stückzahl mal abgeleitetem Legacy-Einheitspreis
den dokumentierten Depotwert centgenau reproduziert. Abgesehen vom ausdrücklich
belegten Siemens-Energy-Kauf ist der Einheitspreis aus Wert geteilt durch
Stückzahl abgeleitet und daher keine unabhängige Kursfeststellung.

## Datenschutz

- ausschließlich im privaten Repository arbeiten;
- kein GitHub Pages und kein öffentlicher Branch;
- keine Depotdaten an externe Dienste übertragen;
- `.env`, lokale Secrets und virtuelle Umgebungen werden nicht committed;
- für spätere Automatisierung zunächst eine gesonderte Datenschutz- und
  Providerentscheidung treffen.
