# ProfiPrompt Companion

Der Web/PWA-Companion ist die mobile und browserbasierte Leselinie für ProfiPrompt. Er bleibt bewusst read-only und arbeitet ausschließlich mit exportierten Dateien im Format `profiprompt-library-v1.json`.

## Umfang

- Dateiimport für `profiprompt-library-v1.json`
- lokale Speicherung der zuletzt geladenen Bibliothek im Browser
- Suche über Titel, Zweck, Tags, Prompttexte, Versionen und Boardnamen
- Board-Ansicht mit Filter auf die enthaltenen Prompts
- Detailansicht mit Versionsumschaltung und Clipboard-Kopie
- mobile Hinweise für Android/iOS zu Installation, Import, Offline-Start und Copy-Fallback
- PWA-Grundausstattung mit Manifest und Service Worker

## Lokal starten

Der Companion ist statisch. Für lokale Tests reicht ein kleiner HTTP-Server:

```bash
python -m http.server 4175
```

Danach im Browser `http://127.0.0.1:4175/web_companion/` öffnen, wenn der Server im Projektroot läuft.

Für eine sofortige Demo ohne Dateidialog kann zusätzlich `?library=./sample-library.json` genutzt werden.

Für lokale Browser-Tests liegt im Companion bewusst ein eigenes `package.json` mit `type: module`, damit dieselben `.js`-Module in Browser und Node-Smokes ohne MIME-Probleme funktionieren.

## Android-/iOS-Testplan

Die aktuelle P2-Testmatrix liegt in [PWA_TESTPLAN.md](PWA_TESTPLAN.md). Dort sind Install-, Import-, Offline-, Such- und Kopierpfade für Android Chrome und iOS Safari beschrieben.

## Grenzen

- kein Rückimport in die Desktop-App
- keine Cloud-Synchronisation
- keine Bearbeitung der Bibliothek im Browser

Das passt zur aktuellen Portierungsentscheidung: Desktop bleibt Master, Web/Mobil dient als leichter Companion.
