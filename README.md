# ProfiPrompt

A desktop tool for managing, versioning, and organizing AI prompts. Built with PySide6 (Qt6).

## Features

- **Prompt Management** -- Create, edit, and categorize prompts
- **Versioning** -- Multiple versions per prompt with full history
- **Board System** -- Organize prompts in thematic boards with tile view
- **Drag & Drop** -- Pin prompts to boards by dragging
- **Export** -- TXT and PDF export (individual or all)
- **Clipboard Integration** -- Quick copy with configurable modes (title, text, result, all)
- **Dark Mode** -- Modern Fusion Dark theme
- **Offline-First** -- All data stored locally (JSON)

## Screenshots

![Main Window](screenshots/main.png)

## Installation

### Requirements

- Python 3.10+
- PySide6

### Steps

```bash
git clone https://github.com/lukisch/ProfiPrompt.git
cd ProfiPrompt
pip install -r requirements.txt
```

## Usage

```bash
python src/profiprompt.py
```

On Windows, you can also double-click `START.bat`.

## Project Structure

```
ProfiPrompt/
├── src/
│   ├── profiprompt.py         # Main application
│   ├── dashboard.py            # Dashboard widget (prompt tree)
│   ├── board_manager.py        # Board management with tile view
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

## Tests

```bash
python -m pytest tests/ -v
```

## Building an Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/profiprompt.py
```

## License

[MIT](LICENSE)

## Author

Lukas Geiger ([@lukisch](https://github.com/lukisch))

---

Deutsche Version: [README.de.md](README.de.md)
