# EXPORTFORMAT - profiprompt-library-v1.json

Stand: 2026-05-24

## Zweck

`profiprompt-library-v1.json` ist das stabile Austauschformat für ProfiPrompt-Bibliotheken. Es verbindet die Windows-Desktop-App mit späteren Web-/PWA-Companions, ohne Cloud-Zwang und ohne direkte Abhängigkeit von den internen Dateien `prompts.json` und `boards.json`.

Das Format ist UTF-8-JSON und enthält Prompts, Versionen, Boards, Board-Items, Tags, Zeitstempel und App-Metadaten.

## Stabilitätsregel

Alle v1-Felder bleiben in der v1-Linie erhalten. Felder werden nicht umbenannt oder entfernt. Neue Felder dürfen additiv ergänzt werden, solange bestehende Importe dadurch nicht brechen.

## Top-Level-Struktur

```json
{
  "schema_version": "profiprompt-library-v1",
  "app": {
    "name": "ProfiPrompt",
    "version": "1.0.1",
    "exported_at": "2026-05-24T12:00:00+00:00"
  },
  "stats": {
    "prompt_count": 1,
    "version_count": 1,
    "board_count": 1,
    "board_item_count": 1
  },
  "tags": ["antwort", "deutsch"],
  "prompts": [],
  "boards": []
}
```

## Prompt

Pflichtfelder:

- `id`: stabile Prompt-ID aus der Desktop-Bibliothek.
- `title`: sichtbarer Titel.
- `purpose`: Zweck oder Kurzbeschreibung.
- `text`: aktueller Prompt-Text.
- `tags`: Liste sichtbarer Tags.
- `last_result`: zuletzt gespeichertes Ergebnis.
- `created_at`: ISO-8601-Zeitstempel.
- `updated_at`: ISO-8601-Zeitstempel.
- `versions`: Liste der Prompt-Versionen.

## Version

Pflichtfelder:

- `id`: stabile Versions-ID.
- `prompt_id`: zugehörige Prompt-ID.
- `version_number`: numerische Version innerhalb des Prompts.
- `title`: Versionstitel.
- `text`: Versionstext.
- `result`: gespeichertes Ergebnis der Version.
- `tags`: Tags der Version.
- `created_at`: ISO-8601-Zeitstempel.
- `updated_at`: ISO-8601-Zeitstempel.

## Board

Pflichtfelder:

- `id`: stabile Board-ID.
- `title`: sichtbarer Board-Titel.
- `description`: Beschreibung, darf leer sein.
- `items`: Liste der Board-Items.
- `created_at`: ISO-8601-Zeitstempel.

## Board-Item

Pflichtfelder:

- `id`: stabile Item-ID.
- `board_id`: zugehörige Board-ID.
- `prompt_id`: referenzierte Prompt-ID.
- `version_id`: referenzierte Version-ID oder `null`, wenn das Item auf den Haupt-Prompt zeigt.
- `created_at`: ISO-8601-Zeitstempel.

## Beispiel

```json
{
  "schema_version": "profiprompt-library-v1",
  "app": {
    "name": "ProfiPrompt",
    "version": "1.0.1",
    "exported_at": "2026-05-24T12:00:00+00:00"
  },
  "stats": {
    "prompt_count": 1,
    "version_count": 1,
    "board_count": 1,
    "board_item_count": 1
  },
  "tags": ["deutsch", "review"],
  "prompts": [
    {
      "id": "p1",
      "title": "Review-Prompt",
      "purpose": "Code-Review vorbereiten",
      "text": "Prüfe den Patch auf Regressionen.",
      "tags": ["review"],
      "last_result": "",
      "created_at": "2026-05-24T10:00:00+00:00",
      "updated_at": "2026-05-24T10:15:00+00:00",
      "versions": [
        {
          "id": "v1",
          "prompt_id": "p1",
          "version_number": 1,
          "title": "Kurzfassung",
          "text": "Fasse die wichtigsten Risiken zusammen.",
          "result": "",
          "tags": ["deutsch"],
          "created_at": "2026-05-24T10:10:00+00:00",
          "updated_at": "2026-05-24T10:10:00+00:00"
        }
      ]
    }
  ],
  "boards": [
    {
      "id": "b1",
      "title": "Reviews",
      "description": "Prompts für schnelle Prüfungen",
      "items": [
        {
          "id": "bi1",
          "board_id": "b1",
          "prompt_id": "p1",
          "version_id": "v1",
          "created_at": "2026-05-24T10:20:00+00:00"
        }
      ],
      "created_at": "2026-05-24T10:20:00+00:00"
    }
  ]
}
```

## Implementierung

Der Desktop-Export wird über `library_export.write_library_export()` erzeugt und im Datei-Menü als `Bibliothek (JSON)` angeboten. Die JSON-Ausgabe nutzt `ensure_ascii=False`, damit deutsche Umlaute und nichtlateinische Zeichen lesbar erhalten bleiben.
