# PORTIERUNGSPLAN - ProfiPrompt

Stand: 2026-05-24

## Kurzentscheidung

ProfiPrompt bleibt zuerst eine Windows-Desktop-App mit Windows-Store-Ziel. Die plattformübergreifende Linie soll nicht als nativer Mobile-Clone der PySide6-App entstehen, sondern als Web/PWA-Companion für Lesen, Suchen, Kopieren und Teilen von Prompt-Sammlungen. Gemeinsamer Vertrag zwischen Desktop und Web/Mobil wird ein versioniertes Exportformat `profiprompt-library-v1.json`.

Begründung: Der Kernnutzen von ProfiPrompt entsteht beim Arbeiten mit KI-Tools auf Desktop und Web. Nutzer brauchen schnelle Zwischenablage, Versionshistorie, Boards und portable Prompt-Bibliotheken. Mobil ist sinnvoll für Nachschlagen, Teilen und kleine Bearbeitungen, aber nicht als vollständiger Ersatz für die Desktop-Arbeitsumgebung.

## Bausubstanz

| Bereich | Ist-Stand |
|---|---|
| Desktop | PySide6-App, lokale JSON-Datenhaltung, `START.bat`, PyInstaller-Spec |
| Daten | `prompts.json` und `boards.json` mit Prompts, Versionen, Tags, Ergebnissen und Board-Items |
| Release | GitHub-Releases vorhanden, Store-Metadaten in `store_package.json`, Store-Listing vorhanden |
| Tests | Pytest-Suite für Modelle, Storage, Clipboard, TXT/PDF-Export |
| Lücke | Kein eigenständiger Portierungsplan, kein dokumentiertes Austauschformat für Web/Mobil |

## Plattformoptionen

| Option | Bewertung | Entscheidung |
|---|---|---|
| Windows Store release | Höchste Priorität, passt zu vorhandener PySide6-App und Store-Artefakten. | P0/P1 weiterführen |
| Android Version oder Clone | Nativ zu teuer für den Nutzen; Android braucht vor allem Lesemodus und Kopieren. | Über PWA abdecken |
| Webapp | Sehr sinnvoll für Prompt-Bibliothek, Suche, Teilen, Import/Export und Nutzung neben KI-Webtools. | P1 Companion planen |
| iOS Version | Nativ zunächst nicht sinnvoll; App-Store-Aufwand zu hoch. | Über PWA abdecken |
| Mac App | PySide6 kann grundsätzlich laufen; Verpackung ist nachrangig. | P3 Smoke-Test |
| Linux Version | PySide6 kann grundsätzlich laufen; Zielgruppe kleiner, aber für Entwickler nützlich. | P3 Smoke-Test |

## Zielbild

1. Windows-Desktop bleibt Master-App für Erfassung, Versionierung, Board-Pflege und PDF/TXT-Export.
2. `profiprompt-library-v1.json` exportiert Prompts, Versionen, Boards, Tags, Zeitstempel und App-Metadaten.
3. Web/PWA-Companion importiert das Exportformat, bietet Suche, Board-Ansicht, Prompt-Kopie und optional lokale Speicherung im Browser.
4. Android und iOS nutzen dieselbe PWA statt getrennte native Codebasen.
5. macOS und Linux werden als Smoke-Test-Ziele aus derselben PySide6-Codebasis geführt.
6. Desktop-zu-Web-Export bleibt ohne Cloud-Zwang; Synchronisation erfolgt nur über Dateiimport oder später bewusst gewählte Cloud-Option.

## Umsetzungsstatus

| Status | Punkt |
|---|---|
| vorhanden | Desktop-App, JSON-Datenmodell, Store-Listing, GitHub-Release-Struktur |
| erledigt P0 | Exportformat `profiprompt-library-v1.json` spezifiziert und getestet |
| teilweise erledigt P1 | Export-Aktion im Desktop angebunden; Import bleibt für den Companion-/Rückimport-Schritt offen |
| erledigt P1 | `web_companion/` importiert `profiprompt-library-v1.json`, bietet Suche, Board-Ansicht, Versionsumschaltung, Kopierpfade und lokalen Browser-Speicher |
| offen P2 | Android/iOS-PWA-Testmatrix mit Offline-Speicher und Clipboard-Rechten erstellen |
| offen P3 | macOS/Linux-PySide6-Smoke-Test dokumentieren |

## Exportformat `profiprompt-library-v1.json`

Mindestfelder:

- `schema_version`: `"profiprompt-library-v1"`
- `app`: Name, Version, Exportzeitpunkt
- `prompts`: `id`, `title`, `purpose`, `text`, `tags`, `last_result`, `created_at`, `updated_at`, `versions`
- `versions`: `id`, `prompt_id`, `version_number`, `title`, `text`, `result`, `tags`, `created_at`, `updated_at`
- `boards`: `id`, `title`, `description`, `items`, `created_at`
- `items`: `id`, `board_id`, `prompt_id`, optional `version_id`, `created_at`

Stabilitätsregel: Neue Felder dürfen additiv ergänzt werden. Bestehende Felder werden in v1 nicht umbenannt oder entfernt.

## Nächste Schritte

1. Android-/iOS-PWA-Testmatrix mit Offline-Speicher, Clipboard-Rechten und kleinen Viewports ergänzen.
2. Rückimport oder Merge-Strategie separat planen; der aktuelle Desktop-Export und der Web-Companion bleiben bewusst read-only.
3. macOS-/Linux-PySide6-Smoke-Test dokumentieren.
4. Optional später Board-spezifische Share-Links oder lokale Snapshot-Exporte prüfen, ohne Cloud-Zwang einzuführen.
5. Windows-Store-Readiness separat weiterführen: Screenshots, WACK/Testprotokoll, finale Listing-Prüfung.
