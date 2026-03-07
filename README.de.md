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

![Hauptfenster](screenshots/main.png)

## Installation

### Voraussetzungen

- Python 3.10+
- PySide6

### Schritte

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
│   ├── profiprompt.py         # Hauptanwendung
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
│   └── test_basic.py           # Unit-Tests (26 Tests)
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

## Lizenz

[MIT](LICENSE)

## Autor

Lukas Geiger ([@lukisch](https://github.com/lukisch))

---

English version: [README.md](README.md)
