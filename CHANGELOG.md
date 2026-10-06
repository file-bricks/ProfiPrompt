# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Sprachwechsel für alle Bereiche, Kacheln auf andere Boards senden/duplizieren & Kachelfarben (2026-10-06)

- **Sprachwechsel live für die gesamte Oberfläche (`src/i18n.py`, alle Widgets):**
  - Bisher übersetzte ein Sprachwechsel nur die Menüleiste; Tabellenköpfe des Prompt-Baums (Titel/Zweck/Tags/Erstellt/Aktualisiert), Filterleiste, Versions-Unterzeilen (Kopier-Buttons), Board-Leiste, Kacheln, Kontextmenüs, Dialoge, Export-/Fehlermeldungen und die Tastenspalte der Shortcut-Tabelle blieben deutsch.
  - Neues Modul `i18n.py` mit einem gemeinsamen Translator (`tr()`); `MainWindow.change_language()` verteilt `bus.languageChanged`, worauf Dashboard, Prompt-Baum und BoardManager per `retranslate_ui()` live neu beschriften – kein Neustart mehr nötig. Die modale Hinweisbox wurde durch eine Statusleisten-Meldung ersetzt.
  - 174 neue Übersetzungs-Keys in allen 6 Sprachen (DE/EN/ES/ZH/JA/RU, 299 Keys, 100 % Parität).
  - **Bugfix:** Das Dashboard-Kontextmenü verglich Export-Aktionen per deutschem Menütext (`chosen.text().startswith(...)`); nach Übersetzung wären alle Exporte wirkungslos gewesen. Jetzt Vergleich per Aktionsobjekt.
  - `TranslationSystem(auto_register=...)`: Die laufende App schreibt fehlende Keys nicht mehr mit leeren Werten in die gebündelte `translations.json`.
- **Regression behoben – Kacheln auf andere Boards senden/duplizieren (`src/board_manager.py`, `src/storage.py`):**
  - Kachel-Kontextmenü: „Auf Board verschieben ▸“ und „Auf Board duplizieren ▸“ mit allen anderen Boards sowie „Neues Board …“.
  - `Storage.transfer_item()` / `move_item_to_board()` / `copy_item_to_board()` aktualisieren Quell- und Ziel-Board in einem atomaren Schreibvorgang (keine verlorenen/doppelten Kacheln); Duplikate auf dem Ziel-Board werden mit Hinweis abgewiesen.
  - Neuer Button „Umbenennen“ in der Board-Leiste (`Storage.rename_board()`); Prompt-Baum-Kontextmenü „Auf Board heften ▸“ als tastaturbedienbare Alternative zu Drag & Drop.
- **Feature – individuelle Kachelfarbe (`src/models.py`, `src/board_manager.py`):**
  - Kontextmenü „Kachelfarbe ▸“ mit Standardfarbe, 9 Vorgaben und „Eigene Farbe …“ (Farbdialog). Gespeichert pro Board-Kachel im neuen optionalen Feld `BoardItem.color` (`#RRGGBB`), wird beim Verschieben/Duplizieren mitgenommen.
  - Strikte Validierung (`normalize_item_color`): ungültige Werte aus fremden/alten JSONs werden verworfen (kein QSS-Injection, kein Crash); Dateien ohne `color` laden unverändert.
- **Board-Raster (`src/board_manager.py`):**
  - Spaltenzahl folgt jetzt der Dock-Breite (statt fest 3 Spalten mit horizontalem Scrollen); alte Kacheln werden beim Neuaufbau sofort ausgeblendet (behebt kurzzeitig überlappende Geister-Kacheln).
- **Tests (`tests/test_i18n_live_board_transfer_tile_colors_20261006.py`):** 32 neue Tests (Live-Sprachwechsel inkl. Tabellenköpfen, Key-Abdeckung aller `tr()`-Aufrufe mit Platzhalter-Parität, Transfer/Verschieben/Duplizieren, Kachelfarben, responsives Raster). Gesamtsuite: 325 passed, 3 skipped.

### Barrierefreiheit: Kachel-Tastatursteuerung, Version-AccessibleNames & Schema-Drift-Härtung (2026-10-04)

- **Kachel-Tastaturbedienung & Signale (`src/board_manager.py`):**
  - `PromptTile` um `removeRequested = QtCore.Signal(QtWidgets.QFrame)` erweitert; `BoardManager.reload_items` verbindet dieses Signal direkt mit `_remove_item_from_board`.
  - Tastenkürzel-Parität mit `ShortcutsDialog`: Fokus auf Kachel + `Ctrl+C` emittiert `bus.copyRequested` (Kopieren); `Entf` / `Backspace` emittiert `removeRequested` und öffnet den Bestätigungsdialog zum Entfernen der Kachel vom Board.
  - Modernisierung auf PySide6 / Qt 6 `QMouseEvent.position().toPoint()` in `mousePressEvent` und `mouseMoveEvent` (behebt DeprecationWarnings zu `QMouseEvent.pos()`).
- **Screenreader-Barrierefreiheit für Kacheln (`src/board_manager.py`):**
  - Dynamischer `accessibleName` für Version-Kacheln (`Prompt-Kachel: [Titel] (v[Nr] — [Versionstitel])`) unterscheidet Versionen klar vom Hauptprompt.
  - Semantische `accessibleName`-Attribute für untergeordnete Kachel-Labels (`Badge`, `Subtitle`, `Preview`).
- **Defensive Härtung & Schema-Drift-Resilienz (`src/profiprompt.py`, `src/dashboard.py`, `src/storage.py`):**
  - `MainWindow.handle_copy_request`: Defensive Handhabung von `None`-Prompts und `None`-Versionen verhindert `TypeError`/`AttributeError` bei korrupten Datensätzen.
  - `DashboardWidget._apply_filters`: Schutz vor `None`-Prompts bei der Aktualitäts-Sortierung; Vermeidung von Phantom-Büroklammer-Icons in Spalte 5, wenn nur ungültige `[None]`-Versionseinträge vorliegen.
  - `DashboardWidget.delete_current_item` & Kontextmenü: Löschen einer Version filtert `p.versions` defensiv mit `x is not None and getattr(x, 'id', None) != v.id`.
  - `DashboardWidget.get_current_version`: Längenprüfung (`len(data) >= 3`) schützt vor Entpack-Fehlern bei verkürzten UserRole-Tupeln.
  - `Storage`: `get_version`, `next_version_number`, `add_version`, `upsert_version` und `add_item_to_board` defensiv gegen `None`-Versionen und `None`-Items gehärtet.
- **Automatisierte Vertragstests (`tests/test_bugsweep_a11y_keyboard_and_drift_resilience_20261004.py`):**
  - 5 neue hermetische Unit- und Integrationstests decken Kachel-Shortcuts (`Ctrl+C`, `Entf`, `Backspace`), Accessible Names, Drift-Resilienz in Copy-Requests, Storage-Methoden und Dashboard-Tree-Rendering ab (Gesamtsuite 293 passed, 3 skipped, 0 warnings).

### Bugsweep: Board-Kachel Drag&Drop Klickunterdrückung, Drop-Validierung & Schema-Drift-Resilienz (2026-10-03)

- **Drag&Drop Klickunterdrückung & MIME-Format (`src/board_manager.py`):**
  - `PromptTile.mouseMoveEvent` setzt `self._suppress_click = True` vor Ausführung von `drag.exec(Qt.MoveAction)`. Verhindert, dass das Loslassen der Maustaste nach einem Drag-Vorgang irrtümlich als Klick gewertet wird (ungewolltes Kopieren in die Zwischenablage und Tooltip-Anzeige).
  - Drag-MIME-Payload um strukturierten Datentyp `application/x-prompt-item` erweitert.
  - `BoardManager.dropEvent` validiert Drop-Erfolg strikt: Nur bei erfolgreichem Einfügen wird `acceptProposedAction()` aufgerufen; ungültige oder bereits vorhandene Kacheln werden via `event.ignore()` abgewiesen.
- **Resilienz gegen Schema-Drift und Null-Werte (`src/models.py`, `src/storage.py`, `src/board_manager.py`):**
  - Deserialisierer `board_from_dict`, `boarditem_from_dict` und `prompt_from_dict` fangen explizite `null`/`None`-Werte in JSON-Dateien robust mit Fallbacks auf leere Listen und Standardwerte ab (`TypeError: 'NoneType' object is not iterable` behoben).
  - `Storage._validate_records` akzeptiert `None`-Platzhalter nicht nur für `"versions"`, sondern auch für `"items"`.
  - Mutationen und Lese-Iterationen in `Storage` (`delete_prompt`, `delete_version`, `add_item_to_board`, `remove_item_from_board`) und `BoardManager.reload_items` prüfen defensiv auf `None`-Elemente in Board-Listen.
- **Automatisierte Regressionstests (`tests/test_bugsweep_board_and_schema_drift_20261003.py`):**
  - 9 neue Unit- und Integrationstests decken Klickunterdrückung bei Drag, Drop-Event-Validierung, MIME-Typen, `null`-Resilienz in Models und Storage sowie defensive Iteration hermetisch ab.

### Pfad A / WCAG 2.1 AA / BITV 2.0 Dialog-Barrierefreiheit, Label-Buddies, Button-Accessibility & Statusleiste (2026-10-02)

- **Dialog-Barrierefreiheit & Modalität (`src/prompt_dialog.py`, `src/copy_settings_dialog.py`, `src/appearance_dialog.py`):**
  - Alle Dialoge (`PromptDialog`, `VersionDialog`, `CopySettingsDialog`, `AppearanceDialog`) explizit als modal (`setModal(True)`) konfiguriert; garantiert verlässliches Fokus-Trapping für Screenreader und Tastaturnutzer.
  - Vollständige semantische Barrierefreiheitsattribute (`accessibleName`, `accessibleDescription`) für alle Eingabefelder, Textbereiche, Checkboxen, Buttons und Listen.
  - Formular-Ergonomie nach WCAG 2.1 AA (Kriterium 1.3.1 Info und Beziehungen, 3.3.2 Beschriftungen/Anweisungen): Explizite `QLabel.setBuddy(...)`-Zuordnungen für alle Eingabeelemente („Titel*", „Zweck", „Tags", „Prompt-Text*", „Ergebnis", „Kopiermodus", „Theme", Farbwähler).
  - Standard-Aktionsbuttons: `isDefault()` (`setDefault(True)`) für alle Bestätigungs- und Speicheraktionen aktiviert, sodass Eingaben per Enter direkt ausgeführt werden.
  - Tooltips und Tastaturhinweise (`Enter`, `Esc`) auf allen Dialog-Schaltflächen integriert.
  - Farbwähler-Buttons in `AppearanceDialog` aktualisieren nun dynamisch Tooltip und `accessibleDescription` mit aktuellem Hex-Farbcode und Zielkacheltyp.
- **Inline-Aktionsbuttons im Prompt-Tree (`src/dashboard.py`):**
  - Kopier-Toolbuttons (`QToolButton`) in der Baumansicht mit barrierefreien Namen (`accessibleName`), Beschreibungen und Tooltips versehen („Prompt kopieren: [Titel]", „Version kopieren: v[Nr] — [Titel]"), um blinden und sehbehinderten Nutzern sofortiges Kontextfeedback zu geben.
- **Statusleiste & Dock-Accessibility (`src/profiprompt.py`):**
  - `MainWindow.statusBar()` explizit mit `accessibleName="Statusleiste"` und `accessibleDescription` initialisiert; sichert Screenreader-Readback von Aktions-Statustips und Feedback.
  - `boardDock` mit `accessibleName="Boards-Bereich"` und semantischer Beschreibung ausgestattet.
- **Automatisierte Vertragstests (`tests/test_ui_accessibility.py`):**
  - 6 neue hermetische Vertragstests implementiert (`test_prompt_dialog_accessibility_and_buddies`, `test_version_dialog_accessibility_and_buddies`, `test_copy_settings_dialog_accessibility_and_buddies`, `test_appearance_dialog_accessibility_and_buddies`, `test_dashboard_tree_item_copy_buttons_accessibility`, `test_mainwindow_statusbar_and_dock_accessibility`); Testsuite von 8 auf 14 Tests ausgebaut (Gesamtsuite 199 Tests, 100% bestanden).

### Bibliotheksdaten nach Ladefehlern erhalten (2026-10-02)

- Änderungen und direkte Speicher-APIs brechen bei unlesbaren oder beschädigten Bibliotheksdateien ab, statt vorhandene Daten als leere Bibliothek zu überschreiben.
- Prompt-/Versionslöschungen lesen Prompt- und Board-Datei vor dem ersten Schreiben. Änderungen desselben Storage-Objekts halten einen gemeinsamen Lock.
- JSON- und PDF-Gesamtexporte verwenden vollständig gelesene Bibliotheken; vorhandene Sicherungen bleiben bei Ladefehlern erhalten.
- Speicherdialoge bleiben bei Fehlern offen und verändern geteilte Modelle erst nach erfolgreichem Speichern. Entfernte Prompts führen nicht zu einer falschen Erfolgsmeldung für Versionen.
- Der fehlende Speicherpfad zum Entfernen einer Board-Kachel ist ergänzt; beide Bedienwege verwenden ihn.
- Grenzen und manuelle Wiederherstellung sind in `LIBRARY_SAFETY.md` beschrieben. Zwei JSON-Dateien bilden keine gemeinsame Transaktion; keine neue EXE oder Store-Abnahme.

### Atomare Exporte, Fsync-Durability, Storage-Schutz & PDF-Validierung (2026-10-01)

- **Atomare Datei-Operationen & Fsync-Durability (`src/atomic_io.py`):**
  - Neues Modul `atomic_io.py` mit `atomic_write_text`, `atomic_write_json`, `atomic_publish_file` und `is_protected_path`.
  - Atomare Schreibvorgänge via kollisionsfreie temporäre Dateien (`.{target}.tmp.{pid}_{uuid8}`), `flush()` und `os.fsync()`.
  - Windows-Rechtebehebung (`stat.S_IWRITE`) vor atomarem `os.replace` verhindert Windows `AccessDenied`.
  - Fail-safe `finally`-Bereinigung garantiert, dass niemals temporäre Zwischendateien bei Fehlern verbleiben.
- **Speichersicherheit & Schutz interner Datenbankdateien (`src/storage.py`, `src/library_export.py`):**
  - `Storage._atomic_write` und `_ensure_files` auf `atomic_write_json` umgestellt; verhindert Korruption bei Prozessabbruch.
  - Schutzprüfung (`is_protected_path`) in allen Exportpfaden: Überschreiben interner Bibliotheksdateien (`prompts.json`, `boards.json`) wird strikt mit `PermissionError` blockiert.
- **Fail-Safe PDF-Export & Header-Validierung (`src/pdf_exporter.py`):**
  - Isolierte Generierung in temporärer Zieldatei mit Validierung des binären PDF-Headers (`%PDF-`) und Mindestgröße.
  - Verhindert das Abschneiden bestehender Zieldateien bei fehlerhaftem Druck.
- **UI & Export-Integration (`src/dashboard.py`, `src/profiprompt.py`):**
  - Alle TXT- und PDF-Exportfunktionen in Hauptfenster und Dashboard auf atomare I/O-Routinen und Bibliotheksschutz umgestellt.
- **Automatisierte Testsuite (`tests/test_atomic_exports_and_storage_resilience.py`):**
  - 11 neue Regressionstests für atomare Schreibvorgänge, Fehlerabfang ohne Dateibeschädigung, Schutz interner Datenbankdateien, PDF-Validierung und Windows-Rechte-Handling (Testsuite wächst auf 193 Tests).

### Pfad A Technische Hygiene, CI Lifecycle Workflows & Lock-Defense (2026-09-28)

- **CI/CD Lifecycle Automation & Workflows (`.github/workflows/`):**
  - **Auto-Assign PRs (`.github/workflows/auto-assign.yml`):** Bereitstellung des standardisierten Auto-Assign-Workflows (`actions/github-script@v7`, `timeout-minutes: 5`, Concurrency `cancel-in-progress: true`, least-privilege `issues: write`, `pull-requests: write`) zur automatischen Zuweisung neu geöffneter PRs an den Repository-Owner.
  - **Label-Sync Automation (`.github/workflows/label-sync.yml`):** Bereitstellung des automatisierten Label-Sync-Workflows (`EndBug/label-sync@v2`, `timeout-minutes: 5`, least-privilege `issues: write`, Concurrency `cancel-in-progress: true`).
  - **Kanonische Labels-Konfiguration (`.github/labels.yml`):** Hinterlegung der 11 Standard-Governance-Labels nach `GOVERNANCE.md` §4.2 (`bug`, `enhancement`, `good first issue`, `help wanted`, `documentation`, `duplicate`, `wontfix`, `priority: high`, `priority: low`, `needs-triage`, `stale`).
  - **Python Testmatrix Modernisierung (`.github/workflows/tests.yml`):** Erweiterung der Python-Matrix um Python `3.13` (`python-version: ['3.10', '3.11', '3.12', '3.13']`).
- **Multi-Host Cloud-Sync-, Lock- und Cache-Schutz (`.gitignore`):**
  - Erweiterung der Multi-Host Ausschlussmuster um Host-Tokens (`*-MacBook*`, `*-IDEAPAD*`, `*_WORKSTATION*`, `*_WORKSTATION-LG*`, `*-WORKSTATION.*`, `*-WORKSTATION-LG.*`).
  - Härtung gegen kanonische Lock-Dateien (`LOCK.user.*`, `LOCK.until.*`, `LOCK.condition.*`, `.automation-lock`).
  - Absicherung gegen temporäre Test- und Tooling-Verzeichnisse (`.pytest_temp/`, `.pytest_tmp*/`, `.tox/`) sowie OS-Artefakte (`Desktop.ini`).
- **PEP 621 & Packaging Standardisierung (`pyproject.toml`):**
  - Ergänzung von `THIRD_PARTY_LICENSES.txt` in `license-files`: `["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md", "THIRD_PARTY_LICENSES.txt"]`.
  - Ergänzung von `"Plain-Text Licenses"` unter `[project.urls]`.
  - Härtung von `[tool.pytest.ini_options]` mit `addopts = "-ra -v --basetemp=.pytest_temp"` und standardisiertem `norecursedirs`-Array.
  - Strikte Version-Freeze-Disziplin per `T-20260920-167562623`: Version `1.0.2` strikt unverändert beibehalten.
- **Level 1 SBOM & Lizenz-Audit (`THIRD_PARTY_LICENSES.md`, `THIRD_PARTY_LICENSES.txt`):**
  - Re-Audit Stand 2026-09-28 durchgeführt; Bestätigung aller 10 Governance- und Laufzeit-Invarianten (`INV-LOCAL-01` bis `INV-SLA-10`), Unprivileged `RunAsInvoker` User Mode und Zero-Copyleft Isolation.
- **Dokumentation, Badges & Kontext-Parität:**
  - `llms.txt`: Last-checked auf Stand `2026-09-28` aktualisiert; Plain-Text Lizenz-URL verlinkt; Test-Metriken auf 174 Pytest-Tests + 46 Node.js Web Companion Tests (100% grün) synchronisiert.
  - `README.md`, `README_de.md`, `README_es.md`: Verified-Shields auf `verified-2026--09--28-blue.svg` synchronisiert; Plain-Text-Lizenz-Link auf `THIRD_PARTY_LICENSES.txt` ergänzt.
  - `MARKETING-LOG.txt`: Section 11 mit Pfad A Repository Hygiene, CI Lifecycle Hardening, Multi-Host Sync Defense & Contract Tests (2026-09-28) dokumentiert.
- **Automatisierte Vertragstestsuite (`tests/test_security_license_contract.py`):**
  - Neue und erweiterte Contract-Tests für CI-Lifecycle-Workflows (`auto-assign.yml`, `label-sync.yml`, `labels.yml`, `tests.yml`), erweiterte `.gitignore` Multi-Host/Lock-Guards, PEP 621 `license-files` & `norecursedirs`, SBOM Recency 2026-09-28 und `CHANGELOG.md` Pfad A Eintrag.

### WCAG 2.1 AA / BITV 2.0 Barrierefreiheit, Tastatur-Ergonomie & Menü-Mnemonics (2026-09-29)

- **Barrierefreier Tastaturkürzel- und Hilfedialog (`src/shortcuts_dialog.py`):**
  - Neuer modaler Dialog `ShortcutsDialog` nach WCAG 2.1 AA und BITV 2.0 mit strukturierter 3-Spalten-Tabelle (`Tastenkombination`, `Funktion / Aktion`, `Bereich`) für alle 24 Tastaturbefehle.
  - Offizieller Konformitätshinweis nach BITV 2.0 / WCAG 2.1 AA für Screenreader und sehbehinderte Nutzer.
  - Initialer Tastaturfokus auf der Schließen-Schaltfläche (`isDefault()`) und vollständige Tastaturbedienbarkeit via Escape, Return und Tab-Navigation.
  - Headless-sichere Testbarkeit via `get_shortcuts_list()`.
- **Tastatur-Ergonomie & Navigation in der Prompt-Übersicht (`src/dashboard.py`):**
  - Tastaturbedienung in `PromptTree`: `Eingabe`/`Return` und `F2` zum Öffnen und Bearbeiten ausgewählter Prompts/Versionen, `Entf`/`Backspace` zum Löschen mit Bestätigungsdialog, `Ctrl+C` zum Kopieren des Inhalts in die Zwischenablage mit Benachrichtigung, `F5` zum Neuladen der Daten.
  - Semantische Barrierefreiheits-Attribute: `accessibleName="Prompt-Übersicht"` und detaillierte `accessibleDescription`.
  - Formular-Buddies: `QLabel.setBuddy()` für alle Filter-Labels (`Suche:`, `Tag:`, `Von:`, `Bis:`) an die entsprechenden Eingabeelemente gebunden.
  - Semantische `accessibleName`- und `accessibleDescription`-Attribute für alle Filter-Widgets (`search_edit`, `tag_combo`, `date_from`, `date_to`, `btn_clear`).
- **Board- und Kachel-Barrierefreiheit (`src/board_manager.py`, `src/theme.py`):**
  - `PromptTile`: Tastaturfokusierung (`StrongFocus`), sichtbarer Tastatur-Fokusring (`#PromptTile:focus` mit 2px blauem Kontrastrand) im QSS-Theme, `Return` zum Bearbeiten/Öffnen, `Leertaste` zum Aktivieren, `Ctrl+C` zum Kopieren des Kacheltexts in die Zwischenablage, `Entf` zum Entfernen der Kachel vom Board.
  - Semantische Accessible Names und Descriptions für Kacheln (`Prompt-Kachel: {title}`, Badges, Untertitel und Vorschautext).
  - `BoardManager`: Label-Buddy für `Board:` an `board_combo`, Accessible Names und Descriptions für alle Header-Buttons (`Neues Board`, `Board löschen`, `Kachelschriftart wählen`), Scroll-Arbeitsfläche und Kachel-Raster; sichere Kachellöschung via `remove_tile_item()`.
- **Menüleiste mit Mnemonics & Globale Shortcuts (`src/profiprompt.py`):**
  - Tastatur-Zugriffstasten (Mnemonics) für alle Hauptmenüs: `&Datei` (`Alt+D`), `&Bearbeiten` (`Alt+B`), `&Ansicht` (`Alt+A`), `&Sprache / Language` (`Alt+S`), `&Hilfe` (`Alt+H`).
  - Standard-Shortcuts verankert: `F1` (Tastaturkürzel & Hilfe), `Ctrl+F` (Suche fokussieren), `Ctrl+N` (Neuen Prompt erstellen), `Ctrl+B` (Boards anzeigen/ausblenden), `Ctrl+1` (Prompt-Liste fokussieren), `Ctrl+2` (Board-Bereich fokussieren), `Ctrl+,` (Darstellungseinstellungen), `Ctrl+Shift+C` (Kopier-Einstellungen), `Ctrl+Q` (Beenden), `F5` (Aktualisieren).
  - StatusTips und erweiterte Tooltips für alle Menüaktionen.
- **Mehrsprachigkeit & Tier-2 6-Sprachen-Parität (`locales/translations.json`):**
  - 51 neue Lokalisierungsschlüssel für alle Barrierefreiheits-Elemente, Menü-Mnemonics, Tastaturkürzel und StatusTips mit 100% Parität über Deutsch (`de`), Englisch (`en`), Spanisch (`es`), Chinesisch (`zh`), Japanisch (`ja`) und Russisch (`ru`).
  - Echte deutsche Umlaute (ä, ö, ü, ß) standardisiert; `manage_translations.py --check` validiert 125/125 Keys (100% Parität).
- **Automatisierte Vertragstestsuite (`tests/test_ui_accessibility.py`):**
  - 8 neue automatisierte Vertragstests für ShortcutsDialog Struktur/BITV-Hinweis/Initialfokus, 6-Sprachen-Parität, Dashboard A11y & Buddies, PromptTree Tastaturbedienung, BoardManager & Kachel-A11y/Tastatur, Menüleisten-Mnemonics/Shortcuts, Navigation & Dialogauslösung, Theme-Fokusring.
  - Pytest Gesamtsuite wächst auf 182 Tests (100% bestanden in 3.36s).


### Dashboard Filterung, Volltextsuche, Versions-Hierarchie & Export-Resilienz — Bugsweep (2026-09-26)

- **Dashboard Tag-Filter & Volltextsuche (`src/dashboard.py`):**
  - **Tag-Filter Robustheit:** `DashboardWidget._apply_filters()` gegen `None`-Elemente in `p.versions` abgesichert (`AttributeError`-Guard); Normalisierung auf getrimmte Kleinbuchstaben für Quell- und Dropdown-Tags stellt sicher, dass auch ungetrimmte Tags (z.B. `' AI '`) oder numerische Tags (z.B. `2026`) zuverlässig gefiltert werden.
  - **Umfassende Volltextsuche:** Suchfeld `search_edit` durchsucht nun zusätzlich das Zweck-Feld `p.purpose` (Spalte 2 im Prompt-Baum) sowie sämtliche Versionen eines Prompts (`v.title`, `v.text`, `v.tags`), sodass Prompts auch über ihre Versionsinhalte und Zweckangaben im Prompt-Baum aufgefunden werden.
- **Hierarchische Prompt-Auflösung (`src/dashboard.py`):**
  - `DashboardWidget.get_current_prompt()` löst bei Auswahl eines Versions-Kindelements im Prompt-Baum nun den übergeordneten `Prompt` über `data[1]` auf, anstatt `None` zurückzugeben. Dadurch funktionieren Hauptmenü-Aktionen wie „Aktueller Prompt (TXT/PDF)“ auch dann, wenn der Nutzer im Baum eine Version markiert hat.
- **Dateinamen-Sanitisierung & I/O-Resilienz (`src/dashboard.py`, `src/profiprompt.py`):**
  - **`sanitize_export_filename()`:** Filtert Windows-Verbotszeichen (`:`, `/`, `\`, `<`, `>`, `*`, `?`, `"`, `|`, ASCII-Steuerzeichen) und trimmt Punkte/Leerzeichen aus vorgeschlagenen Export-Dateinamen in `dashboard.py` und `profiprompt.py` (Fallback auf `'prompt'` bzw. `'version'`).
  - **Defensive Verzeichnisanlage & Fehlerbehandlung:** `_export_prompt_txt()`, `_export_version_txt()`, `_export_bundle_txt()` und `MainWindow._write_txt_export()` legen übergeordnete Ordner via `Path(path).parent.mkdir(parents=True, exist_ok=True)` vor dem Schreiben automatisch an; I/O- und Zugriffsfehler werden abgefangen und per `QMessageBox.critical` benutzerfreundlich gemeldet, statt die Anwendung ungefangen abstürzen zu lassen; fehlende Prompts in `_export_version_txt()` werden defensiv abgefangen.
- **Automatisierte Regressionstests (`tests/test_bugsweep_dashboard_and_export_resilience_20260926.py`):**
  - 5 neue hermetische Regressionstests für Tag-Filterung mit `None`-Versionen, Zweck- und Versionssuche, Prompt-Auflösung bei Version-Selektion, Dateinamen-Sanitisierung und Verzeichnisanlage/Fehlerbehandlung.
  - Gesamtsuite wächst auf 174 Tests (171 passed, 3 skipped; 100% grün).

- **GitHub Topics & Discoverability Saturation:**
  - Expanded GitHub repository topics to full saturation (20/20 topics) via `gh repo edit`: added `developer-tools`, `fail-closed`, `file-bricks`, `open-bricks`, `zero-egress` alongside prompt engineering, local-first, PySide6, PWA, and desktop keywords.
  - Aligned `pyproject.toml` keywords array to 20 keywords matching repository topics and domain discoverability.
- **Canonical Root Attribution & Package Metadata:**
  - Created canonical root `NOTICE` attribution file documenting Lukas Geiger, `file-bricks`, `open-bricks`, MIT license, and Level 1 SBOM references.
  - Updated `pyproject.toml` with `license-files = ["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md"]` and `"Notice"` entry under `[project.urls]`.
- **Level 1 SBOM Invariant Cross-Reference Matrix & Non-Elevation (`THIRD_PARTY_LICENSES.md`):**
  - Added Section 7: Level 1 SBOM Invariant Cross-Reference Matrix mapping all 10 invariants (`INV-LOCAL-01` through `INV-SLA-10`) to architectural implementation files, automated test suites, and compliance status.
  - Added Section 8: Unprivileged Non-Elevation Certification (`RunAsInvoker`) guaranteeing execution entirely in unprivileged user space without administrative elevation.
  - Added Section 9: Zero-Copyleft Isolation Guarantee detailing dynamic linking of LGPL-3.0 libraries (`PySide6`, `shiboken6`) and decoupling of build-time tools.
- **Trilingual README Parity, Dual Anchors & Visual Architecture (`README.md`, `README_de.md`, `README_es.md`):**
  - Implemented reciprocal dual HTML anchors (`<a id="sec-01"></a><a id="overview"></a>...`) before each of the 17 `## ` sections across English, German, and Spanish documentation.
  - Added dual Mermaid architecture diagrams: autonumbered `sequenceDiagram` for prompt versioning & clipboard lifecycle alongside existing `flowchart TD` architecture diagram.
  - Added shields badges for `attribution: NOTICE` and `verified: 2026-09-22`, updated Pytest badge to `157 passed | 100%`, and added quick document reference navigation bar.
  - Strengthened Section 17 with statutory liability limitation (§ 521 BGB Gefälligkeitsrecht) and 48-Hour Security Response SLA.
- **Machine-Readable AI Context (`llms.txt`):**
  - Updated audit timestamp to `2026-09-22`.
  - Added canonical reference to `NOTICE`, updated test suite verification numbers to 160 Pytest + 46 Node.js = 206 passing tests (100% green), and documented Level 1 SBOM invariants and statutory disclaimer.
- **Automated Contract Tests & Quality Assurance (`tests/test_security_license_contract.py`):**
  - Added automated contract assertions for `NOTICE` file presence, author attribution, and Level 1 SBOM references.
  - Added assertions for Section 7 Level 1 SBOM matrix and Section 8 non-elevation certification in `THIRD_PARTY_LICENSES.md`.
  - Synchronized test counts across all documentation and validated 0 Mermaid lint issues across 15 files.

### Multi-Language Expansion & Spanische Dokumentation — Policy P-006 Tier-2 (2026-09-20)

- **Tier-2 6-Sprachen-Ausbau (`translator.py`, `locales/translations.json`, `manage_translations.py`):**
  - **TranslationSystem v2.0:** Auf 6 Sprachen ausgebaut (`de`, `en`, `es`, `zh`, `ja`, `ru`) mit deterministischer 4-Stufen-Fallback-Kette (`target_lang` -> `en` -> `de` -> `key`), sicherer atomarer Datei-Persistierung (`.tmp` + rename) und Keyword-Interpolation `t(key, **kwargs)`.
  - **100% Parität des Wörterbuchs:** `locales/translations.json` auf 74 Keys erweitert, die alle GUI-Elemente (Menüleiste, Datei-, Bearbeiten-, Ansicht-, Hilfe-Menüs, Darstellungsdialog, Kopier-Einstellungen, Prompt- und Versions-Dialoge, Dashboard-Filter, Bestätigungs- und Fehlermeldungen) über alle 6 Sprachen lückenlos und nicht-leer abdecken.
  - **Paritäts-Prüfer & CLI:** `manage_translations.py` mit `argparse`, `--check`-Modus (Exit-Code 1 bei Lücken, 0 bei 100% Parität) und robuster UTF-8-Ausgabe ausgerüstet.
  - **Settings & Smoke-Integration:** `SettingsManager` und `MockSettings` in `src/platform_smoke.py` auf `SUPPORTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")` erweitert mit persistenter `QSettings`-Speicherung.
  - **Dynamisches Menü:** Menüpunkt „Sprache / Language“ in `src/profiprompt.py` wird dynamisch für alle 6 Sprachen erzeugt; `change_language()` gibt lokalisierte Neustart-Hinweise in der gewählten Sprache aus.
- **Spanische Dokumentation (Policy P-006 Leerlauf-Sprachzug Stufe 2):**
  - `README_es.md` mit 100% reziproker 17-Punkte-Navigationsstruktur, Anker-Parität, Shields-Badges, 4 Personas, 10 Governance-Invarianten und 10-Dimensionen-Vergleichsmatrix angelegt.
  - Sprachwechsler-Kopfzeilen in `README.md`, `README_de.md` und `README_es.md` um `[Español](README_es.md)` synchronisiert.
- **Automatisierte Vertragstests & Qualitätssicherung:**
  - `tests/test_i18n_tier2_contract.py`: 5 neue Vertragstests für Wörterbuch-Integrität (74 Keys, 100% Parität), 4-Stufen-Fallback, Keyword-Interpolation, Klassen-Hilfsmethoden und Subprozess-Prüfung via `manage_translations.py --check`.
  - `tests/test_language_switch.py`: Umschalten und QSettings-Roundtrip über alle 6 Sprachen sowie Zurückweisung ungültiger Sprachen erweitert.
  - `tests/test_security_license_contract.py`: Navigations- und Anker-Vertragstest auf `README_es.md` erweitert; Datumsprüfung auf 2026-09-20 aktualisiert. Testsuite wächst auf 152 bestandene Pytest-Tests (100% grün).


- **VersionDialog Persistenz & Synchronisation (`src/prompt_dialog.py`, `src/storage.py`):**
  - **BUG-VD01 (KRIT):** In `VersionDialog._on_save_update()` wurden Version-Edits nicht in `storage` persistiert, da `VersionDialog` Instanzen aus getrennten `load_prompts()`-Aufrufen (`get_prompt()` vs `get_version()`) erhielt und In-Place-Änderungen am losgelösten Version-Objekt die Versionsliste des Prompts unberührt ließen. Behoben durch explizite Synchronisation der In-Memory-Versionsliste und Speicherung via `storage.upsert_version()`.
  - **BUG-VD02 (HOCH):** `Storage.upsert_version()` und `Storage.delete_version()` als atomare Methoden zur gezielten Versionsverwaltung hinzugefügt.
  - **BUG-VD03 (MITTEL):** Kaskadierende Bereinigung verwaister `BoardItem`-Referenzen: Bei `delete_prompt()` und `delete_version()` werden nun alle assoziierten BoardItems aus `boards.json` bereinigt, um tote Verweise zu verhindern.
  - **BUG-VD04 (MITTEL):** Drag & Drop Härtung in `src/board_manager.py` und `src/storage.py`: Text- und MIME-Payloads werden gestrippt; ungültige oder verwaiste Prompt-IDs werden vor Persistierung in Boards abgewiesen.
  - **Regressionstests (`tests/test_bugsweep_version_dialog_persistence_20260918.py`):** 6 neue automatisierte Tests decken Version-Edits, Versions-Upserts, Board-Bereinigung und Drop-Validierung ab.

### Repository Hygiene, CI Workflow Hardening & Multi-Host Protection — Pfad A (2026-09-16)

- **GitHub Actions Workflow Härtung (`.github/workflows/`):**
  - `tests.yml`: Top-Level `concurrency` mit `cancel-in-progress: true` hinzugefügt; Job-Timeouts etabliert (`python`: 15 min, `web-companion`: 10 min); Testlauf auf standardisierte Pytest-Flags `python -m pytest -ra -v` umgestellt.
  - `stale.yml`: Concurrency-Absicherung mit `cancel-in-progress: true` und Job-Timeout von 10 Minuten eingeführt.
  - `welcome.yml`: Concurrency-Absicherung mit `cancel-in-progress: true` und Job-Timeout von 5 Minuten eingeführt.
- **Multi-Host- & Cloud-Sync-Schutz (`.gitignore`):**
  - Lock-System-Ausschlüsse für kanonisches Multi-Agenten-Locking gehärtet (`LOCK`, `LOCK.permissions.json`, `uv.lock`, `!package-lock.json`).
  - Umfassende Multi-Host- und OneDrive-Konfliktmasken hinzugefügt (`* (copy)*`, `* (Kopie)*`, `*conflicted copy*`, `*-WORKSTATION*`, `*-ASUS*`, `*-LAPTOP*`, `*-Mac Studio*`, `*.sync-temp-*`, `*.orig`, `*.rej`).
  - Test- und Coverage-Caches geblockt (`.coverage.*`, `.hypothesis/`, `.turbo/`, `wheelhouse/`, `.wheel-smoke/`).
- **Paket- & Tooling-Konfiguration (`pyproject.toml`):**
  - PEP 621 Metadaten-URLs um `"Parent Organization"` (`file-bricks`), `"Umbrella Ecosystem"` (`open-bricks`) und `"LLM Ready"` (`llms.txt`) ergänzt.
  - Pytest-Konfiguration mit `minversion = "7.0"` und `addopts = "-ra -v"` verankert.
  - `[tool.ruff]` und `[tool.ruff.lint]` standardisiert; Codebase auf 100% ruff-Konformität gebracht.
- **Dokumentations- & LLM-Kontext-Synchronisation (`llms.txt`, `README.md`, `README_de.md`, `MARKETING-LOG.txt`):**
  - `llms.txt`: `Last-checked: 2026-09-16` aktualisiert, Testzähler auf 141 bestandene Pytest-Tests und 187 Gesamttests synchronisiert.
  - `README.md` & `README_de.md`: Pytest-Badge auf 141 Tests aktualisiert und Testübersichten synchronisiert.
  - `MARKETING-LOG.txt`: Abschnitt 8 für Pfad-A-Hygiene-Audit ergänzt.
- **Automatisierte Vertragstests (`tests/test_security_license_contract.py`):**
  - Neue Vertragstests `test_ci_workflow_guardrails`, `test_pep621_and_tool_configuration` und `test_marketing_log_hygiene_audit_recency` implementiert; `test_gitignore_security_and_multi_host_hardening` um Multi-Host- und Lock-Muster erweitert. Testsuite: 141 passed, 3 skipped (100% grün).

### Discoverability, Marketing & Visual Architecture — Pfad B (2026-09-13)

- **Bilinguale Navigationsarchitektur mit 100% reziproker Parität (`README.md`, `README_de.md`):**
  - Vollständige 17-Punkte-Schnellnavigation mit wechselseitiger Abschnitts- und Anker-Parität eingeführt.
  - Shields.io-Badges auf aktuellen Stand gebracht (Version 1.0.2, 138 Pytest-Tests grün, 46 Web-Companion-Tests grün, Gesamt: 184 bestandene automatisierte Tests).
  - Banner-Einbindung vereinheitlicht (`assets/banner.png` 1200x340) und Callout-Blöcke für maschinenlesbaren LLM-Kontext synchronisiert.
- **Zielgruppen-Personas & Discoverability:**
  - 4 strukturierte Stakeholder-Personas (`[PERSONA-1]` Prompt-Engineers & LLM-Praktiker, `[PERSONA-2]` Desktop Power-User & Solo-Entwickler, `[PERSONA-3]` Datenschutz- und Compliance-Beauftragte, `[PERSONA-4]` Multi-Device Wissensarbeiter & Prompt-Kuratoren) in Dokumentation und Marketing-Protokoll etabliert.
  - Bilinguale High-Intent-Suchbegriffe (DE/EN) für maximale Auffindbarkeit in Entwickler- und Enterprise-Suchanfragen.
- **10-Dimensionen-Vergleichsmatrix:**
  - Systematischer Vergleich gegenüber 4 Alternativen (ProfiPrompt, reine Notizen/Obsidian, Cloud-Prompt-SaaS, generische Snippet-Tools) entlang 10 Kernkriterien (Local-First, Versionsbäume, Ergebnis-Tracking, Kanban-Boards, Clipboard-Engine, Multi-Format-Exporte, PWA-Begleiter, atomare Speicherung, Lizenz/Kosten, offener Standard).
- **Drittanbieter-Lizenzinventar & Governance-Laufzeit-Invarianten (`THIRD_PARTY_LICENSES.md`):**
  - Umfassendes Lizenz-Audit mit SPDX-Kennungen für PySide6, shiboken6, PyInstaller, Packaging, Pytest, Pluggy, Iniconfig und Ruff.
  - 10 strikte Laufzeit- und Betriebs-Invarianten (`INV-LOCAL-01` bis `INV-SLA-10`) formal verankert.
  - Parität mit `THIRD_PARTY_LICENSES.txt` gewahrt.
- **Marketing- & Discoverability-Register (`MARKETING-LOG.txt`):**
  - Eigenständiges Marketing-Register für Pfad-B-Audits, Personas, Suchbegriffe und Wettbewerbsanalyse angelegt.
- **Projekt-Metadaten & LLM-Indexierung (`pyproject.toml`, `llms.txt`):**
  - `pyproject.toml` URLs um Marketing Log und Third-Party Licenses erweitert.
  - `llms.txt` Zeitstempel auf 2026-09-13 aktualisiert, Testzähler (184 Tests 100% grün) synchronisiert und direkte Verweise auf Marketing- und Lizenz-Dokumente ergänzt.
- **Automatisierte Vertragstests (`tests/test_security_license_contract.py`):**
  - Neue Vertragstests für 17-Punkte-Navigationsparität, Persona-Definitionen, Vergleichsmatrix, 10 Governance-Invarianten und Metadaten-Synchronisation hinzugefügt. Testsuite wächst auf 138 bestandene Pytest-Tests.

### Software Bugsweep — Export, Dialog & Tag-Aggregation Resilienz (2026-09-11)

- **PDF-Export & Druck-Initialisierung (`src/pdf_exporter.py`):**
  - `_init_printer(path)` stellt das übergeordnete Verzeichnis via `Path(path).parent.mkdir(parents=True, exist_ok=True)` sicher, um Speicherfehler bei neuen Zielpfaden zu verhindern.
  - `_render_html_for_prompt` und `_render_html_for_version` gegen `None`-Werte in `last_result` und `result` gehärtet (`AttributeError` auf `.strip()` eliminiert).
  - Robuste Tag-Formatierung via `_format_tags()` schützt vor `TypeError` bei `None` oder heterogenen Datentypen in Tag-Listen.
  - `export_single_prompt_with_versions` fängt `prompt.versions = None` sowie `version_number = None` sicher ab.
- **Dashboard & Filterung (`src/dashboard.py`):**
  - `_collect_tags()` gegen `None`-Versionen und heterogene Tags abgesichert; Tag-Sortierung erfolgt stabil via `casefold`.
  - Tag-Filterung (`self.tag_combo`) und Child-Item-Generierung handhaben `versions = None` und `version_number = None` defensiv ohne `TypeError`.
  - Bundle-Export (`_export_bundle_txt`) und Kontextmenü-Aktionen (`act_copy_full`, Löschabfrage) defensiv gegen `None`-Versionen gehärtet.
- **Dialog-Resilienz (`src/prompt_dialog.py`):**
  - `PromptDialog._populate()` und `VersionDialog.__init__()` gegen `None`-Attribute (`title`, `purpose`, `text`, `last_result`, `tags`) geschützt, da PySide6-Widget-Setter (`setText`, `setPlainText`) `None` mit `TypeError` abweisen.
- **Text-Export (`src/profiprompt.py`):**
  - `export_all_txt()` gegen `None`-Werte in Titeln, Zweck, Versionen und heterogene Tags gehärtet.
- **Testabdeckung (`tests/test_bugsweep_export_dialog_resilience_20260911.py`):**
  - 8 neue Regressions- und Resilienztests hinzugefügt (`test_ed01` bis `test_ed06`). Testsuite: 128 passed, 3 skipped (100% grün).

### Store-Preflight & Build-Hygiene Resilienz (2026-09-09)

- **Preflight-Resilienz (`scripts/check_store_readiness.py`):** `latest_release_version()` gegen fehlende oder noch nicht erstellte `releases/GitHub`-Verzeichnisse gehärtet. `validate_store_package()` fängt `FileNotFoundError` defensiv ab und liefert einen sauberen Preflight-Befund anstelle eines unbehandelten Python-Tracebacks. `main()` handhabt fehlende Release-Ordner beim Versionsdruck defensiv.
- **Gitignore & Store-Metadaten (`.gitignore`, `releases/windowsstore/`):** `.gitignore` nach Vorbild des Standards (`ProSync`) angepasst, sodass `releases/windowsstore/` Konfigurations- und Dokumentationsdateien (`BUILD.md`, `store_settings.json`, `WACK_PROTOCOL.md`, `store_listing_*.md`, `SUBMISSION-SHEET.md`, `test_reports/`) im Git-Tracking verbleiben, während binäre MSIX/EXE-Artefakte und GitHub-Release-Archive sicher ignoriert werden.
- **Testabdeckung (`tests/test_store_readiness.py`):** Neue Unit-Tests `test_validate_store_package_handles_missing_releases_dir` und `test_latest_release_version_nonexistent_dir` hinzugefügt. Testsuite: 111 passed, 3 skipped (100% grün).

### Store-Preflight: Suchbegriff-Policy gilt jetzt für alle Quellen (2026-08-14)

Nachprüfung des markenbezogenen Zertifizierungsfehlers (Ablehnung vom 2026-08-11,
Store-Policy 10.1.3 „Search Terms"). Ergebnis der Messung: Der beanstandete Verstoß
ist in **allen vier** Suchbegriff-Quellen behoben — je 7 Begriffe, kein fremder
Produkttitel. Korrigiert wurde die Ursache, die den Verstoß überhaupt durchließ.

- **Gemeinsame Prüfregel (`scripts/check_store_readiness.py`):** Marken- und
  Obergrenzenprüfung in `keyword_policy_findings()` herausgezogen. Bisher hing die
  Prüfung ausschließlich an `STORE_LISTING.md` — die Einreichung zieht ihre
  Suchbegriffe aber zusätzlich aus `releases/windowsstore/store_settings.json`
  (speist MSIX-Build und Submission-Sheet). Diese Datei lief bis jetzt komplett
  ohne Suchbegriff-Prüfung durch; genau dort blieb der Verstoß unsichtbar.
- **`validate_windowsstore_settings()`** prüft das `keywords`-Feld nun gegen
  dieselbe Policy (Obergrenze 7, keine fremden Produkttitel). Die Untergrenze von
  5 Begriffen bleibt dem redaktionell gepflegten Haupt-Listing vorbehalten
  (`require_minimum=False`).
- **Testabdeckung:** 4 neue Tests in `tests/test_store_readiness.py` — Markentreffer,
  Obergrenze, kein Fehlalarm auf „Prompt Template", Untergrenzen-Schalter sowie
  Positiv-/Negativfall für `store_settings.json`. Testsuite: 109 passed, 3 skipped.
- **Nicht geändert:** Beschreibungstexte. Die Nennung von KI-Werkzeugen ist dort
  beschreibend und war nicht Gegenstand der Ablehnung.

### Software Bugsweep — Iteration 2 (2026-08-03)
- **GUI & Board-State Resilienz (`src/models.py`):** `board_from_dict` und `boarditem_from_dict` wurden gehärtet. Fehlende oder korrupte Schlüssel (`title`, `id`, `board_id`, `prompt_id`) in `boards.json` lösen dank `.get()`-Defaults keinen `KeyError` mehr aus und verhindern den Absturz des Board-Managers beim Laden der Boards.
- **Dashboard Filter-Resilienz (`src/dashboard.py`):** Volltextsuche und Tag-Filterung in `DashboardWidget._apply_filters` gegen `None` oder Nicht-String-Elemente in `tags` und Versionstags gehärtet (`isinstance(t, str)`), um `AttributeError` bei korrupten/externe Datenstrukturen zu unterbinden.
- **Testabdeckung:** Unit-Tests in `tests/test_bug_regressions.py` (`TestBugsweep28GUIAndBoardState`) erweitert. Pytest Testsuite: 105 passed, 3 skipped (100% grün).

### Technische Hygiene & Maintenance Check (2026-08-02)

- **Version Alignment & Metadata:** `pyproject.toml` Version auf `1.0.2` synchronisiert (Parität mit Release 1.0.2 im Changelog).
- **LLM Indexing & Timestamps:** `llms.txt` Last-checked-Zeitstempel auf `2026-08-02` aktualisiert.
- **Verifikation & Testabdeckung:** Testsuite-Verifikation abgeschlossen — 103 Python-Pytest-Tests + 46 Node.js-Web-Companion-Tests = 149 Tests 100% grün (0 Fehler).

### Discoverability & Sichtbarkeit (2026-07-29)
- `llms.txt` Last-checked-Zeitstempel auf `2026-07-29` aktualisiert; SEO-Keywords, kanonische Repository-URLs (`file-bricks/ProfiPrompt`), Validierungsbefehle (`pytest`, Node-Companion-Smoke) und Scope-Grenzen im Rahmen der Discoverability-Hygiene auf Vollständigkeit und Parität verifiziert.

## [1.0.2] - 2026-07-26

### Discoverability, SEO & Doku-Wartung
- **PEP 621 Standardisierung:** Standardisierte `pyproject.toml` mit Projekt-Metadaten, Schlüsselwörtern, URLs und Pytest-Optionen (`pythonpath = "."`, `testpaths = ["tests"]`) angelegt.
- **Visual Badges & i18n:** Shields.io Badges (Python 3.10+, PySide6 Qt6, Pytest 103 passed, Web Companion 46 passed, Windows, Offline-first, LLM-Ready `llms.txt`) & Sprach-Umschalter (`[English](README.md) | [Deutsch](README_de.md)`) integriert.
- **GFM Callout & Systemarchitektur:** KI/LLM-Integrationshinweis (`> [!NOTE]`) für maschinenlesbaren Kontext und Mermaid-Systemarchitekturdiagramm in `README.md` und `README_de.md` eingebunden.
- **Deutsche Dokumentation:** Eigene deutsche `README_de.md` mit 100% i18n-Parität, Screenshot-Verweisen und rechtlichem Haftungsausschluss (§ 521 BGB) neu erstellt.
- **llms.txt Synchronisation:** Timestamp `Last-checked: 2026-07-26` und Testsuiten-Gesamtzahl (149 passed) in `llms.txt` verifiziert und synchronisiert.

### Neue Funktionen / Features
- **Welle-1 U1 — sichtbarer DE/EN-Sprachschalter** (`src/profiprompt.py`,
  `src/settings_manager.py`, `locales/translations.json`): Neues Menü „Sprache /
  Language" (Deutsch/English, exklusiv wählbar) in der Menüleiste. Die
  Menüleiste stellt sofort um (Live-Retranslate), tiefer liegende Texte folgen
  nach einem Neustart (Hinweis-Dialog). Die Auswahl wird in den bestehenden
  QSettings (`ui/language`) persistiert und beim Start geladen. Das bisher
  ungenutzte `translator.py` / `locales/translations.json` ist damit im UI
  verdrahtet (robuste locales-Auflösung für Source- und Frozen-Build; `.spec`
  nachgezogen). `translator.py` erhielt zusätzlich den isinstance-Guard gegen
  korrupte Einträge. Regressionstests: `tests/test_language_switch.py`.
- **Welle-1 U2 — Hell-/Dunkel-Theme umschaltbar** (`src/theme.py` (neu),
  `src/profiprompt.py`, `src/settings_manager.py`, `src/board_manager.py`): Neuer
  Menüpunkt „Bearbeiten → Darstellung …". Die Theme-Logik wurde aus
  `profiprompt.py` in ein eigenes Modul `theme.py` ausgelagert; neben dem
  bisherigen Dunkel-Theme gibt es jetzt eine sauber definierte Hell-Palette (kein
  bloßes Invertieren: eigene Fusion-Palette + Stylesheet). Die Board-Flächenfarbe
  folgt dem Theme (vorher hart `#252525`). Umschaltung erfolgt live (App-Palette
  wird zur Laufzeit neu gesetzt, Board-Kacheln + Tree-Icons neu gezeichnet). Die
  Auswahl wird in den QSettings (`ui/theme`) persistiert — analog zu `ui/language`.
  `apply_dark_theme` bleibt als Kompat-Wrapper (von `platform_smoke.py` /
  `generate_store_screenshots.py` genutzt). Regressionstests:
  `tests/test_appearance_u2_u3_u4.py`.
- **Welle-1 U3 — Kachelfarben konfigurierbar** (`src/theme.py`,
  `src/board_manager.py`, `src/settings_manager.py`, `src/appearance_dialog.py`
  (neu)): Getrennte Basis-Farbwahl für Haupt-Prompt- und Versionsprompt-Kacheln
  über einen `QColorDialog` im Darstellungs-Dialog. Aus der gewählten Farbe wird
  eine kohärente Kachel-Palette abgeleitet (Farbverlauf, Rand, Badge, lesbarer
  Text per Luminanz-Kontrast), damit jede Wunschfarbe stimmig wirkt. Persistenz
  in QSettings (`tiles/color_main`/`tiles/color_version`); Default = bisherige
  Farben (`#5D4037` / `#37474F`); „Zurücksetzen"-Knopf stellt die Standardfarben
  wieder her. Die zuvor hart kodierten Kachelfarben sind entfernt.
- **Welle-1 U4 — echte transparente UI-Icons** (`src/icons/*.png` (neu),
  `scripts/generate_ui_icons.py` (neu), `src/dashboard.py`): Die Clipboard- und
  Büroklammer-Icons in der Prompt-Liste waren eingebettete Rasterbilder ohne
  Alphakanal. Ersetzt durch schlanke, transparente Linien-Icons (128×128 PNG mit
  Alphakanal, aus SVG gerendert) in je einer hellen und dunklen Variante; die App
  wählt die theme-passende Variante, sodass die Icons auf hellem UND dunklem
  Hintergrund sichtbar sind (wichtig wegen U2). Die alten `clipboard.ico/.jpg`
  und `paperclip.ico/.jpg` wurden entfernt.

### Tests / Infrastruktur
- Neue `tests/conftest.py`: leitet die App-QSettings (IniFormat/UserScope)
  session-weit in ein Temp-Verzeichnis um (Tests schreiben nicht mehr in das echte
  `%APPDATA%\PromptManager`) und stellt eine gemeinsame `QApplication`-Fixture
  bereit. `tests/test_appearance_u2_u3_u4.py` deckt U2/U3/U4 ab (Persistenz,
  Theme-/Farbhelfer, Appearance-Dialog, Icon-Transparenz, Regressionsschutz gegen
  wieder eingeführte harte Farben). Suite: 103 passed / 3 skipped.

### Bugfixes (Bugsweep 2026-06-28 — Storage/Persistenz)
- **BUG-PS01 (KRIT):** `prompt_from_dict` in `models.py` krachte mit `KeyError: 'title'`
  bei alten oder fremden JSON-Exporten ohne `title`-Feld und riss den gesamten
  `load_prompts`-Aufruf mit. Fix: `title=d["title"]` → `title=d.get("title", "")`;
  konsistent mit der `version_from_dict`/`boarditem_from_dict`-Härtung aus Sweep 19.
  Regressionstests: `tests/test_bugsweep_storage_20260628.py`.
- **BUG-PS02 (MITTEL):** `load_prompts` und `load_boards` in `storage.py` fingen keinen
  `OSError` (inkl. `FileNotFoundError`, `PermissionError`) — eine zwischen `_ensure_files`
  und dem Lesezugriff gelöschte Datei (z.B. OneDrive-Lock, fehlgeschlagener `.tmp`-Rename)
  ließ die App hart crashen. Fix: `except`-Klausel um `OSError` erweitert.
  `UnicodeDecodeError` war bereits über `ValueError` abgedeckt (im Test verifiziert).
  74/74 Tests grün.

### Planung / Platform
- Portierungsplan am 2026-06-07 usecase-basiert aktualisiert: Windows Desktop bleibt Master-App und Store-Hauptkanal; Web/PWA bleibt read-only Companion für Web, Android und iOS; macOS/Linux bleiben Source-Smoke-Ziele; native Mobile-Voll-App, Cloud-Zwang und Server-Sync sind weiterhin Nicht-Ziele.

### Build / Release
- EXE neu gebaut 2026-06-01 (PyInstaller COLLECT, `ProfiPrompt.spec` → `C:\_Local_DEV\codex_build\profiprompt`); 34/34 Tests grün, Smoke-Test bestanden. Vorherige EXE: 2026-05-01. Anlass: pdf_exporter.py 2026-05-29. Hinweis: kein build_exe.bat vorhanden — direkter PyInstaller-Aufruf mit explizitem `--distpath`.
- Der Store-Preflight prüft `STORE_LISTING.md` jetzt strukturell auf beide Sprachblöcke, 100-Zeichen-Kurzbeschreibungen, nichtleere Schlüsselwort-/Kategorie-Felder und die Kategorie-Ausrichtung zu `store_package.json`; `AUFGABEN.txt`, `PORTIERUNGSPLAN.md` und README führen den Listing-Schritt damit als erledigt.
- GitHub-Repo-Hygiene aktualisiert: `LOCK*.txt` und `docs/superpowers/` bleiben ignoriert, `DesktopIcon.ico` und `DesktopIcon.png` sind als Quellassets dokumentiert, und Store-Readiness-Tests überspringen lokale Release-Artefaktprüfungen in sauberen CI-Checkouts.
- `scripts/check_store_readiness.py write-test-protocol` schreibt jetzt ein lokales Windows-Store-Testprotokoll mit repo-relativen Pfaden, MSIX-SHA256, Materialstatus und offenem WACK-Gate.

### Hinzugefügt / Added
- `EXPORTFORMAT.md` dokumentiert das stabile Austauschformat `profiprompt-library-v1.json`.
- Datei-Menü um `Bibliothek (JSON)` erweitert; der Export schreibt Prompts, Versionen, Boards, Board-Items, Tags, Zeitstempel und App-Metadaten als UTF-8-JSON.
- Neuer statischer Web/PWA-Companion unter `web_companion/` für Dateiimport, Suche, Boards, Versionsumschaltung, Kopierpfade und lokalen Browser-Speicher.
- Node-Smoke-Tests für den Companion prüfen Schema-Normalisierung, Filter, Board-Auflösung, Kopiertext und Restore aus `localStorage`.
- `web_companion/PWA_TESTPLAN.md` ergänzt die Android-/iOS-Testmatrix für Installation, Import, Offline-Start, Suche und Copy-Flows.
- Der Companion zeigt mobile Hinweise für Android/iOS direkt in der Oberfläche an.
- Neuer reproduzierbarer Desktop-Plattform-Smoke `src/platform_smoke.py` prüft Start, Storage, TXT/PDF-Export, `profiprompt-library-v1.json`, Clipboard und UTF-8-Umlaute in einem isolierten Ausgabeordner.
- Regressionstest `tests/test_platform_smoke.py` hält den Plattform-Smoke für macOS/Linux stabil.
- Neuer Generator `generate_store_screenshots.py` rendert vier feste
  Windows-Store-Screenshots aus redigierten Demo-Daten nach
  `README/screenshots/store/`; `tests/test_store_screenshots.py` sichert die
  PNG-Erzeugung und Grundstruktur ab.
- Neuer Store-Preflight `scripts/check_store_readiness.py` prüft
  `store_package.json`, `releases/windowsstore/store_settings.json`,
  `STORE_LISTING.md`, Screenshot-Summary, `releases/ProfiPrompt.msix` und
  vorhandene `wack_*.xml`-Reports reproduzierbar im Repo.
- `tests/test_store_readiness.py` deckt Store-Metadaten, Listing-Struktur,
  fehlenden WACK-Report, die XML-Auswertung und das neue lokale
  Store-Testprotokoll regressionssicher ab.
- `llms.txt` ergänzt kanonische Links, Interfaces, Datenschutzgrenzen und Validierungsbefehle für Crawler und LLM-Agenten.
- GitHub-Actions-Workflow `ProfiPrompt tests` prüft Python 3.10/3.11/3.12, Compile-Smoke und Web/PWA-Companion-Tests.
- Community-Workflows auf `actions/stale@v10` und `actions/first-interaction@v3` aktualisiert.

### Behoben / Fixed (web_companion)
- `service-worker.js`: fetch handler cachte 404s und opaque Responses ohne Statusprüfung — Guard `response.status !== 200 || response.type === "opaque"` ergänzt (Bug #1).
- `service-worker.js`: ASSETS-Liste enthielt nur `profiprompt-companion.svg`, aber die 4 PNG-Icons aus dem Manifest fehlten — Offline hatten Manifest-Icons keine Cache-Abdeckung; alle 4 PNGs in ASSETS ergänzt (Bug #2).
- `manifest.webmanifest`: `"id": "./"` ergänzt (PWA-Installierbarkeit gemäß Spec).
- `service-worker.js`: CACHE_NAME v1→v2; `skipWaiting()` in install-Handler; `clients.claim()` in activate-`waitUntil`-Kette.
- `service-worker.js`: Offline-Fetches nutzen `ignoreSearch: true`, damit gecachte Companion-Dateien auch bei Query-Parametern gefunden werden.
- `app.js`: Install-Prompt wird vor `prompt()` zurückgesetzt, damit schnelle Doppel-Klicks keinen zweiten Install-Dialog starten.
- `app.js`: gespeicherte Board-Auswahl fällt auf `all` zurück, wenn die importierte Bibliothek das alte Board nicht mehr enthält.
- `index.html`: `apple-touch-icon` ergänzt, damit iOS-Homescreen-Installationen ein passendes Icon erhalten.
- `app.js`: der `fallbackCopy()`-Textarea wird per `finally` entfernt, auch wenn `execCommand("copy")` eine Ausnahme wirft.
- `tests/pwa.test.mjs`: 22 neue Node-Tests; Gesamt 30/30 grün.

### Geplant / Planned
- Plattformstrategie in `PORTIERUNGSPLAN.md` fortgeschrieben: Windows Store bleibt Hauptkanal; Android/iOS folgen über PWA-Checks auf Basis des neuen Companions; der macOS/Linux-Smoke ist jetzt reproduzierbar dokumentiert.

### Behoben / Fixed
- Der Versions-PDF-Export respektiert jetzt die Metadaten-Einstellung auch dann, wenn er aus Dashboard oder Hauptfenster ausgelöst wird.
- Versionen werden im PDF-HTML weiterhin sauber escaped; die Regressionstests decken den Exportpfad jetzt explizit ab.
- Wenn mobile Browser die Zwischenablage sperren, fällt der Companion jetzt sichtbar auf ein manuelles Copy-Feld zurück statt still zu scheitern.
- `STORE_LISTING.md` und `releases/windowsstore/store_settings.json` wurden
  auf den aktuellen Export-/Companion-/Teststand sowie die korrekten
  GitHub-Privacy-/Support-Links gehoben.

## [1.0.1] - 2026-05-01

### Behoben / Fixed
- Board-Speicherung importiert `board_to_dict` explizit, damit `save_boards()` serialisieren kann.
- Einzelne Prompt- und Versions-TXT-Exports schreiben jetzt echten Plaintext statt den PDF-Exporter aufzurufen.

### Geändert / Changed
- README und Community-Dateien auf `file-bricks/ProfiPrompt` aktualisiert.
- README, Security-Policy, Privacy-Policy und Store-Listing auf Version 1.0.1 aktualisiert.
- App-About-Dialog und Store-Paketversion zeigen jetzt 1.0.1.
- Generierte Store-Staging-Artefakte werden nicht mehr als Repo-Quelldateien geführt.
- Regressionstests für einzelne TXT-Exports ergänzt; die Testsuite umfasst jetzt 28 Unit-Tests.

## [1.0.0] - 2026-02-28

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
- Prompt-Verwaltung (CRUD) mit Versionierung
- Board-System mit Kachel-Ansicht und Drag & Drop
- TXT- und PDF-Export (einzeln und alle)
- Clipboard-Integration mit konfigurierbaren Modi
- Modernes Dark Theme (Fusion)
- 26 Unit-Tests
