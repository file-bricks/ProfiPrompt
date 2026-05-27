# PWA-Testplan - ProfiPrompt Companion

Stand: 2026-05-27

## Ziel

Der Companion soll auf Android und iOS als kleine read-only PWA belastbar funktionieren: installieren, JSON importieren, offline erneut öffnen, suchen, Boards filtern und Prompttexte kopieren.

## Voraussetzungen

- Desktop-Export `profiprompt-library-v1.json` liegt lokal vor.
- Companion wird zuerst online über `http://127.0.0.1:4175/web_companion/` oder einen gleichwertigen Host geöffnet, damit Manifest und Service Worker geladen werden.
- Für Demo-Läufe kann zusätzlich `?library=./sample-library.json` genutzt werden.

## Testmatrix

| Bereich | Android (Chrome) | iOS (Safari) | Erwartung |
|---|---|---|---|
| Erststart | Seite online öffnen | Seite online öffnen | Startseite lädt ohne Console-Fehler, Status zeigt „Keine Bibliothek geladen“. |
| Import | `Bibliothek importieren` und `profiprompt-library-v1.json` wählen | `Bibliothek importieren` und JSON aus Dateien-App wählen | Prompt-, Versions-, Board- und Tag-Zähler werden gefüllt; Detailbereich zeigt den ersten Prompt. |
| Installation | PWA-Prompt oder `PWA installieren` nutzen | Teilen > `Zum Home-Bildschirm` | App startet als installierte PWA mit identischer Oberfläche. |
| Offline-Neustart | Flugmodus aktivieren, PWA neu öffnen | WLAN/Mobilfunk kurz deaktivieren, PWA neu öffnen | Bereits geladene Bibliothek bleibt sichtbar; Suche und Board-Filter funktionieren weiter. |
| Suche/Board | Suche nach Titel, Tags und Board; Board wechseln | Suche nach Titel, Tags und Board; Board wechseln | Trefferzahl und Auswahl aktualisieren sich ohne Layout-Bruch auf kleinem Display. |
| Kopieren | `Auswahl kopieren` drücken | `Auswahl kopieren` drücken | Android nutzt Clipboard direkt; iOS darf bei Sperre den manuellen Copy-Fallback mit markierbarem Text öffnen. |
| Bibliothek löschen | `Bibliothek löschen` ausführen | `Bibliothek löschen` ausführen | Lokaler Stand verschwindet; Offline-Neustart zeigt danach keine Bibliothek mehr. |

## Viewports

- Android-Referenz: 412 x 915
- iPhone-Referenz: 393 x 852

Bei beiden Größen müssen Hero, Mobile-Hinweise, Suchleiste, Listen und Detailkarten ohne horizontales Scrollen nutzbar bleiben.

## Abschlusskriterien

- Import, Suche, Board-Filter und Detailansicht laufen auf beiden Plattformen.
- Offline-Neustart funktioniert nach einem ersten Online-Laden.
- Kopieren ist entweder direkt möglich oder fällt sichtbar auf den manuellen Copy-Fallback zurück.
- Keine End-User-Texte enthalten `ae`, `oe`, `ue` als Umlaut-Ersatz.
