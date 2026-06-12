# Store-Screenshots - ProfiPrompt

Dieses Verzeichnis enthält den reproduzierbaren Screenshot-Satz für den
Windows-Store-Strang von ProfiPrompt.

## Enthaltene Ansichten

- `main-window.png` - Gesamtansicht mit Prompt-Liste und Board-Dock
- `search-and-versions.png` - Suchtreffer plus sichtbare Versionshistorie
- `boards-and-launch.png` - Board-Fokus für Briefing- und Release-Usecases
- `support-focus.png` - Support-/Kundenkommunikations-Prompt mit Detailfokus

## Erzeugung

Die PNGs stammen aus redigierten Demo-Daten und greifen nicht auf echte
Nutzerbibliotheken oder User-Settings zu.

```bash
python generate_store_screenshots.py
```

Der Generator schreibt die PNGs und eine `summary.json` direkt in dieses
Verzeichnis. Für Regressionen gibt es zusätzlich:

```bash
python -m pytest -q tests/test_store_screenshots.py
```
