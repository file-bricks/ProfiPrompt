# Beitragsrichtlinien / Contributing Guidelines

[English](#english) | [Deutsch](#deutsch)

---

<a id="english"></a>
## English

Thank you for your interest in contributing to **ProfiPrompt**!

### Architectural Principles & Governance Invariants

ProfiPrompt is an open-source, local-first PySide6 desktop workstation and offline Web/PWA companion for designing, versioning, organizing, and deploying generative AI prompts. All contributions must respect all 10 foundational governance and runtime invariants:

1. **Local-First & Zero Egress (`INV-LOCAL-01`)**: 100% offline-ready workstation. Zero outbound network sockets, zero telemetry, zero analytics, zero external API queries, and zero tracking. Operates completely air-gapped.
2. **Full Offline Autonomy (`INV-OFFLINE-02`)**: All prompt management, versioning, board editing, search, and export workflows execute locally without internet connectivity.
3. **Atomic File Persistence (`INV-ATOMIC-03`)**: All data writes (`prompts.json`, `boards.json`) utilize atomic tempfile + replace patterns, preventing corrupted state on sudden crash or power loss.
4. **Open Portable Schema (`INV-SCHEMA-04`)**: Standardized export via `profiprompt-library-v1.json` with documented schema (`EXPORTFORMAT.md`) ensures user data is never trapped in a proprietary silo.
5. **Non-Elevation & RunAsInvoker (`INV-UNPRIV-05`)**: Application executes exclusively within standard unprivileged user space (`RunAsInvoker`). Code must never require administrator, root, or UAC elevation.
6. **Fail-Safe Backup & Recovery (`INV-BACKUP-06`)**: Automatic `.bak` snapshot generation and recovery mechanisms protect prompt libraries against external filesystem errors.
7. **Local Clipboard Safety (`INV-COPY-07`)**: Clipboard copying features (Title, Prompt, Result, Full Document) operate directly through native OS memory with sanitization and zero external logging.
8. **Deterministic Multi-Format Rendering (`INV-PRINT-08`)**: High-fidelity document generation for TXT and PDF formats through Qt's vector print engine with robust parent directory creation.
9. **Read-Only Companion Isolation (`INV-PWA-09`)**: The Web/PWA companion (`web_companion/`) is strictly read-only, ensuring browser sessions cannot accidentally alter or corrupt the master desktop database.
10. **Open Source Governance & 48h SLA (`INV-SLA-10`)**: MIT License, canonical attribution (`NOTICE`), multilingual parity (DE, EN, ES, ZH, JA, RU), and binding 48h response / 5-day triage security SLA.

### Version Freeze & Release Governance

- **Version Freeze Policy (`T-20260920-167562623`)**: Version `1.0.2` is strictly frozen. Zero arbitrary version bumps. All improvements, CI hardening, and contract test expansions are documented under `## [Unreleased]` in `CHANGELOG.md`.

### Development & Quality Gates

- **Plan D Architecture**: Development, git operations, and tests occur strictly in the local git repository clone (`C:\_Local_DEV\repos\ProfiPrompt`). GitHub remote `https://github.com/file-bricks/ProfiPrompt.git` is origin.
- **Python Version Support**: Compatible with Python 3.10 through 3.13.
- **Pre-commit Quality Gates**:
  - Bytecode compilation: `python -m compileall -q .`
  - Linting: `ruff check .`
  - Automated test suite: `pytest` (100% green required)
  - Whitespace hygiene: `git diff --check`
  - Version freeze verification: `git diff -G"version = "` (0 version changes)
- **Security Vulnerabilities**: Please do not report security vulnerabilities publicly. Follow our [SECURITY.md](SECURITY.md) guidelines for responsible disclosure (48h response SLA) via `security@file-bricks.org`, `support@lukasgeiger.com`, `security@open-bricks.org`, or `lukas@open-bricks.org`.

### Statutory Notice (§ 521 BGB)

Provided free of charge under the MIT License as open-source software. Under German statutory law (§ 521 BGB Gefälligkeitsrecht), liability in the case of gratuitous provision is limited to intent and gross negligence.

---

<a id="deutsch"></a>
## Deutsch

Vielen Dank für Ihr Interesse an einer Mitarbeit an **ProfiPrompt**!

### Architektur-Prinzipien & Governance-Invarianten

ProfiPrompt ist eine quelloffene, lokale Desktop-Anwendung (PySide6 / Qt6) mit mobilem Web/PWA-Begleiter zur systematischen Erstellung, Versionierung, Organisation und Bereitstellung generativer KI-Prompts. Alle Beiträge müssen alle 10 grundlegenden Governance- und Laufzeit-Invarianten einhalten:

1. **100% Offline & Local-First Zero-Egress (`INV-LOCAL-01`)**: Vollständig offline-fähige Workstation. Keine ausgehenden Netzwerkverbindungen, keine Telemetrie, keine Nutzungsstatistiken, keine externen API-Aufrufe. Vollständiger Air-Gap-Betrieb.
2. **Volle Offline-Autonomie (`INV-OFFLINE-02`)**: Sämtliche Workflows für Prompt-Verwaltung, Versionierung, Board-Organisation, Volltextsuche und Dokumentenexporte laufen lokal ohne Internetverbindung.
3. **Atomare Dateipersistenz (`INV-ATOMIC-03`)**: Schreibvorgänge (`prompts.json`, `boards.json`) erfolgen atomar über temporäre Zwischendateien und atomaren Replace zum Schutz vor Datenkorruption bei Systemabsturz oder Stromausfall.
4. **Offenes, portables Datenformat (`INV-SCHEMA-04`)**: Standardisierter Export via `profiprompt-library-v1.json` mit offengelegtem Schema (`EXPORTFORMAT.md`); verhindert Vendor-Lock-in.
5. **Unprivilegierter Modus & Keine Elevation (`INV-UNPRIV-05`)**: Die Anwendung läuft ausschließlich im unprivilegierten Standard-Benutzerkontext (`RunAsInvoker`). Niemals Administrator-, Root- oder UAC-Rechte anfordern.
6. **Ausfallsichere Sicherung & Wiederherstellung (`INV-BACKUP-06`)**: Automatische `.bak`-Snapshot-Erstellung und Recovery-Routinen sichern Prompt-Bibliotheken gegen Dateisystemfehler ab.
7. **Lokale Zwischenablagen-Sicherheit (`INV-COPY-07`)**: Kopierfunktionen (Titel, Prompt, Ergebnis, Gesamtdokument) nutzen den nativen OS-Arbeitsspeicher mit Bereinigung und ohne Protokollierung.
8. **Deterministischer Mehrformat-Export (`INV-PRINT-08`)**: Hochwertige Dokumentenerzeugung für TXT und PDF über die Vektor-Druckengine von Qt mit robuster Verzeichniserstellung.
9. **Schreibgeschützte PWA-Isolation (`INV-PWA-09`)**: Der Web/PWA-Begleiter (`web_companion/`) ist strikt lesend ausgelegt, sodass Browsersitzungen die Desktop-Stammdatenbank nicht verändern können.
10. **Open-Source-Governance & 48h-SLA (`INV-SLA-10`)**: MIT-Lizenz, kanonische Attribution (`NOTICE`), mehrsprachige Parität (DE, EN, ES, ZH, JA, RU) und verbindliche 48h-Erstantwort / 5-Tage-Triage-SLA.

### Versions-Freeze & Release-Governance

- **Version-Freeze-Regel (`T-20260920-167562623`)**: Version `1.0.2` ist strikt eingefroren. Keine willkürlichen Versionserhöhungen. Alle Verbesserungen, CI-Härtungen und Vertragstests werden unter `## [Unreleased]` in `CHANGELOG.md` gepflegt.

### Richtlinien für Entwickler

- **Plan D Architektur**: Entwicklung und Tests erfolgen ausschließlich im lokalen Git-Repository (`C:\_Local_DEV\repos\ProfiPrompt`). GitHub `https://github.com/file-bricks/ProfiPrompt.git` ist origin.
- **Python-Unterstützung**: Python 3.10 bis 3.13.
- **Qualitäts-Tore vor Commits**:
  - Bytecode-Prüfung: `python -m compileall -q .`
  - Linter: `ruff check .`
  - Testsuite: `pytest` (100% grün erforderlich)
  - Whitespace-Prüfung: `git diff --check`
  - Version-Freeze-Prüfung: `git diff -G"version = "` (0 Versionsänderungen)
- **Sicherheitsmeldungen**: Sicherheitslücken bitte nicht öffentlich melden, sondern gemäß [SECURITY.md](SECURITY.md) vertraulich einreichen (48h Reaktions-SLA) an `security@file-bricks.org`, `support@lukasgeiger.com`, `security@open-bricks.org` oder `lukas@open-bricks.org`.

### Gesetzlicher Haftungsausschluss (§ 521 BGB)

Die Bereitstellung erfolgt unentgeltlich als Open-Source-Software unter den Bedingungen der MIT-Lizenz. Gemäß § 521 BGB (Gefälligkeitsrecht) ist die Haftung bei unentgeltlicher Überlassung auf Vorsatz und grobe Fahrlässigkeit beschränkt.
