# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Behoben / Fixed
- Board-Speicherung importiert `board_to_dict` explizit, damit `save_boards()` serialisieren kann.

### Geändert / Changed
- README und Community-Dateien auf `file-bricks/ProfiPrompt` aktualisiert.
- Generierte Store-Staging-Artefakte werden nicht mehr als Repo-Quelldateien geführt.

## [1.0.0] - 2026-02-28

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
- Prompt-Verwaltung (CRUD) mit Versionierung
- Board-System mit Kachel-Ansicht und Drag & Drop
- TXT- und PDF-Export (einzeln und alle)
- Clipboard-Integration mit konfigurierbaren Modi
- Modernes Dark Theme (Fusion)
- 26 Unit-Tests
