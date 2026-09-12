# Security Policy / Sicherheitsrichtlinie

## Deutsch

### Sicherheitsphilosophie & Leitlinien

file-bricks/ProfiPrompt ist als lokale Desktop-Anwendung (Local-First) zur Verwaltung, Strukturierung und Versionierung von KI-Prompts sowie für den Export von Prompt-Bibliotheken und Begleit-Web-Apps (PWA) konzipiert. Sicherheit, Vertraulichkeit von Textentwürfen und Schutz privater Daten basieren auf folgenden Kernprinzipien:

- **Local-First & Zero Egress:** ProfiPrompt überträgt keinerlei Telemetriedaten, Nutzungsstatistiken, Prompts oder Metadaten an externe Server oder Drittanbieter. Die gesamte Speicherung (JSON-Dateien) und Verarbeitung findet ausschließlich lokal auf dem System des Benutzers statt.
- **Unprivilegierter User-Mode (Non-Elevation):** ProfiPrompt benötigt und verlangt keine Administratorrechte. Alle Datei-, Export- und UI-Operationen laufen streng im unprivilegierten Benutzerkontext ab.
- **Sichere Dateinamen-Sanitisierung & Pfad-Isolation:** Beim Exportieren von Prompts (TXT, PDF, JSON) werden Dateinamen strikt bereinigt, um Directory-Traversal-Angriffe (../, verbotene Steuerzeichen, reservierte Windows-Gerätenamen wie CON, PRN, AUX) abzuwehren.
- **Sichere Clipboard-Operationen:** Zwischenablage-Operationen verarbeiten Daten direkt im Speicher und hinterlassen keine unverschlüsselten temporären Cache-Dateien auf dem Dateisystem.
- **Offline-fähige Begleiter-PWA:** Der Web-Companion arbeitet über Service Worker vollständig offline-fähig und benötigt für seine Funktion keine externen Netzzugriffe oder Analytics-Skripte.

### Unterstützte Versionen

| Version | Unterstützt | Anmerkungen |
| ------- | ----------- | ----------- |
| 1.0.x   | Ja          | Aktuelle Produktionsversion mit PySide6, PWA-Export und PDF-Unterstützung |
| < 1.0.0 | Nein        | Bitte auf Version 1.0.x oder neuer aktualisieren |

### Sicherheitslücken melden

Wenn Sie eine Sicherheitslücke oder ein Datenschutzrisiko in ProfiPrompt entdecken:

1. **Bevorzugter Meldeweg:** Nutzen Sie die private Vulnerability-Reporting-Funktion auf GitHub:
   - Öffnen Sie den Tab **Security** in diesem Repository
   - Wählen Sie **Report a vulnerability** ([Direktlink](https://github.com/file-bricks/ProfiPrompt/security/advisories/new))
   - Beschreiben Sie das Problem, Schritte zur Reproduktion und mögliche Auswirkungen
2. **Direkter E-Mail-Kontakt:** Alternativ können Sie sich an unsere Sicherheitskoordinatoren wenden:
   - security@file-bricks.org
   - security@open-bricks.org
   - support@lukasgeiger.com

### Reaktionszeiten & SLAs

- **Erste Eingangsbestätigung:** Verbindlich innerhalb von 48 Stunden nach Eingang der Meldung.
- **Erste Risikobewertung & Triage:** Innerhalb von 5 Werktagen.
- **Sicherheits-Patch:** Nach Priorität und Kritikalität im schnellstmöglichen Turnus.

Bitte öffnen Sie für Sicherheitslücken **keine öffentlichen Issues** und veröffentlichen Sie keine vertraulichen Daten vor Bereitstellung eines Patches.

---

## English

### Security Principles & Core Guarantees

file-bricks/ProfiPrompt is engineered as a local-first desktop application for managing, organizing, and versioning AI prompts, as well as exporting prompt libraries and progressive web app (PWA) companions. Privacy, confidentiality, and data safety are grounded in the following guarantees:

- **Local-First & Zero Egress:** ProfiPrompt does not transmit telemetry, analytics, prompt contents, or metadata to external servers or third-party providers. All storage (JSON files) and processing occur strictly on the user's local system.
- **Unprivileged User-Mode Operation (Non-Elevation):** ProfiPrompt operates entirely within standard user permissions and does not require administrative privileges or elevation.
- **Safe Attachment Sanitization & Path Traversal Guard:** During export operations (TXT, PDF, JSON), filenames are sanitized to prevent directory traversal (../, control characters, reserved Windows device names).
- **Safe Clipboard Operations:** Clipboard actions are processed directly in memory without writing unencrypted cache files to disk.
- **Offline Companion PWA:** The web companion functions entirely offline via service worker caching without external network dependencies or third-party trackers.

### Supported Versions

| Version | Supported | Notes |
| ------- | --------- | ----- |
| 1.0.x   | Yes       | Current production release with PySide6, PWA companion, and PDF export |
| < 1.0.0 | No        | Upgrade to version 1.0.x or later is recommended |

### Reporting a Vulnerability

If you discover a security vulnerability or sensitive data issue in ProfiPrompt:

1. **Preferred Method:** Report privately via GitHub's Security Advisories:
   - Navigate to the **Security** tab of this repository
   - Click **Report a vulnerability** ([Direct Link](https://github.com/file-bricks/ProfiPrompt/security/advisories/new))
   - Provide reproduction steps, affected versions, and expected impact
2. **Direct Security Email:** Alternatively, email our security coordinators directly:
   - security@file-bricks.org
   - security@open-bricks.org
   - support@lukasgeiger.com

### Response SLAs & Vulnerability Handling

- **Initial Acknowledgment:** Guaranteed within 48 hours of receipt.
- **Triage & Risk Assessment:** Within 5 business days.
- **Remediation & Patching:** Deployed with highest priority according to severity.

Please **do not disclose vulnerabilities in public issues**. Confirmed security patches are prioritized and released promptly.
