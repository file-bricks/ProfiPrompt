# Third-Party Licenses & Software Inventory / Drittanbieter-Lizenzen

This document lists all third-party software components, libraries, and build tools used in **ProfiPrompt** (`file-bricks/ProfiPrompt`) along with their license and SPDX identifiers, usage notices, and governance runtime invariants.

**Project:** `ProfiPrompt` (`file-bricks/ProfiPrompt`)<br>
**License:** [MIT License](LICENSE)<br>
**Audit Date:** 2026-09-22<br>
**Status:** AUDITED & VERIFIED (Level 1 SBOM Transparency, Discoverability & Licensing Governance)<br>
**Attribution Notice:** [NOTICE](NOTICE)<br>
**Security SLA:** [SECURITY.md](SECURITY.md) (48h Initial Response, 5-Day Triage)

---

## 1. Runtime Dependencies & Desktop Architecture

ProfiPrompt is built on top of Qt6 via the official Python bindings. The core desktop application runs 100% locally and executes no telemetry or background network calls.

| Package | Version Spec | License | SPDX Identifier | Source / Upstream | Purpose & Boundary Notice |
|:---|:---|:---|:---|:---|:---|
| **PySide6** | `>=6.5.0` | LGPL-3.0-only | `LGPL-3.0-only` | [PySide6 on PyPI](https://pypi.org/project/PySide6/) | Official Python Qt6 bindings for desktop UI, dialogs, clipboard, font rendering, and PDF printing engine. |
| **shiboken6** | `>=6.5.0` | LGPL-3.0-only | `LGPL-3.0-only` | [shiboken6 on PyPI](https://pypi.org/project/shiboken6/) | C++ binding generator and runtime support library required by PySide6. |

*LGPL Compliance Note:* PySide6 and shiboken6 are dynamically loaded shared libraries. ProfiPrompt does not modify Qt or PySide6 internals. In standalone binary distributions, dynamic linkage or PyInstaller bundle relinking provisions comply with LGPLv3 §4.

---

## 2. Web / PWA Companion Architecture

The companion application in `web_companion/` provides a mobile-ready, offline-first, read-only browser interface for exported libraries (`profiprompt-library-v1.json`).

| Component | License | SPDX Identifier | Source | Purpose & Boundary Notice |
|:---|:---|:---|:---|:---|
| **Vanilla Web Engine** | MIT / Project License | `MIT` | `web_companion/` | 100% vanilla JavaScript (ES6+), semantic HTML5, and CSS3. Zero external runtime npm dependencies, zero remote CDN scripts, zero trackers. |
| **Service Worker v4** | MIT / Project License | `MIT` | `web_companion/service-worker.js` | Offline caching shell with offline search and local storage resilience. Operates completely client-side. |

---

## 3. Standalone Packaging & Build Dependencies

The following tools are utilized during automated build and packaging pipelines to compile standalone Windows executables:

| Package | License | SPDX Identifier | Source / Upstream | Scope & Purpose |
|:---|:---|:---|:---|:---|
| **PyInstaller** | GPL-2.0-or-later WITH Bootloader-exception | `GPL-2.0-or-later WITH Bootloader-exception` | [PyInstaller](https://www.pyinstaller.org/) | Standalone executable packaging for Windows desktop releases (`ProfiPrompt.spec`). Uses standard bootloader exception. |
| **pyinstaller-hooks-contrib** | Apache-2.0 | `Apache-2.0` | [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | Community packaging hooks for PySide6 and standard library isolation. |
| **altgraph** | MIT | `MIT` | [altgraph on PyPI](https://pypi.org/project/altgraph/) | Static dependency graph analysis used internally by PyInstaller. |
| **packaging** | Apache-2.0 OR BSD-2-Clause | `Apache-2.0 OR BSD-2-Clause` | [packaging on PyPI](https://pypi.org/project/packaging/) | PEP 440 and PEP 508 version specification parsing and compatibility checks. |

*Notice:* Packaging tools are build-time only and are not bundled into user environments or distributed as runtime dependencies.

---

## 4. Development, Quality Assurance & Linting Tools

The following open-source tools are used strictly for local development, automated testing, and continuous integration:

| Package | Version Spec | License | SPDX Identifier | Source / Upstream | Scope & Purpose |
|:---|:---|:---|:---|:---|:---|
| **pytest** | `>=9.1.1` | MIT | `MIT` | [pytest](https://pytest.org/) | Automated test execution framework (hardened against CVE-2025-7117 / GHSA-6w46-j5rx-g56g). |
| **pluggy** | `>=1.5.0` | MIT | `MIT` | [pluggy on PyPI](https://pypi.org/project/pluggy/) | Plugin management and hook execution mechanism for pytest. |
| **iniconfig** | `>=2.0.0` | MIT | `MIT` | [iniconfig on PyPI](https://pypi.org/project/iniconfig/) | Lightweight INI and pyproject.toml parser for pytest test discovery. |
| **ruff** | `>=0.9.0` | MIT OR Apache-2.0 | `MIT OR Apache-2.0` | [ruff on GitHub](https://github.com/astral-sh/ruff) | High-speed static analysis, linting, and code quality engine. |

*Notice:* QA and linting packages are purely development-time tools and are never distributed to end users.

---

## 5. Governance & Runtime Invariants

Every release and component of **ProfiPrompt** adheres to 10 strict operational and security invariants:

| Invariant ID | Title | Scope | Description & Compliance Status |
|:---|:---|:---|:---|
| **INV-LOCAL-01** | 100% Local-First & Zero Egress | Network & Privacy | **PASS** — Zero outbound network sockets, zero telemetry, zero analytics, zero external API queries. Operates completely air-gapped. |
| **INV-OFFLINE-02** | Full Offline Autonomy | Reliability | **PASS** — All prompt management, versioning, board editing, and search operations execute locally without internet connectivity. |
| **INV-ATOMIC-03** | Atomic File Persistence | Data Integrity | **PASS** — All data writes (`prompts.json`, `boards.json`) utilize atomic tempfile + replace patterns, preventing corrupted state on sudden crash or power loss. |
| **INV-SCHEMA-04** | Open Portable Schema | Portability | **PASS** — Standardized export via `profiprompt-library-v1.json` with documented schema (`EXPORTFORMAT.md`) ensures user data is never trapped in a proprietary silo. |
| **INV-UNPRIV-05** | Non-Elevation & RunAsInvoker | Security | **PASS** — Application executes exclusively within standard unprivileged user space; no administrative or elevated rights required. |
| **INV-BACKUP-06** | Fail-Safe Backup & Recovery | Resilience | **PASS** — Automatic `.bak` snapshot generation and recovery mechanisms protect prompt libraries against external filesystem errors. |
| **INV-COPY-07** | Local Clipboard Safety | System Integration | **PASS** — Clipboard copying features (Title, Prompt, Result, Full Document) operate directly through native OS memory with sanitization and zero external logging. |
| **INV-PRINT-08** | Deterministic Multi-Format Rendering | Export Quality | **PASS** — High-fidelity document generation for TXT and PDF formats through Qt's vector print engine with robust parent directory creation. |
| **INV-PWA-09** | Read-Only Companion Isolation | Sandboxing | **PASS** — The Web/PWA companion is strictly read-only, ensuring browser sessions cannot accidentally alter or corrupt the master desktop database. |
| **INV-SLA-10** | 48h Response / 5d Triage Security SLA | Governance | **PASS** — Committed security incident response policy via `security@file-bricks.org` and `support@lukasgeiger.com` with 48h initial response SLA. |

---

## 6. License Compatibility & Redistribution Summary

- All runtime and build dependencies are licensed under permissive or weakly reciprocal (LGPLv3) open-source licenses compatible with the project's **MIT License**.
- Zero strong copyleft (GPL without exception, AGPL) components are bundled in distributed runtimes.
- No commercial restrictions or non-commercial-only clauses are present in any transitive dependency.

---

## 7. Level 1 SBOM Invariant Cross-Reference Matrix

| Invariant ID | Rule & Principle | Architectural Implementation File | Automated Verification Test File | Compliance Status |
|:---|:---|:---|:---|:---:|
| **INV-LOCAL-01** | 100% Local-First & Zero Egress | `src/storage.py`, `src/profiprompt.py` | `tests/test_security_license_contract.py` | **PASS** |
| **INV-OFFLINE-02** | Full Offline Autonomy | `src/profiprompt.py`, `web_companion/service-worker.js` | `tests/test_security_license_contract.py`, `web_companion/tests/pwa.test.mjs` | **PASS** |
| **INV-ATOMIC-03** | Atomic File Persistence | `src/storage.py` | `tests/test_storage.py` | **PASS** |
| **INV-SCHEMA-04** | Open Portable Schema | `src/storage.py`, `web_companion/library.js` | `tests/test_storage.py`, `web_companion/tests/library.test.mjs` | **PASS** |
| **INV-UNPRIV-05** | Non-Elevation & RunAsInvoker | `pyproject.toml`, `ProfiPrompt.spec` | `tests/test_security_license_contract.py` | **PASS** |
| **INV-BACKUP-06** | Fail-Safe Backup & Recovery | `src/storage.py` | `tests/test_storage.py` | **PASS** |
| **INV-COPY-07** | Local Clipboard Safety | `src/clipboard_manager.py` | `tests/test_clipboard.py`, `tests/test_security_license_contract.py` | **PASS** |
| **INV-PRINT-08** | Deterministic Multi-Format Rendering | `src/pdf_exporter.py` | `tests/test_pdf_exporter.py` | **PASS** |
| **INV-PWA-09** | Read-Only Companion Isolation | `web_companion/app.js` | `web_companion/tests/pwa.test.mjs`, `web_companion/tests/accessibility.test.mjs` | **PASS** |
| **INV-SLA-10** | 48h Response / 5d Triage Security SLA | `SECURITY.md`, `README.md` | `tests/test_security_license_contract.py` | **PASS** |

---

## 8. Non-Elevation Certification (RunAsInvoker)

`ProfiPrompt` is engineered and certified to execute entirely within standard unprivileged user space (`RunAsInvoker`).
- The application never requests, inherits, or requires Windows UAC administrative privileges or elevated root rights on POSIX platforms.
- File operations are strictly confined to the local user profile directory (`~/.prompt_manager/`) or user-selected export paths.
- System-wide registry mutations, driver installations, and privileged background services are entirely absent.

---

## 9. Zero-Copyleft Isolation Guarantee

`ProfiPrompt` maintains clean commercial and enterprise licensing compatibility under the permissive [MIT License](LICENSE):
- **LGPL-3.0 Dynamic Linking:** `PySide6` and `shiboken6` are utilized strictly as dynamically loaded shared libraries without internal modification, satisfying LGPLv3 §4 provisions.
- **Zero GPL Runtime Bundling:** Build tools utilizing GPL (such as PyInstaller) operate strictly with standard bootloader exceptions and are decoupled from distributed application logic.
- **No Network Copyleft:** Zero AGPL, SSPL, or restrictive commercial dual-licensed dependencies exist across the direct or transitive dependency tree.
