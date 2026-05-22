# ProfiPrompt

Ein Desktop-Tool zur Verwaltung, Versionierung und Organisation von AI-Prompts. Gebaut mit PySide6 (Qt6).

**Aktueller Stand:** Version 1.0.1 behebt die Board-Speicherung und stellt sicher, dass einzelne TXT-Exporte echten Plaintext schreiben. Der aktuelle Unreleased-Stand reicht die Metadaten-Einstellung auch an Versions-PDFs aus Hauptfenster und Dashboard weiter.

## Funktionen

- **Prompt-Verwaltung** -- Erstellen, Bearbeiten und Kategorisieren von Prompts
- **Versionierung** -- Mehrere Versionen pro Prompt mit vollständiger Historie
- **Board-System** -- Prompts in thematischen Boards mit Kachel-Ansicht organisieren
- **Drag & Drop** -- Prompts per Drag auf Boards anheften
- **Export** -- TXT- und PDF-Export (Prompts, Versionen oder alle)
- **Clipboard-Integration** -- Schnelles Kopieren mit konfigurierbaren Modi (Titel, Text, Ergebnis, Alles)
- **Dark Mode** -- Modernes Fusion Dark Theme
- **Offline-First** -- Alle Daten lokal gespeichert (JSON)
- **Robuste Speicherung** -- Prompts und Boards werden atomar geschrieben, um defekte JSON-Dateien bei Abbrüchen zu vermeiden

## Screenshots

![Main Window](screenshots/main.png)

## Voraussetzungen

- Python 3.10+
- PySide6

## Installation

```bash
git clone https://github.com/file-bricks/ProfiPrompt.git
cd ProfiPrompt
pip install -r requirements.txt
```

## Verwendung

```bash
python src/profiprompt.py
```

Unter Windows alternativ Doppelklick auf `START.bat`.

## Projektstruktur

```
ProfiPrompt/
├── src/
│   ├── profiprompt.py          # Hauptanwendung
│   ├── dashboard.py            # Dashboard-Widget (Prompt-Baum)
│   ├── board_manager.py        # Board-Verwaltung mit Kachel-Ansicht
│   ├── prompt_dialog.py        # Prompt/Version-Editor-Dialoge
│   ├── clipboard_manager.py    # Clipboard-Operationen
│   ├── copy_settings_dialog.py # Kopier-Einstellungen
│   ├── pdf_exporter.py         # PDF-Export via Qt
│   ├── storage.py              # Datenpersistenz (JSON)
│   ├── settings_manager.py     # Einstellungen (QSettings/INI)
│   ├── event_bus.py            # Event-System (Qt Signals)
│   ├── models.py               # Datenmodelle (Prompt, Version, Board)
│   └── icons/                  # Anwendungs-Icons
├── locales/
├── screenshots/
├── store_assets/
├── tests/
│   └── test_basic.py           # Unit tests (30 tests)
├── store_package.json
├── requirements.txt
├── LICENSE
└── README.md
```

## Tests

```bash
python -m pytest tests/ -v
```

Die Testsuite umfasst 30 Unit-Tests für Modelle, Storage, Clipboard-Textaufbau sowie TXT- und PDF-Exportpfade.

## Datenspeicherung / Privacy

ProfiPrompt arbeitet offline. Nutzerdaten werden standardmäßig im lokalen Benutzerprofil unter `.prompt_manager` gespeichert; es gibt keine Telemetrie, keine Cloud-Synchronisation und keine externen API-Aufrufe.

## EXE erstellen

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/profiprompt.py
```

Für reproduzierbare Windows-Builds kann die versionierte PyInstaller-Spezifikation genutzt werden:

```bash
python -m PyInstaller ProfiPrompt.spec --clean --noconfirm
```

## Autor

Lukas Geiger ([@lukisch](https://github.com/lukisch))

---

## English

A desktop tool for managing, versioning, and organizing AI prompts. Built with PySide6 (Qt6).

**Current status:** Version 1.0.1 fixes board persistence and ensures individual TXT exports write real plaintext. The current unreleased state also forwards the metadata setting to version PDF exports from the main window and dashboard.

### Features

- **Prompt Management** -- Create, edit, and categorize prompts
- **Versioning** -- Multiple versions per prompt with full history
- **Board System** -- Organize prompts in thematic boards with tile view
- **Drag & Drop** -- Pin prompts to boards via drag
- **Export** -- TXT and PDF export (prompts, versions, or all)
- **Clipboard Integration** -- Quick copy with configurable modes (title, text, result, all)
- **Dark Mode** -- Modern Fusion Dark Theme
- **Offline-First** -- All data stored locally (JSON)
- **Robust Persistence** -- Prompts and boards are written atomically to avoid broken JSON files after interrupted writes

### Requirements

- Python 3.10+
- PySide6

### Installation

```bash
git clone https://github.com/file-bricks/ProfiPrompt.git
cd ProfiPrompt
pip install -r requirements.txt
```

### Usage

```bash
python src/profiprompt.py
```

On Windows, you can also double-click `START.bat`.

### Project Structure

```
ProfiPrompt/
├── src/
│   ├── profiprompt.py          # Main application
│   ├── dashboard.py            # Dashboard widget (prompt tree)
│   ├── board_manager.py        # Board manager with tile view
│   ├── prompt_dialog.py        # Prompt/version editor dialogs
│   ├── clipboard_manager.py    # Clipboard operations
│   ├── copy_settings_dialog.py # Copy settings
│   ├── pdf_exporter.py         # PDF export via Qt
│   ├── storage.py              # Data persistence (JSON)
│   ├── settings_manager.py     # Settings (QSettings/INI)
│   ├── event_bus.py            # Event system (Qt Signals)
│   ├── models.py               # Data models (Prompt, Version, Board)
│   └── icons/                  # Application icons
├── locales/
├── screenshots/
├── store_assets/
├── tests/
│   └── test_basic.py           # Unit tests (30 tests)
├── store_package.json
├── requirements.txt
├── LICENSE
└── README.md
```

### Tests

```bash
python -m pytest tests/ -v
```

The test suite currently contains 30 unit tests for models, storage, clipboard text generation, and TXT/PDF export paths.

### Data Storage / Privacy

ProfiPrompt works offline. User data is stored by default in the local user profile under `.prompt_manager`; there is no telemetry, no cloud sync, and no external API access.

### Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/profiprompt.py
```

For reproducible Windows builds, use the versioned PyInstaller spec:

```bash
python -m PyInstaller ProfiPrompt.spec --clean --noconfirm
```

### Author

Lukas Geiger ([@lukisch](https://github.com/lukisch))

## License

[MIT](LICENSE)

---

## Haftung / Liability

Dieses Projekt ist eine **unentgeltliche Open-Source-Schenkung** im Sinne der §§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß **§ 521 BGB** auf **Vorsatz und grobe Fahrlässigkeit** beschränkt. Ergänzend gilt der Haftungsausschluss der MIT-Lizenz.

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie, keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation under the MIT License. Liability is limited to intent and gross negligence (§ 521 German Civil Code). Use at your own risk. No warranty, no maintenance guarantee, no fitness-for-purpose assumed.

