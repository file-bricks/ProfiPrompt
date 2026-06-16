# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Planung / Platform
- Portierungsplan am 2026-06-07 usecase-basiert aktualisiert: Windows Desktop bleibt Master-App und Store-Hauptkanal; Web/PWA bleibt read-only Companion für Web, Android und iOS; macOS/Linux bleiben Source-Smoke-Ziele; native Mobile-Voll-App, Cloud-Zwang und Server-Sync sind weiterhin Nicht-Ziele.

### Build / Release
- EXE neu gebaut 2026-06-01 (PyInstaller COLLECT, `ProfiPrompt.spec` → `C:\_Local_DEV\codex_build\profiprompt`); 34/34 Tests grün, Smoke-Test bestanden. Vorherige EXE: 2026-05-01. Anlass: pdf_exporter.py 2026-05-29. Hinweis: kein build_exe.bat vorhanden — direkter PyInstaller-Aufruf mit explizitem `--distpath`.
- Der Store-Preflight prüft `STORE_LISTING.md` jetzt strukturell auf beide Sprachblöcke, 100-Zeichen-Kurzbeschreibungen, nichtleere Schlüsselwort-/Kategorie-Felder und die Kategorie-Ausrichtung zu `store_package.json`; `AUFGABEN.txt`, `PORTIERUNGSPLAN.md` und README führen den Listing-Schritt damit als erledigt.

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
  fehlenden WACK-Report und die XML-Auswertung regressionssicher ab.
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
