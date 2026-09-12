# ProfiPrompt - Windows Store Build-Anleitung

Stand: 2026-06-14

## Voraussetzungen

1. Python 3.10+ mit PySide6
2. PyInstaller (`pip install pyinstaller`)
3. Windows App Certification Kit / Windows SDK
4. Aktuelles MSIX `releases\ProfiPrompt.msix`
5. Für echten Store-Lauf: Publisher-/Identity-Werte passend zu `store_package.json`

## Schritt 1: EXE bauen und Store-Artefakte prüfen

```bash
cd "C:\_Local_DEV\repos\ProfiPrompt"
build_exe.bat
python scripts/check_store_readiness.py
```

Der Preflight prüft `store_package.json`, `STORE_LISTING.md`,
`releases/windowsstore/store_settings.json`, die Store-Screenshot-Summary,
`releases\ProfiPrompt.msix` und vorhandene WACK-Reports.
Für `STORE_LISTING.md` validiert er zusätzlich beide Sprachabschnitte, die
Kurzbeschreibungen, Schlüsselwörter, Kategorien und die Ausrichtung zur
Store-Konfiguration.

Ein lokales Testprotokoll für den aktuellen Paketstand wird so erzeugt:

```bash
python scripts/check_store_readiness.py write-test-protocol
```

Das Protokoll liegt unter `releases\windowsstore\test_reports\`, enthält
MSIX-SHA256, Materialstatus und markiert fehlende WACK-XML ausdrücklich als
offenes Gate.

## Schritt 2: WACK-Testprotokoll erneuern

1. `releases\ProfiPrompt.msix` im Windows App Certification Kit prüfen.
2. XML-Report unter `releases\windowsstore\test_reports\wack_YYYYMMDD_HHMMSS.xml` speichern.
3. Report lokal auswerten:

```bash
python scripts/check_store_readiness.py review-wack-report
```

## Schritt 3: Store Submission

Vor dem Partner-Center-Upload noch einmal ausführen:

```bash
python scripts/check_store_readiness.py
```

Preis: kostenlos
