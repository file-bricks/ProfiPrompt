"""Automated security, dependency floor, and third-party license contract tests for ProfiPrompt."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_vulnerability_floors() -> None:
    """Verify requirements.txt and pyproject.toml enforce patched dependency floors against CVEs."""
    req_file = ROOT / "requirements.txt"
    assert req_file.is_file(), "requirements.txt must exist"
    req_text = req_file.read_text(encoding="utf-8")

    assert re.search(r"^PySide6\s*>=\s*6\.5\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce PySide6>=6.5.0 floor"
    )

    pyproject_file = ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist"
    pyproject_text = pyproject_file.read_text(encoding="utf-8")

    # PEP 621 dependencies section
    assert "dependencies = [" in pyproject_text, "pyproject.toml must define project.dependencies"
    assert "PySide6>=6.5.0" in pyproject_text, "pyproject.toml must specify PySide6>=6.5.0"

    # Dev optional dependencies floor (pytest >= 9.1.1 protects against CVE-2025-7117 / GHSA-6w46-j5rx-g56g)
    assert "[project.optional-dependencies]" in pyproject_text, "pyproject.toml must define optional-dependencies"
    assert "pytest>=9.1.1" in pyproject_text, "pyproject.toml dev dependencies must require pytest>=9.1.1"
    assert "ruff>=0.9.0" in pyproject_text, "pyproject.toml dev dependencies must require ruff>=0.9.0"
    assert "pyinstaller>=6.10.0" in pyproject_text, "pyproject.toml build dependencies must require pyinstaller>=6.10.0"

    # Check author contact email
    assert "support@lukasgeiger.com" in pyproject_text, "pyproject.toml must use official support email"


def test_third_party_licenses_complete_and_accurate() -> None:
    """Verify THIRD_PARTY_LICENSES.txt comprehensively covers runtime, packaging, and test packages."""
    license_file = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert license_file.is_file(), "THIRD_PARTY_LICENSES.txt must exist"
    content = license_file.read_text(encoding="utf-8")

    required_packages = [
        ("PySide6", "LGPL-3.0-only"),
        ("shiboken6", "LGPL-3.0-only"),
        ("PyInstaller", "GPL-2.0-or-later WITH Bootloader-exception"),
        ("pyinstaller-hooks-contrib", "Apache-2.0"),
        ("altgraph", "MIT"),
        ("packaging", "Apache-2.0 OR BSD-2-Clause"),
        ("pytest", "MIT"),
        ("pluggy", "MIT"),
        ("iniconfig", "MIT"),
        ("ruff", "MIT OR Apache-2.0"),
    ]

    for pkg, spdx in required_packages:
        assert pkg in content, f"Package {pkg} missing from THIRD_PARTY_LICENSES.txt"
        assert spdx in content, f"SPDX identifier {spdx} for {pkg} missing from THIRD_PARTY_LICENSES.txt"

    # Ensure structured schema fields exist
    assert "License:" in content, "License: field missing in THIRD_PARTY_LICENSES.txt"
    assert "URL:" in content, "URL: field missing in THIRD_PARTY_LICENSES.txt"
    assert "SPDX:" in content, "SPDX: field missing in THIRD_PARTY_LICENSES.txt"


def test_gitignore_security_and_multi_host_hardening() -> None:
    """Verify .gitignore blocks private secrets, certificates, and multi-host conflict files."""
    gitignore_file = ROOT / ".gitignore"
    assert gitignore_file.is_file(), ".gitignore must exist"
    content = gitignore_file.read_text(encoding="utf-8")

    # Secrets and certificate protection
    for pat in ["credentials.json", "*.pfx", "*.pem", "*.key", "keyring/", "secrets.*"]:
        assert pat in content, f"Secret pattern {pat} missing in .gitignore"

    # Multi-host sync hardening
    for host_pat in ["*-WORKSTATION-LG*", "*-ASUS-GEI*", "*.sync-conflict-*", "*.conflict"]:
        assert host_pat in content, f"Sync conflict pattern {host_pat} missing in .gitignore"

    # Multi-agent lock system fail-closed patterns
    for lock_pat in ["LOCK.*", "*.lock", "LOCK*.txt"]:
        assert lock_pat in content, f"Lock pattern {lock_pat} missing in .gitignore"

    # Web companion test cache patterns
    assert "node_modules/" in content, "node_modules/ pattern missing in .gitignore"


def test_no_hardcoded_user_paths_in_python_code() -> None:
    """Verify no hardcoded personal user profile paths exist in active Python source and tests."""
    disallowed_regex = re.compile(r"""(?i)C:[/\\]Users[/\\](?:lukas|admin|administrator)[/\\]""", re.VERBOSE)

    python_files = list(ROOT.glob("*.py")) + list((ROOT / "src").glob("*.py")) + list((ROOT / "tests").glob("*.py"))
    assert len(python_files) >= 15, "Expected at least 15 Python files to scan"

    violating_lines = []
    for py_file in python_files:
        if not py_file.is_file():
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if disallowed_regex.search(line):
                violating_lines.append(f"{py_file.name}:{idx}: {line.strip()}")

    assert not violating_lines, "Found hardcoded user paths in Python code:\n" + "\n".join(violating_lines)


def test_security_policy_bilingual_and_sla() -> None:
    """Verify SECURITY.md provides bilingual policy, security contact addresses, and 48h SLA."""
    sec_file = ROOT / "SECURITY.md"
    assert sec_file.is_file(), "SECURITY.md must exist"
    sec_text = sec_file.read_text(encoding="utf-8")

    assert "## Deutsch" in sec_text, "SECURITY.md must contain German section"
    assert "## English" in sec_text, "SECURITY.md must contain English section"

    # Contact addresses
    assert "security@file-bricks.org" in sec_text, "SECURITY.md must list security@file-bricks.org"
    assert "support@lukasgeiger.com" in sec_text, "SECURITY.md must list support@lukasgeiger.com"

    # SLA commitment
    assert "48" in sec_text, "SECURITY.md must define 48-hour response SLA"
    assert "Local-First" in sec_text, "SECURITY.md must document Local-First commitment"


def test_local_first_and_offline_invariants() -> None:
    """Verify absence of unapproved telemetry, analytics, and remote trackers."""
    disallowed_patterns = [
        re.compile(r"google-analytics\.com", re.IGNORECASE),
        re.compile(r"mixpanel\.com", re.IGNORECASE),
        re.compile(r"segment\.io", re.IGNORECASE),
        re.compile(r"sentry\.io", re.IGNORECASE),
    ]

    core_files = [
        ROOT / "src" / "profiprompt.py",
        ROOT / "src" / "storage.py",
        ROOT / "src" / "clipboard_manager.py",
        ROOT / "src" / "pdf_exporter.py",
        ROOT / "web_companion" / "app.js",
        ROOT / "web_companion" / "service-worker.js",
    ]

    for source_file in core_files:
        if not source_file.is_file():
            continue
        text = source_file.read_text(encoding="utf-8")
        for pat in disallowed_patterns:
            assert not pat.search(text), f"Found disallowed telemetry/analytics pattern {pat.pattern} in {source_file.name}"
