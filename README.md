# ProfiPrompt

Ein Desktop-Tool zur Verwaltung, Versionierung und Organisation von AI-Prompts. Gebaut mit PySide6 (Qt6).

## Funktionen

- **Prompt-Verwaltung** -- Erstellen, Bearbeiten und Kategorisieren von Prompts
- **Versionierung** -- Mehrere Versionen pro Prompt mit vollstaendiger Historie
- **Board-System** -- Prompts in thematischen Boards mit Kachel-Ansicht organisieren
- **Drag & Drop** -- Prompts per Drag auf Boards anheften
- **Export** -- TXT- und PDF-Export (einzeln oder alle)
- **Clipboard-Integration** -- Schnelles Kopieren mit konfigurierbaren Modi (Titel, Text, Ergebnis, Alles)
- **Dark Mode** -- Modernes Fusion Dark Theme
- **Offline-First** -- Alle Daten lokal gespeichert (JSON)

## Screenshots

![Main Window](screenshots/main.png)

## Voraussetzungen

- Python 3.10+
- PySide6

## Installation

```bash
git clone https://github.com/lukisch/ProfiPrompt.git
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
├── tests/
│   └── test_basic.py           # Unit tests (26 tests)
├── requirements.txt
├── LICENSE
└── README.md
```

## Tests

```bash
python -m pytest tests/ -v
```

## EXE erstellen

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/profiprompt.py
```

## Autor

Lukas Geiger ([@lukisch](https://github.com/lukisch))

---

## English

A desktop tool for managing, versioning, and organizing AI prompts. Built with PySide6 (Qt6).

### Features

- **Prompt Management** -- Create, edit, and categorize prompts
- **Versioning** -- Multiple versions per prompt with full history
- **Board System** -- Organize prompts in thematic boards with tile view
- **Drag & Drop** -- Pin prompts to boards via drag
- **Export** -- TXT and PDF export (single or all)
- **Clipboard Integration** -- Quick copy with configurable modes (title, text, result, all)
- **Dark Mode** -- Modern Fusion Dark Theme
- **Offline-First** -- All data stored locally (JSON)

### Requirements

- Python 3.10+
- PySide6

### Installation

```bash
git clone https://github.com/lukisch/ProfiPrompt.git
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
├── tests/
│   └── test_basic.py           # Unit tests (26 tests)
├── requirements.txt
├── LICENSE
└── README.md
```

### Tests

```bash
python -m pytest tests/ -v
```

### Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/profiprompt.py
```

### Author

Lukas Geiger ([@lukisch](https://github.com/lukisch))

## License

[MIT](LICENSE)
