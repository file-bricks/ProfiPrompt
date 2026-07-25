# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

## [1.0.2] - 2026-07-26

### Discoverability, SEO & Doku-Wartung
- **PEP 621 Standardisierung:** Standardisierte `pyproject.toml` mit Projekt-Metadaten, Schlüsselwörtern, URLs und Pytest-Optionen (`pythonpath = "."`, `testpaths = ["tests"]`) angelegt.
- **Visual Badges & i18n:** Shields.io Badges (Python 3.10+, PySide6 Qt6, Pytest 103 passed, Web Companion 46 passed, Windows, Offline-first, LLM-Ready `llms.txt`) & Sprach-Umschalter (`[English](README.md) | [Deutsch](README_de.md)`) integriert.
- **GFM Callout & Systemarchitektur:** KI/LLM-Integrationshinweis (`> [!NOTE]`) für maschinenlesbaren Kontext und Mermaid-Systemarchitekturdiagramm in `README.md` und `README_de.md` eingebunden.
- **Deutsche Dokumentation:** Eigene deutsche `README_de.md` mit 100% i18n-Parität, Screenshot-Verweisen und rechtlichem Haftungsausschluss (§ 521 BGB) neu erstellt.
- **llms.txt Synchronisation:** Timestamp `Last-checked: 2026-07-26` und Testsuiten-Gesamtzahl (149 passed) in `llms.txt` verifiziert und synchronisiert.


### Neue Funktionen / Features
- **Welle-1 U1 — sichtbarer DE/EN-Sprachschalter** (`src/profiprompt.py`,
  `src/settings_manager.py`, `locales/translations.json`): Neues Menü „Sprache /
  Language" (Deutsch/English, exklusiv wählbar) in der Menüleiste. Die
  Menüleiste stellt sofort um (Live-Retranslate), tiefer liegende Texte folgen
  nach einem Neustart (Hinweis-Dialog). Die Auswahl wird in den bestehenden
  QSettings (`ui/language`) persistiert und beim Start geladen. Das bisher
  ungenutzte `translator.py` / `locales/translations.json` ist damit im UI
  verdrahtet (robuste locales-Auflösung für Source- und Frozen-Build; `.spec`
  nachgezogen). `translator.py` erhielt zusätzlich den isinstance-Guard gegen
  korrupte Einträge. Regressionstests: `tests/test_language_switch.py`.
- **Welle-1 U2 — Hell-/Dunkel-Theme umschaltbar** (`src/theme.py` (neu),
  `src/profiprompt.py`, `src/settings_manager.py`, `src/board_manager.py`): Neuer
  Menüpunkt „Bearbeiten → Darstellung …". Die Theme-Logik wurde aus
  `profiprompt.py` in ein eigenes Modul `theme.py` ausgelagert; neben dem
  bisherigen Dunkel-Theme gibt es jetzt eine sauber definierte Hell-Palette (kein
  bloßes Invertieren: eigene Fusion-Palette + Stylesheet). Die Board-Flächenfarbe
  folgt dem Theme (vorher hart `#252525`). Umschaltung erfolgt live (App-Palette
  wird zur Laufzeit neu gesetzt, Board-Kacheln + Tree-Icons neu gezeichnet). Die
  Auswahl wird in den QSettings (`ui/theme`) persistiert — analog zu `ui/language`.
  `apply_dark_theme` bleibt als Kompat-Wrapper (von `platform_smoke.py` /
  `generate_store_screenshots.py` genutzt). Regressionstests:
  `tests/test_appearance_u2_u3_u4.py`.
- **Welle-1 U3 — Kachelfarben konfigurierbar** (`src/theme.py`,
  `src/board_manager.py`, `src/settings_manager.py`, `src/appearance_dialog.py`
  (neu)): Getrennte Basis-Farbwahl für Haupt-Prompt- und Versionsprompt-Kacheln
  über einen `QColorDialog` im Darstellungs-Dialog. Aus der gewählten Farbe wird
  eine kohärente Kachel-Palette abgeleitet (Farbverlauf, Rand, Badge, lesbarer
  Text per Luminanz-Kontrast), damit jede Wunschfarbe stimmig wirkt. Persistenz
  in QSettings (`tiles/color_main`/`tiles/color_version`); Default = bisherige
  Farben (`#5D4037` / `#37474F`); „Zurücksetzen"-Knopf stellt die Standardfarben
  wieder her. Die zuvor hart kodierten Kachelfarben sind entfernt.
- **Welle-1 U4 — echte transparente UI-Icons** (`src/icons/*.png` (neu),
  `scripts/generate_ui_icons.py` (neu), `src/dashboard.py`): Die Clipboard- und
  Büroklammer-Icons in der Prompt-Liste waren eingebettete Rasterbilder ohne
  Alphakanal. Ersetzt durch schlanke, transparente Linien-Icons (128×128 PNG mit
  Alphakanal, aus SVG gerendert) in je einer hellen und dunklen Variante; die App
  wählt die theme-passende Variante, sodass die Icons auf hellem UND dunklem
  Hintergrund sichtbar sind (wichtig wegen U2). Die alten `clipboard.ico/.jpg`
  und `paperclip.ico/.jpg` wurden entfernt.

### Tests / Infrastruktur
- Neue `tests/conftest.py`: leitet die App-QSettings (IniFormat/UserScope)
  session-weit in ein Temp-Verzeichnis um (Tests schreiben nicht mehr in das echte
  `%APPDATA%\PromptManager`) und stellt eine gemeinsame `QApplication`-Fixture
  bereit. `tests/test_appearance_u2_u3_u4.py` deckt U2/U3/U4 ab (Persistenz,
  Theme-/Farbhelfer, Appearance-Dialog, Icon-Transparenz, Regressionsschutz gegen
  wieder eingeführte harte Farben). Suite: 103 passed / 3 skipped.

### Bugfixes (Bugsweep 2026-06-28 — Storage/Persistenz)
- **BUG-PS01 (KRIT):** `prompt_from_dict` in `models.py` krachte mit `KeyError: 'title'`
  bei alten oder fremden JSON-Exporten ohne `title`-Feld und riss den gesamten
  `load_prompts`-Aufruf mit. Fix: `title=d["title"]` → `title=d.get("title", "")`;
  konsistent mit der `version_from_dict`/`boarditem_from_dict`-Härtung aus Sweep 19.
  Regressionstests: `tests/test_bugsweep_storage_20260628.py`.
- **BUG-PS02 (MITTEL):** `load_prompts` und `load_boards` in `storage.py` fingen keinen
  `OSError` (inkl. `FileNotFoundError`, `PermissionError`) — eine zwischen `_ensure_files`
  und dem Lesezugriff gelöschte Datei (z.B. OneDrive-Lock, fehlgeschlagener `.tmp`-Rename)
  ließ die App hart crashen. Fix: `except`-Klausel um `OSError` erweitert.
  `UnicodeDecodeError` war bereits über `ValueError` abgedeckt (im Test verifiziert).
  74/74 Tests grün.

### Planung / Platform
- Portierungsplan am 2026-06-07 usecase-basiert aktualisiert: Windows Desktop bleibt Master-App und Store-Hauptkanal; Web/PWA bleibt read-only Companion für Web, Android und iOS; macOS/Linux bleiben Source-Smoke-Ziele; native Mobile-Voll-App, Cloud-Zwang und Server-Sync sind weiterhin Nicht-Ziele.

### Build / Release
- EXE neu gebaut 2026-06-01 (PyInstaller COLLECT, `ProfiPrompt.spec` → `C:\_Local_DEV\codex_build\profiprompt`); 34/34 Tests grün, Smoke-Test bestanden. Vorherige EXE: 2026-05-01. Anlass: pdf_exporter.py 2026-05-29. Hinweis: kein build_exe.bat vorhanden — direkter PyInstaller-Aufruf mit explizitem `--distpath`.
- Der Store-Preflight prüft `STORE_LISTING.md` jetzt strukturell auf beide Sprachblöcke, 100-Zeichen-Kurzbeschreibungen, nichtleere Schlüsselwort-/Kategorie-Felder und die Kategorie-Ausrichtung zu `store_package.json`; `AUFGABEN.txt`, `PORTIERUNGSPLAN.md` und README führen den Listing-Schritt damit als erledigt.
- GitHub-Repo-Hygiene aktualisiert: `LOCK*.txt` und `docs/superpowers/` bleiben ignoriert, `DesktopIcon.ico` und `DesktopIcon.png` sind als Quellassets dokumentiert, und Store-Readiness-Tests überspringen lokale Release-Artefaktprüfungen in sauberen CI-Checkouts.
- `scripts/check_store_readiness.py write-test-protocol` schreibt jetzt ein lokales Windows-Store-Testprotokoll mit repo-relativen Pfaden, MSIX-SHA256, Materialstatus und offenem WACK-Gate.

### Hinzugefügt / Added
- `EXPORTFORMAT.md` dokumentiert das stabile Austauschformat `profiprompt-library-v1.json`.
- Datei-Menü um `Bibliothek (JSON)` erweitert; der Export schreibt Prompts, Versionen, Boards, Board-Items, Tags, Zeitstempel und App-Metadaten als UTF-8-JSON.
- Neuer statischer Web/PWA-Companion unter `web_companion/` für Dateiimport, Suche, Boards, Versionsumschaltung, Kopierpfade und lokalen Browser-Speicher.
- Node-Smoke-Tests für den Companion prüfen Schema-Normalisierung, Filter, Board-Auflösung, Kopiertext und Restore aus `localStorage`.
- `web_companion/PWA_TESTPLAN.md` ergänzt die Android-/iOS-Testmatrix für Installation, Import, Offline-Start, Suche und Copy-Flows.
- Der Companion zeigt mobile Hinweise für Android/iOS direkt in der Oberfläche an.
- Neuer reproduzierbarer Desktop-Plattform-Smoke `src/platform_smoke.py` prüft Start, Storage, TXT/PDF-Export, `profiprompt-library-v1.json`, Clipboard und UTF-8-Umlaute in einem isolierten Ausgabeordner.
- Regressionstest `tests/test_platform_smoke.py` hält den Plattform-Smoke für macOS/Linux stabil.
- Neuer Generator `generate_store_screenshots.py` rendert vier feste
  Windows-Store-Screenshots aus redigierten Demo-Daten nach
  `README/screenshots/store/`; `tests/test_store_screenshots.py` sichert die
  PNG-Erzeugung und Grundstruktur ab.
- Neuer Store-Preflight `scripts/check_store_readiness.py` prüft
  `store_package.json`, `releases/windowsstore/store_settings.json`,
  `STORE_LISTING.md`, Screenshot-Summary, `releases/ProfiPrompt.msix` und
  vorhandene `wack_*.xml`-Reports reproduzierbar im Repo.
- `tests/test_store_readiness.py` deckt Store-Metadaten, Listing-Struktur,
  fehlenden WACK-Report, die XML-Auswertung und das neue lokale
  Store-Testprotokoll regressionssicher ab.
- `llms.txt` ergänzt kanonische Links, Interfaces, Datenschutzgrenzen und Validierungsbefehle für Crawler und LLM-Agenten.
- GitHub-Actions-Workflow `ProfiPrompt tests` prüft Python 3.10/3.11/3.12, Compile-Smoke und Web/PWA-Companion-Tests.
- Community-Workflows auf `actions/stale@v10` und `actions/first-interaction@v3` aktualisiert.

### Behoben / Fixed (web_companion)
- `service-worker.js`: fetch handler cachte 404s und opaque Responses ohne Statusprüfung — Guard `response.status !== 200 || response.type === "opaque"` ergänzt (Bug #1).
- `service-worker.js`: ASSETS-Liste enthielt nur `profiprompt-companion.svg`, aber die 4 PNG-Icons aus dem Manifest fehlten — Offline hatten Manifest-Icons keine Cache-Abdeckung; alle 4 PNGs in ASSETS ergänzt (Bug #2).
- `manifest.webmanifest`: `"id": "./"` ergänzt (PWA-Installierbarkeit gemäß Spec).
- `service-worker.js`: CACHE_NAME v1→v2; `skipWaiting()` in install-Handler; `clients.claim()` in activate-`waitUntil`-Kette.
- `service-worker.js`: Offline-Fetches nutzen `ignoreSearch: true`, damit gecachte Companion-Dateien auch bei Query-Parametern gefunden werden.
- `app.js`: Install-Prompt wird vor `prompt()` zurückgesetzt, damit schnelle Doppel-Klicks keinen zweiten Install-Dialog starten.
- `app.js`: gespeicherte Board-Auswahl fällt auf `all` zurück, wenn die importierte Bibliothek das alte Board nicht mehr enthält.
- `index.html`: `apple-touch-icon` ergänzt, damit iOS-Homescreen-Installationen ein passendes Icon erhalten.
- `app.js`: der `fallbackCopy()`-Textarea wird per `finally` entfernt, auch wenn `execCommand("copy")` eine Ausnahme wirft.
- `tests/pwa.test.mjs`: 22 neue Node-Tests; Gesamt 30/30 grün.

### Geplant / Planned
- Plattformstrategie in `PORTIERUNGSPLAN.md` fortgeschrieben: Windows Store bleibt Hauptkanal; Android/iOS folgen über PWA-Checks auf Basis des neuen Companions; der macOS/Linux-Smoke ist jetzt reproduzierbar dokumentiert.

### Behoben / Fixed
- Der Versions-PDF-Export respektiert jetzt die Metadaten-Einstellung auch dann, wenn er aus Dashboard oder Hauptfenster ausgelöst wird.
- Versionen werden im PDF-HTML weiterhin sauber escaped; die Regressionstests decken den Exportpfad jetzt explizit ab.
- Wenn mobile Browser die Zwischenablage sperren, fällt der Companion jetzt sichtbar auf ein manuelles Copy-Feld zurück statt still zu scheitern.
- `STORE_LISTING.md` und `releases/windowsstore/store_settings.json` wurden
  auf den aktuellen Export-/Companion-/Teststand sowie die korrekten
  GitHub-Privacy-/Support-Links gehoben.

## [1.0.1] - 2026-05-01

### Behoben / Fixed
- Board-Speicherung importiert `board_to_dict` explizit, damit `save_boards()` serialisieren kann.
- Einzelne Prompt- und Versions-TXT-Exports schreiben jetzt echten Plaintext statt den PDF-Exporter aufzurufen.

### Geändert / Changed
- README und Community-Dateien auf `file-bricks/ProfiPrompt` aktualisiert.
- README, Security-Policy, Privacy-Policy und Store-Listing auf Version 1.0.1 aktualisiert.
- App-About-Dialog und Store-Paketversion zeigen jetzt 1.0.1.
- Generierte Store-Staging-Artefakte werden nicht mehr als Repo-Quelldateien geführt.
- Regressionstests für einzelne TXT-Exports ergänzt; die Testsuite umfasst jetzt 28 Unit-Tests.

## [1.0.0] - 2026-02-28

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
- Prompt-Verwaltung (CRUD) mit Versionierung
- Board-System mit Kachel-Ansicht und Drag & Drop
- TXT- und PDF-Export (einzeln und alle)
- Clipboard-Integration mit konfigurierbaren Modi
- Modernes Dark Theme (Fusion)
- 26 Unit-Tests
