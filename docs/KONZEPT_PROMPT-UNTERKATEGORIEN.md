# Konzept: Prompt-Unterkategorien (Skill/Workflow/Rolle/Agent)

Stand: 2026-09-26 · Ticket T-20260926-456950433 · Nur Analyse + Konzept, keine Umsetzung.

## Auftrag

Nutzerauftrag wörtlich: "Promptboard hat neben PROMPT noch SKILL WORKFLOW ROLLE AGENT als
Kategorien, ich denke letztendlich kann man alles auch unter den Begriff prompts unterornen
also quasi ein skill prompt ein workflow-skill prompt ein rollenprompt ein agentprompt. Die
Frage ist wie wir es in ProfiPrompt noch einbauen können oder sollen [...] sodass User
verstehen, dass sie auch Skills speichern können und man diese auch evtl. unterschiedlich in
den Boards angezeigt bekommt, dabei sollen keine großen datenbankänderungen nötig seon, weil
es ist ja schon in benutzung."

## 1. Analyse

### 1.1 PromptBoard (`file-bricks/promptboard`)

Datenmodell (`src/models.py`) ist ein **flacher** `LibraryItem`:

```python
class ItemType(str, Enum):
    PROMPT = "PROMPT"
    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"
    ROLLE = "ROLLE"
    AGENT = "AGENT"

@dataclass
class LibraryItem:
    id: str
    item_type: ItemType
    name: str
    content: str
    category: str = ""   # freies Textfeld, UNABHÄNGIG von item_type
    tags: List[str] = field(default_factory=list)
    source: str = ""
    created_at: str
    updated_at: str
```

Wichtige Punkte:

- `item_type` ist die **Art** (Prompt/Skill/Workflow/Rolle/Agent), `category` ist ein
  **zusätzliches, freies** Ordnungsfeld (z. B. "Code-Review", "Marketing") — beide Achsen
  stehen nebeneinander, nicht ineinander verschachtelt.
- `ItemType.from_value()` ist **fehlertolerant**: unbekannte/fremde Werte fallen auf `PROMPT`
  zurück, keine Exception. `item_from_dict()` nutzt durchgängig `.get(..., default)` — exakt
  das Schema-Drift-robuste Muster, das auch ProfiPrompt selbst schon verwendet (siehe 1.2).
- **Keine Versionierung, kein Kanban-Board-Datenmodell.** "Board" ist bei PromptBoard nur die
  Bezeichnung der EINEN sichtbaren Arbeitsfläche (Liste/Tabelle, laut UI-Code
  `promptboard.py` mit Typ-Filter-Combobox `type_combo` und Typ-Dropdown beim Anlegen), keine
  eigene Kanban-Struktur wie bei ProfiPrompt.
- **Templates pro Typ** (`item_templates.py`): jeder `ItemType` hat ein eigenes
  Textgerüst (z. B. Skill: "Zweck:/Auslöser:/Eingaben:/Schritte:/Ergebnis:"), zweisprachig.
- **Materialisierung** (`materializer.py`) ist ein **einheitliches** eigenes Markdown-Format
  für alle Typen (`> Typ: …`, `> Kategorie: …`, `> Tags: …` als Zitatblock) — **nicht** das
  externe SKILL.md-YAML-Frontmatter-Format (Claude Agent Skills) oder das Claude-Code-
  Subagent-Frontmatter. Das ist bei PromptBoard selbst schon eine offene Lücke, keine
  ProfiPrompt-spezifische.
- **Es existiert bereits eine Brücke:** `src/profiprompt_adapter.py` liest ProfiPrompts
  `prompts.json`/`boards.json` **read-only** ein und bildet jeden Prompt auf
  `ItemType.PROMPT` ab (hartkodiert, `category` wird aus dem Board-Titel abgeleitet). Es gibt
  aktuell **keinen Weg**, aus ProfiPrompt einen Skill/Workflow/Rolle/Agent zu importieren —
  PromptBoard kennt kein Typ-Feld von der ProfiPrompt-Seite, weil ProfiPrompt keins hat.

### 1.2 ProfiPrompt (dieses Repo)

Datenmodell (`src/models.py`):

```python
@dataclass
class Prompt:
    id: str
    title: str
    purpose: str
    text: str
    tags: List[str] = field(default_factory=list)
    last_result: str = ""
    created_at, updated_at
    versions: List[Version]

@dataclass
class Version:
    id, prompt_id, version_number, title, text
    result: str = ""
    tags: List[str] = field(default_factory=list)
    created_at, updated_at

@dataclass
class Board:            # echtes Kanban-Board
    id, title, description
    items: List[BoardItem]

@dataclass
class BoardItem:
    id, board_id, prompt_id
    version_id: Optional[str]   # None = zeigt auf den Haupt-Prompt
```

Wichtige Punkte:

- **Es gibt aktuell KEIN `category`- oder `item_type`-Feld** — nur `tags: List[str]`. Die
  Ticket-Annahme "vorhandene Felder wie Kategorie/Typ" trifft also nicht zu; nur `tags`
  existiert schon.
- **Persistenz:** `storage.py` schreibt atomar (Temp-Datei + Replace), `Storage` kennt keine
  Schema-Versionsnummer in der lokalen `prompts.json`/`boards.json` — nur das separate
  Austauschformat `profiprompt-library-v1.json` (`EXPORTFORMAT.md`) trägt `schema_version`.
- **Migrationsmechanik ist bereits additiv-freundlich:** `prompt_from_dict()`/
  `version_from_dict()`/`board_from_dict()`/`boarditem_from_dict()` lesen **feldweise per
  `.get(key, default)`**, nicht per `Prompt(**d)` — das ist exakt gegen KeyError/TypeError bei
  fehlenden Feldern in alten JSONs gehärtet (dokumentiert als Bugsweep 19/28-Fixes in den
  Docstrings). Ein neues, additives Feld mit sinnvollem Default bricht bestehende
  `prompts.json`-Dateien **nicht** — das ist genau der Mechanismus, den auch PromptBoard für
  sein `item_type`/`category` nutzt.
- **`EXPORTFORMAT.md` hat bereits eine Stabilitätsregel**, die für dieses Vorhaben passt:
  "Alle v1-Felder bleiben erhalten. Felder werden nicht umbenannt oder entfernt. Neue Felder
  dürfen additiv ergänzt werden, solange bestehende Importe dadurch nicht brechen." — ein
  neues `item_type`-Feld ist also **innerhalb der bestehenden v1-Linie** zulässig, keine neue
  Schema-Version nötig.
- **UI/Board-Darstellung:** `dashboard.py` ist ein Tree mit Suchfeld, Tag-Combobox
  (`tag_combo`) und Datumsfilter — **kein** Kategorie-/Typ-Filter. `board_manager.py` zeigt
  Prompts als Kacheln in Kanban-Boards (Pin-Zähler, Tag-Badges, Versionsindikator), aber ohne
  Typ-Unterscheidung.
- Es gibt **keinen `docs/`-Ordner** und keine bestehende Konvention für Konzeptdokumente im
  Repo-Root — dieses Dokument legt `docs/` neu an.

## 2. Konzept

### 2.1 Kernidee

**Prompt bleibt der Oberbegriff**, exakt wie im Nutzerauftrag beschrieben. Ein Skill/
Workflow/Rollen-/Agent-Prompt ist strukturell weiterhin ein `Prompt` — er bekommt nur ein
zusätzliches, **additives** Feld, das seine Art markiert. Es entsteht **keine neue Tabelle**,
**keine neue Datei**, **kein Versionssprung** des lokalen Speichers.

### 2.2 Datenmodell-Änderung (minimal)

Neues Feld auf `Prompt` (NICHT auf `Version` — Begründung siehe „Offene Fragen"):

```python
@dataclass
class Prompt:
    ...
    item_type: str = "prompt"     # neu, additiv, Default = bisheriges Verhalten
```

- **String, kein hartes Enum** auf Storage-Ebene — bewusst analog zu ProfiPrompts
  bestehendem Stil (`tags: List[str]` ist auch kein Enum) und robuster gegen Schema-Drift als
  ein `Enum`-Feld, das bei einem unbekannten Fremdwert eine Exception werfen könnte. Auf
  UI-Ebene (Dropdown) wird trotzdem eine feste, kleine Werteliste angeboten, analog
  `ItemType.from_value()` bei PromptBoard: unbekannter/leerer Wert → Fallback `"prompt"`.
- **Vokabular exakt an PromptBoard ausrichten** (klein geschrieben, um sich optisch nicht wie
  ein neues hartes Enum zu geben, aber wertgleich): `prompt`, `skill`, `workflow`, `rolle`,
  `agent`. Das ist die Voraussetzung für reibungslosen Austausch mit PromptBoard (siehe 2.5).
- **Migration:** `prompt_from_dict()` bekommt eine Zeile
  `item_type=d.get("item_type") or "prompt"` — bestehende `prompts.json`-Dateien ohne das
  Feld laden unverändert weiter, jeder alte Prompt gilt automatisch als `"prompt"`. **Keine
  Datenumschreibung, kein Migrationsskript nötig.**
- **`EXPORTFORMAT.md`:** `item_type` wird als **optionales** Feld dokumentiert (Default
  `"prompt"` bei Fehlen), Version bleibt `profiprompt-library-v1` (additive Erweiterung
  laut bestehender Stabilitätsregel).

### 2.3 UI — Onboarding und Darstellung

1. **Anlegen-Dialog** (`prompt_dialog.py`): neues Dropdown "Art" (Prompt/Skill/Workflow/
   Rolle/Agent), Default "Prompt" — genau wie PromptBoards `type_combo`. Bei Auswahl eines
   Nicht-Prompt-Typs wird das Textfeld mit einem **Platzhalter-Gerüst** vorbefüllt (analog
   `item_templates.py`: Skill → "Zweck:/Auslöser:/Eingaben:/Schritte:/Ergebnis:", Workflow →
   "Ziel:/Auslöser:/Voraussetzungen:/Schritte:/Abschluss:", usw.) — das macht dem Nutzer
   beim ersten Klick sichtbar, dass hier mehr als ein Freitext-Prompt entsteht.
2. **Dashboard-Filter** (`dashboard.py`): zusätzliche Combobox "Art" neben der bestehenden
   `tag_combo` — gleiche Mechanik wie der Tag-Filter, nur über `item_type` statt `tags`.
3. **Baumdarstellung/Board-Kacheln:** ein kurzes Typ-Kürzel/Badge vor dem Titel (z. B.
   "[Skill] Titelname" oder ein kleines Präfix-Icon) in `dashboard.py`-Tree-Spalte und
   `board_manager.py`-Kachel — bewusst **kein** aufwendiges Farb-/Icon-System, weil auch
   PromptBoard selbst keins hat (nur eine Filter-Combobox); ein reiner Text-Badge ist
   proportional zum Vorbild und braucht kein neues Icon-Set.
4. **Erstkontakt-Hinweis:** ein einmaliger Tooltip/Infozeile beim ersten Öffnen des
   Anlegen-Dialogs ("Hinweis: Neben Prompts lassen sich hier auch Skills, Workflows,
   Rollen- und Agent-Prompts ablegen") — steuerbar über eine einzelne QSettings-Flag
   (`onboarding_item_type_shown`), analog zu bestehenden Settings in `settings_manager.py`.

### 2.4 Export je Art

- **JSON-Export** (`profiprompt-library-v1.json`): `item_type` wird pro Prompt mitgeschrieben
  (additiv, siehe 2.2).
- **Markdown/TXT/PDF-Export:** Metadatenzeile ergänzt um "Art: Skill" (analog zu
  PromptBoards `> Typ: …`-Zeile in `materializer.py`) — reine Kopfzeilen-Ergänzung, kein
  neues Exportformat.
- **Standards-Integrations-Klausel (P-009):** Eine **vollständige** Angleichung an
  etablierte externe Formate (Agent-Skills-`SKILL.md`-YAML-Frontmatter für Skill-Typen,
  Claude-Code-Subagent-Frontmatter für Agent-Typen) ist **nicht** Teil dieses minimalen
  Konzepts — sie würde ein eigenes, typspezifisches Exportformat pro Art bedeuten (deutlich
  größerer Eingriff als eine additive Spalte) und ist zudem eine Lücke, die **PromptBoard
  selbst** ebenfalls noch hat (dessen `materializer.py` nutzt auch nur das eigene
  Zitat-Metadatenformat, nicht SKILL.md). Empfehlung: als **eigenes, späteres Ticket**
  führen ("SKILL.md-kompatibler Export je Art"), das beide Repos gemeinsam beträfe, statt
  es hier unter Zeitdruck in die minimale Lösung zu pressen.

### 2.5 Kompatibilität/Austausch mit PromptBoard

- Sobald ProfiPrompt `item_type` schreibt, kann `promptboard/src/profiprompt_adapter.py`
  (aktuell hartkodiert `item_type=ItemType.PROMPT`) den Wert **durchreichen** statt ihn zu
  verwerfen — das ist eine **kleine, isolierte Änderung im PromptBoard-Repo** (eine Zeile in
  `_map_prompt()`), kein Bestandteil dieses ProfiPrompt-Konzepts, aber die Voraussetzung
  dafür ist mit der Werte-Angleichung in 2.2 bereits geschaffen.
- Gemeinsames Vokabular (`prompt/skill/workflow/rolle/agent`, kleingeschrieben in
  ProfiPrompt, `ItemType.from_value()` bei PromptBoard normalisiert ohnehin
  groß/klein-tolerant über `.upper()`) macht beide Werkzeuge zukünftig **ohne
  Mapping-Tabelle** austauschbar.

## 3. Empfehlung

**Additives `item_type: str = "prompt"`-Feld auf `Prompt`** (kein neues Enum-Storage, keine
neue Datei, keine Versionsspalte) plus drei kleine, unabhängig auslieferbare UI-Bausteine:
Anlegen-Dropdown mit Typ-Vorlagen, Dashboard-Filter-Combobox, Typ-Badge in Tree/Board-Kachel.
Das erfüllt die Nutzeranforderung ("keine großen Datenbankänderungen", "Boards zeigen es evtl.
unterschiedlich an", "User verstehen, dass sie auch Skills speichern können") vollständig,
ohne die bestehende Nutzerbasis zu gefährden — die Migrationsmechanik (`.get(..., default)`)
ist im Code bereits etabliert und genau für diesen Fall gebaut.

### Grober Umsetzungsplan

1. `models.py`: Feld `item_type: str = "prompt"` auf `Prompt`; `prompt_from_dict()` um
   `item_type=d.get("item_type") or "prompt"` ergänzen; `prompt_to_dict()` bleibt
   unverändert (nutzt `asdict()`, nimmt das neue Feld automatisch mit).
2. Regressionstest: bestehende `prompts.json`-Fixture **ohne** `item_type`-Schlüssel laden →
   erwartet `item_type == "prompt"` für jeden Prompt (Schema-Drift-Test analog den
   bestehenden Bugsweep-19/28-Regressionstests).
3. `item_templates.py`-Äquivalent in ProfiPrompt anlegen (oder Templates direkt in
   `prompt_dialog.py`), Werte 1:1 aus PromptBoards `item_templates.py` übernehmen
   (Begriffe stimmen bereits überein).
4. `prompt_dialog.py`: Typ-Dropdown + Vorbefüllung bei Neuanlage.
5. `dashboard.py`: Typ-Filter-Combobox neben `tag_combo`, Typ-Spalte/Badge im Tree.
6. `board_manager.py`: Typ-Badge auf der Kachel.
7. `EXPORTFORMAT.md`: `item_type` als optionales Feld dokumentieren (kein Versionssprung).
8. `pdf_exporter.py`/Markdown-/TXT-Export: Metadatenzeile "Art: …" ergänzen.
9. Onboarding-Hinweis (einmaliger Tooltip) über neue QSettings-Flag.
10. Test-Update: bestehende Fixture-Exporte (`tests/`) auf das neue optionale Feld prüfen,
    keine bestehenden Assertions brechen (additiv).

Kein Schritt erfordert das Umschreiben vorhandener `prompts.json`/`boards.json`-Dateien im
Feld; jeder Schritt ist für sich releasbar (Feature-Flag-frei, weil rein additiv).

## 4. Offene Nutzerfragen

1. **Schreibweise des Vokabulars:** klein (`skill`, `workflow`, `rolle`, `agent`, wie hier
   vorgeschlagen, passend zum bisherigen ProfiPrompt-JSON-Stil) oder groß wie PromptBoards
   `ItemType`-Werte (`SKILL`, `WORKFLOW`, …)? Beides ist mit `ItemType.from_value()"s
   Normalisierung PromptBoard-seitig kompatibel — reine Stilfrage für ProfiPrompt.
2. **Feld auf Prompt- oder auch auf Versions-Ebene?** Dieses Konzept setzt `item_type` nur
   auf den `Prompt` (nicht auf `Version`), weil eine Versionshistorie i. d. R. dieselbe Art
   bleibt (ein Skill bleibt über seine Versionen hinweg ein Skill). Falls gewünscht, dass
   sich die Art zwischen Versionen ändern kann, wäre das Feld stattdessen auf `Version` nötig
   — das ist eine Nutzerentscheidung, keine technische Notwendigkeit.
3. **SKILL.md-kompatibler Export** (Punkt 2.4): als eigenes, späteres Ticket verfolgen (beträfe
   auch PromptBoard) oder bewusst zurückstellen?
4. **PromptBoard-Adapter-Anpassung** (Punkt 2.5, `_map_prompt()` in
   `profiprompt_adapter.py`): im selben Zug beauftragen oder getrennt terminieren? (Ist ein
   PromptBoard-Repo-Change, nicht Teil dieses ProfiPrompt-Tickets.)
