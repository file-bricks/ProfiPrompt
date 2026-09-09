# Submission-Sheet — ProfiPrompt (Welle 1)

> Quelle-Dateien (alle per fc_read_file real gelesen): `STORE_LISTING.md`, `store_package.json`, `PRIVACY_POLICY.md`, `README.md`, `LICENSE`, `releases\windowsstore\store_listing_de.md`, `releases\windowsstore\store_listing_en.md`, `releases\windowsstore\store_settings.json`, `releases\windowsstore\BUILD.md`, `releases\windowsstore\WACK_PROTOCOL.md`, `releases\windowsstore\test_reports\store_readiness_20260625_000000.md`, `store_package\ProfiPrompt\AppxManifest.xml`, Verzeichnislisting `releases\windowsstore\screenshots\` und `README\screenshots\store\`, `START.bat`. Zusätzlich Web-Verifikation der Repo-URLs am 2026-07-23 (siehe Abschnitt 8).
> Erstellt 2026-07-23 · STORE-ID nach Reservierung HIER eintragen: `STORE-ID: ________`

## 1. App-Name (Reservierung)

```
ProfiPrompt
```

Begründung: `store_package.json`, `AppxManifest.xml` (tatsächlich gebautes Paket), `releases\windowsstore\store_settings.json`, README und beide Listing-Dateien stimmen durchgehend auf **„ProfiPrompt"** überein — keine Namens-Inkonsistenz gefunden (im Gegensatz zu den anderen beiden Apps dieser Welle).

## 2. Pricing & Availability

```
Preis: Kostenlos / Free
Märkte: alle
Sichtbarkeit: Public
```

Bestätigt durch `releases\windowsstore\BUILD.md` ("Preis: kostenlos").

## 3. Properties

```
Kategorie (aus store_package.json): Productivity
Unterkategorie: nicht in store_package.json angegeben
System requirements: Windows 10/11 Desktop x64
```

- `releases\windowsstore\store_settings.json` bestätigt dieselbe Kategorie „Productivity" — hier kein Widerspruch wie bei PDFtoPDFocr.
- STORE_LISTING.md (root) nennt zusätzlich „Productivity / AI Tools" als Kategorie-Vorschlag mit Unterkategorie-Idee „AI Tools" — das ist NICHT aus `store_package.json` und „AI Tools" ist keine sicher bestätigte offizielle Microsoft-Store-Unterkategorie; im Partner-Center-Dropdown zum Zeitpunkt der Einreichung die tatsächlich passende Unterkategorie wählen.
- `AppxManifest.xml` bestätigt `TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0"` — konsistent mit Windows 10/11 Desktop x64.

## 4. Age Ratings / IARC

Stichpunkte für den IARC-Fragebogen:

- ProfiPrompt ist ein reines **Produktivitäts-/Verwaltungstool** für Text-Prompts (Erstellen, Versionieren, Organisieren in Boards, Export) — keine Spiel-, Gewalt- oder Glücksspiel-Komponente.
- Kein nutzergenerierter Content mit Sharing-/Veröffentlichungsfunktion gegenüber Dritten; der Web/PWA-Companion ist laut README „read-only" und lokal.
- Keine Standortdaten, kein Tracking (PRIVACY_POLICY.md: „Keine Datenerhebung", „Kein Tracking", „Keine Drittanbieter-Dienste").
- Erwartete Einstufung: niedrigste verfügbare Alterseinstufung. Die Projektdateien deklarieren durchgehend `"age_rating": "3+"` (`store_package.json`, `releases\windowsstore\store_settings.json`, beide Listing-Dateien) — konsistent über alle Quellen.

## 5. Packages

```
Pfad (relativ zum Projektordner): releases\ProfiPrompt.msix
Version (aus store_package.json): 1.0.1.0
```

⚠ Wichtige Befunde vor Einreichung prüfen:
- **Versions-Widerspruch:** `store_package.json` und `releases\windowsstore\store_settings.json` stimmen übereinstimmend auf `1.0.1.0` überein — die Staging-`AppxManifest.xml` (`store_package\ProfiPrompt\`) nennt dagegen `1.0.0.0`. Vor Einreichung klären, ob das Staging-Manifest vor dem finalen Build noch aktualisiert wird.
- Die Datei `releases\ProfiPrompt.msix` ist real vorhanden (46,88 MB, erstellt 13.03.2026, geprüft per fc_file_info). Der SHA256-Hash aus `releases\windowsstore\test_reports\store_readiness_20260625_000000.md` (`69c13955e64ab5ae7f1224e96bc067abf20f4b326b49556a6f1fbd4a2d6cafeb`, 49155924 Bytes) passt zur Dateigröße — das Testprotokoll vom 25.06.2026 bezieht sich also auf denselben (alten) Build vom 13.03.2026, nicht auf einen neueren.
- `releases\windowsstore\store_settings.json` hat einen **leeren `pfx_path`/`pfx_password`** — das Paket ist damit **nicht signiert**. `WACK_PROTOCOL.md` bestätigt: „Für das aktuelle Paket liegt noch kein frischer wack_*.xml-Report vor" — kein WACK-Lauf dokumentiert.
- Das lokale Testprotokoll markiert selbst offen: „WARN – WACK-XML fehlt" als letztes Gate vor der Einreichung.

## 6. Store Listing DEUTSCH

Quelle: `releases\windowsstore\store_listing_de.md` (bereits Partner-Center-strukturiert, korrekte Umlaute geprüft).

**Kurzbeschreibung:**
```
AI-Prompt-Manager — Prompts verwalten, versionieren, organisieren
```

**Beschreibung:**
```
ProfiPrompt ist ein Desktop-Tool zur professionellen Verwaltung und Versionierung von AI-Prompts.

FEATURES:
- Prompt-Verwaltung: Erstellen, bearbeiten, kategorisieren
- Versionierung: Vollständige Historie jeder Prompt-Version
- Board-System: Thematische Organisation mit Kachel-Ansicht
- Drag & Drop: Prompts einfach auf Boards verschieben
- Export: TXT (einzeln oder alle), PDF
- Clipboard-Integration: Konfigurierbarer Kopiermodus (Titel, Text, Ergebnis, Alles)
- Dark Mode: Modernes Design
- Offline-First: Alle Daten lokal als JSON gespeichert

FÜR WEN:
Alle, die regelmäßig mit KI-Tools wie ChatGPT, Claude oder Copilot arbeiten und ihre Prompts professionell organisieren und wiederverwenden wollen.
```

Hinweis: Diese Fassung nennt nur TXT/PDF-Export. STORE_LISTING.md (root) erwähnt zusätzlich den portablen JSON-Bibliotheksexport (`profiprompt-library-v1.json`) und den Web/PWA-Companion — beides laut README/CHANGELOG real vorhandene Features, die hier aus Platzgründen nicht ergänzt wurden, aber bei Bedarf aus STORE_LISTING.md nachgetragen werden können.

**Feature-Bullets (einzeln, je ≤100 Zeichen, aus Beschreibung übernommen):**
```
Prompt-Verwaltung: Erstellen, bearbeiten, kategorisieren
Versionierung: Vollständige Historie jeder Prompt-Version
Board-System: Thematische Organisation mit Kachel-Ansicht
Drag & Drop: Prompts einfach auf Boards verschieben
Export: TXT (einzeln oder alle), PDF
Clipboard-Integration: konfigurierbarer Kopiermodus (Titel, Text, Ergebnis, Alles)
Offline-First: alle Daten lokal als JSON gespeichert
```

**Suchbegriffe (≤7, aus Quelle gekürzt von 9 auf 7):**
```
Prompt Manager, Prompt Engineering, AI Prompts, Prompt Library, Prompt Organizer, Prompt Template, LLM
```
(Quelle nannte zusätzlich „Versionierung" und „KI" — bei Bedarf tauschen.)

**Copyright-Zeile (aus LICENSE):**
```
© 2026 Lukas Geiger
```

**Screenshots-Ordnerpfad:**
```
releases\windowsstore\screenshots\
```
⚠ Dieser Ordner ist aktuell **leer** (per Verzeichnislisting geprüft). Fertige, Store-taugliche Screenshots liegen bereits unter `README\screenshots\store\` (`main-window.png`, `boards-and-launch.png`, `search-and-versions.png`, `support-focus.png`, dazu `README.md`+`summary.json`) — vor dem Upload dorthin kopieren oder direkt von dort hochladen.

## 7. Store Listing ENGLISH

Quelle: `releases\windowsstore\store_listing_en.md`.

**Short Description:**
```
AI prompt manager — manage, version, and organize your prompts
```

**Description:**
```
ProfiPrompt is a desktop tool for professional management and versioning of AI prompts.

FEATURES:
- Prompt Management: Create, edit, categorize
- Versioning: Complete history of every prompt version
- Board System: Thematic organization with tile view
- Drag & Drop: Easily move prompts to boards
- Export: TXT (single or all), PDF
- Clipboard Integration: Configurable copy mode (title, text, result, all)
- Dark Mode: Modern design
- Offline-First: All data stored locally as JSON

FOR WHOM:
Anyone who regularly works with AI tools like ChatGPT, Claude or Copilot and wants to professionally organize and reuse their prompts.
```

**Feature bullets (≤100 chars each):**
```
Prompt Management: create, edit, categorize
Versioning: complete history of every prompt version
Board System: thematic organization with tile view
Drag & Drop: easily move prompts to boards
Export: TXT (single or all), PDF
Clipboard Integration: configurable copy mode (title, text, result, all)
Offline-First: all data stored locally as JSON
```

**Keywords (≤7, matches source exactly — source already had 8, trimmed by 1):**
```
Prompt Manager, Prompt Engineering, AI Prompts, Prompt Library, Prompt Organizer, Prompt Template, LLM
```

**Copyright line:**
```
© 2026 Lukas Geiger
```

**Screenshots folder path:** identisch zu Abschnitt 6 (`releases\windowsstore\screenshots\`, aktuell leer, echte Bilder unter `README\screenshots\store\`).

## 8. Support-Infos

```
Privacy Policy URL: https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md
Support URL: https://github.com/file-bricks/ProfiPrompt/issues
Website: nicht separat angegeben (kein dediziertes Website-Feld in den Quelldateien gefunden)
```

Web-Verifikation (2026-07-23, per WebFetch geprüft):
- `github.com/file-bricks/ProfiPrompt` ist ein **echtes, öffentliches** Repository (50 Commits, Release v1.0.0 vom 28.02.2026, MIT-Lizenz). Die konkrete URL `.../blob/master/PRIVACY_POLICY.md` lädt tatsächlich mit vollem Inhalt.
- `store_package.json` UND `releases\windowsstore\store_settings.json` stimmen übereinstimmend auf `file-bricks/ProfiPrompt` überein — **kein Widerspruch zwischen den beiden kanonischen Config-Dateien** (anders als bei RPX Pro/PDFtoPDFocr).
- Leichte Abweichung: `releases\windowsstore\store_listing_de.md`/`en.md` (ältere Listing-Fassungen) verlinken stattdessen auf `github.com/lukisch/ProfiPrompt` — ebenfalls real und öffentlich (per WebFetch verifiziert, gleicher Projektinhalt, Autor Lukas Geiger), aber ein anderes Konto. Da beide JSON-Konfigs konsistent `file-bricks` nutzen, wird diese Org hier als kanonisch vorgeschlagen.
- Kein Website-Feld gefunden; als Ersatz kann das GitHub-Repo selbst dienen.

## 9. Notes for Certification

```
Start: ProfiPrompt.exe (installiertes Paket) bzw. START.bat / "python src\profiprompt.py" (Quellcode-Variante)
Login: nicht erforderlich
Offline: ja, offline-first
```

- Kein Account, kein Login (bestätigt durch `START.bat` — prüft nur, ob Python installiert ist, fragt keine Zugangsdaten ab; `PRIVACY_POLICY.md` — „Keine Internetverbindung erforderlich").
- Kurzanleitung für Tester: Prompt anlegen (Titel + Prompt-Text) → optional Board zuweisen (Drag & Drop) → Export testen (TXT/PDF) → Clipboard-Kopie testen.
- ⚠ Zu prüfender Punkt: `store_package.json` UND `releases\windowsstore\store_settings.json` deklarieren beide die Capability `internetClient`, obwohl `PRIVACY_POLICY.md` explizit sagt: „Keine Internetverbindung erforderlich: Alle Funktionen arbeiten vollständig offline" und „Keine Drittanbieter-Dienste". Dieser Widerspruch zwischen deklarierter Capability und dokumentiertem Verhalten sollte vor der Zertifizierung geklärt werden (evtl. ungenutztes Boilerplate aus einer Vorlage) — eine unbegründete Netzwerk-Capability kann bei der WACK-Prüfung oder im Store-Review Nachfragen auslösen.
