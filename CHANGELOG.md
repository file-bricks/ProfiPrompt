# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- `EXPORTFORMAT.md` dokumentiert das stabile Austauschformat `profiprompt-library-v1.json`.
- Datei-Menü um `Bibliothek (JSON)` erweitert; der Export schreibt Prompts, Versionen, Boards, Board-Items, Tags, Zeitstempel und App-Metadaten als UTF-8-JSON.
- Neuer statischer Web/PWA-Companion unter `web_companion/` für Dateiimport, Suche, Boards, Versionsumschaltung, Kopierpfade und lokalen Browser-Speicher.
- Node-Smoke-Tests für den Companion prüfen Schema-Normalisierung, Filter, Board-Auflösung, Kopiertext und Restore aus `localStorage`.
- `web_companion/PWA_TESTPLAN.md` ergänzt die Android-/iOS-Testmatrix für Installation, Import, Offline-Start, Suche und Copy-Flows.
- Der Companion zeigt mobile Hinweise für Android/iOS direkt in der Oberfläche an.

### Geplant / Planned
- Plattformstrategie in `PORTIERUNGSPLAN.md` ergänzt: Windows Store bleibt Hauptkanal; Android/iOS folgen über PWA-Checks auf Basis des neuen Companions; macOS/Linux werden als P3-Smoke-Ziele geführt.

### Behoben / Fixed
- Der Versions-PDF-Export respektiert jetzt die Metadaten-Einstellung auch dann, wenn er aus Dashboard oder Hauptfenster ausgelöst wird.
- Versionen werden im PDF-HTML weiterhin sauber escaped; die Regressionstests decken den Exportpfad jetzt explizit ab.
- Wenn mobile Browser die Zwischenablage sperren, fällt der Companion jetzt sichtbar auf ein manuelles Copy-Feld zurück statt still zu scheitern.

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
