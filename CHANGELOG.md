# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Behoben / Fixed
- Der Versions-PDF-Export respektiert jetzt die Metadaten-Einstellung auch dann, wenn er aus Dashboard oder Hauptfenster ausgelöst wird.
- Versionen werden im PDF-HTML weiterhin sauber escaped; die Regressionstests decken den Exportpfad jetzt explizit ab.

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
