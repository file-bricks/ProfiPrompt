from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RELEASES_GITHUB = _PROJECT_ROOT / "releases" / "GitHub"
_releases_present = pytest.mark.skipif(
    not _RELEASES_GITHUB.exists(),
    reason="releases/ ist gitignored und in CI nicht vorhanden; Test läuft nur im lokalen Build-Tree",
)


def load_module():
    module_path = _PROJECT_ROOT / "scripts" / "check_store_readiness.py"
    spec = importlib.util.spec_from_file_location("check_store_readiness", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_store_readiness_fixture(tmp_path: Path, *, with_wack: bool = False) -> Path:
    module = load_module()

    (tmp_path / "README" / "screenshots" / "store").mkdir(parents=True)
    (tmp_path / "releases" / "GitHub" / "v1.0.1").mkdir(parents=True)
    (tmp_path / "releases" / "windowsstore" / "test_reports").mkdir(parents=True)

    package = {
        "app_name": "ProfiPrompt",
        "publisher": "CN=52596601-BAB4-4F3F-B182-E8F3F273B202",
        "publisher_display": "Geiger",
        "identity_name": "Geiger.ProfiPrompt",
        "version": "1.0.1.0",
        "description": "Desktop-Tool zur Verwaltung und Versionierung von AI-Prompts.",
        "executable": "ProfiPrompt.exe",
        "capabilities": "internetClient,runFullTrust",
        "category": "Productivity",
        "age_rating": "3+",
        "privacy_url": "https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md",
        "support_url": "https://github.com/file-bricks/ProfiPrompt/issues",
    }
    (tmp_path / "store_package.json").write_text(
        json.dumps(package, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "releases" / "windowsstore" / "store_settings.json").write_text(
        json.dumps(
            {
                "app_name": "ProfiPrompt",
                "publisher_display": "Geiger",
                "identity_name": "Geiger.ProfiPrompt",
                "version": "1.0.1.0",
                "privacy_url": package["privacy_url"],
                "support_url": package["support_url"],
                "capabilities": package["capabilities"],
                "category": "Productivity",
                "age_rating": "3+",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README" / "screenshots" / "store" / "summary.json").write_text(
        json.dumps(
            {
                "screenshots": {
                    key: str(tmp_path / "README" / "screenshots" / "store" / f"{key}.png")
                    for key in sorted(module.REQUIRED_SCREENSHOTS)
                }
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for key in module.REQUIRED_SCREENSHOTS:
        (tmp_path / "README" / "screenshots" / "store" / f"{key}.png").write_bytes(b"png")
    (tmp_path / "releases" / "ProfiPrompt.msix").write_bytes(b"msix")
    (tmp_path / "STORE_LISTING.md").write_text(
        """# Store Listing -- ProfiPrompt

## Deutsch

### Kurzbeschreibung (max 100 Zeichen)
AI-Prompt-Manager: Prompts erstellen, versionieren, in Boards organisieren und exportieren.

### Beschreibung (max 10.000 Zeichen)
ProfiPrompt mit Web/PWA-Companion, profiprompt-library-v1.json,
https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md,
https://github.com/file-bricks/ProfiPrompt/issues, 41 Python-Tests und
30 Web/PWA-Smoke-Tests.

### Schlüsselwörter
AI Prompt, Prompt Manager, ChatGPT, Claude, LLM

### Kategorie
Productivity / AI Tools

---

## English

### Short Description (max 100 chars)
AI Prompt Manager: create, version, organize in boards, and export your prompts.

### Description (max 10,000 chars)
ProfiPrompt with Web/PWA-Companion, profiprompt-library-v1.json,
https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md,
https://github.com/file-bricks/ProfiPrompt/issues, 41 Python-Tests and
30 Web/PWA-Smoke-Tests.

### Keywords
AI Prompt, Prompt Manager, ChatGPT, Claude, LLM

### Category
Productivity / AI Tools
""",
        encoding="utf-8",
    )
    for name in module.REQUIRED_DOCS:
        if name == "STORE_LISTING.md":
            continue
        (tmp_path / name).write_text("ok", encoding="utf-8")
    (tmp_path / "releases" / "windowsstore" / "BUILD.md").write_text(
        "\n".join(
            [
                "build_exe.bat",
                "scripts\\check_store_readiness.py",
                "releases\\windowsstore\\test_reports",
                "ProfiPrompt.msix",
            ]
        ),
        encoding="utf-8",
    )
    if with_wack:
        (
            tmp_path / "releases" / "windowsstore" / "test_reports" / "wack_20260614_120000.xml"
        ).write_text(
            """<REPORT>
  <OVERALL_RESULT>PASS</OVERALL_RESULT>
  <REQUIREMENTS>
    <REQUIREMENT>
      <TITLE>Package integrity</TITLE>
      <OVERALL_RESULT>PASS</OVERALL_RESULT>
    </REQUIREMENT>
  </REQUIREMENTS>
</REPORT>
""",
            encoding="utf-8",
        )

    return tmp_path


@_releases_present
def test_store_files_match_current_release_metadata():
    module = load_module()

    package = module.load_store_package()

    assert package["app_name"] == "ProfiPrompt"
    assert package["identity_name"] == "Geiger.ProfiPrompt"
    assert package["version"] == module.expected_store_version()
    assert "runFullTrust" in package["capabilities"]


def test_store_listing_mentions_current_store_scope_and_links():
    module = load_module()
    listing = module.listing_text()

    assert "Web/PWA-Companion" in listing
    assert "profiprompt-library-v1.json" in listing
    assert "https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md" in listing
    assert "https://github.com/file-bricks/ProfiPrompt/issues" in listing

def test_parse_store_listing_sections_reads_both_languages():
    module = load_module()

    sections = module.parse_store_listing_sections(module.listing_text())

    assert sections["Deutsch"]["short_description"].startswith("AI-Prompt-Manager:")
    assert sections["Deutsch"]["category"] == "Productivity / AI Tools"
    assert sections["English"]["short_description"].startswith("AI Prompt Manager:")
    assert sections["English"]["category"] == "Productivity / AI Tools"


def test_validate_store_listing_flags_overlong_short_description_and_missing_category(tmp_path):
    module = load_module()

    (tmp_path / "releases" / "GitHub" / "v1.0.1").mkdir(parents=True)
    (tmp_path / "store_package.json").write_text(
        json.dumps(
            {
                "app_name": "ProfiPrompt",
                "identity_name": "Geiger.ProfiPrompt",
                "version": "1.0.1.0",
                "capabilities": "internetClient,runFullTrust",
                "category": "Productivity",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "STORE_LISTING.md").write_text(
        """# Store Listing -- ProfiPrompt

## Deutsch

### Kurzbeschreibung (max 100 Zeichen)
Diese Kurzbeschreibung ist absichtlich deutlich länger als einhundert Zeichen, damit der Preflight genau hier anschlägt.

### Beschreibung (max 10.000 Zeichen)
ProfiPrompt mit Web/PWA-Companion, profiprompt-library-v1.json,
https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md,
https://github.com/file-bricks/ProfiPrompt/issues, 41 Python-Tests und
30 Web/PWA-Smoke-Tests.

### Schlüsselwörter
AI Prompt, Prompt Manager, ChatGPT, Claude, LLM

### Kategorie
AI Tools

---

## English

### Short Description (max 100 chars)
AI Prompt Manager: create, version, organize in boards, and export your prompts.

### Description (max 10,000 chars)
ProfiPrompt with Web/PWA-Companion, profiprompt-library-v1.json,
https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md,
https://github.com/file-bricks/ProfiPrompt/issues, 41 Python-Tests and
30 Web/PWA-Smoke-Tests.

### Keywords
AI Prompt, Prompt Manager, ChatGPT, Claude, LLM

### Category
Productivity / AI Tools
""",
        encoding="utf-8",
    )

    findings = module.validate_store_listing(tmp_path)

    assert "STORE_LISTING.md Kurzbeschreibung überschreitet 100 Zeichen im Abschnitt Deutsch." in findings
    assert "STORE_LISTING.md Kategorie enthält nicht Productivity im Abschnitt Deutsch." in findings


@_releases_present
def test_evaluate_store_readiness_reports_only_missing_wack_report():
    module = load_module()

    findings = module.evaluate_store_readiness()

    assert findings == [f"Keine WACK-XML-Reports gefunden in: {module.WACK_REPORT_DIR}"]


def test_summarize_wack_report_counts_failures_and_warnings(tmp_path):
    module = load_module()
    report = tmp_path / "wack_20260614_120000.xml"
    report.write_text(
        """<REPORT>
  <OVERALL_RESULT>FAIL</OVERALL_RESULT>
  <REQUIREMENTS>
    <REQUIREMENT>
      <TITLE>Supported APIs</TITLE>
      <OVERALL_RESULT>PASS</OVERALL_RESULT>
    </REQUIREMENT>
    <REQUIREMENT>
      <TITLE>Package integrity</TITLE>
      <OVERALL_RESULT>FAIL</OVERALL_RESULT>
      <TEST>
        <RESULT>FAIL</RESULT>
        <DESCRIPTION>Manifest entry is invalid.</DESCRIPTION>
      </TEST>
    </REQUIREMENT>
    <REQUIREMENT>
      <TITLE>Installability</TITLE>
      <OVERALL_RESULT>WARNING</OVERALL_RESULT>
      <TEST>
        <RESULT>WARNING</RESULT>
        <DESCRIPTION>Signing check skipped in sandbox.</DESCRIPTION>
      </TEST>
    </REQUIREMENT>
  </REQUIREMENTS>
</REPORT>
""",
        encoding="utf-8",
    )

    summary = module.summarize_wack_report(report)
    rendered = module.format_wack_summary(summary)

    assert summary["overall_result"] == "FAIL"
    assert summary["pass_count"] == 1
    assert summary["fail_count"] == 1
    assert summary["warning_count"] == 1
    assert "Package integrity" in rendered
    assert "Signing check skipped in sandbox." in rendered


def test_evaluate_store_readiness_accepts_fixture_with_passing_wack_report(tmp_path):
    module = load_module()

    make_store_readiness_fixture(tmp_path, with_wack=True)

    assert module.evaluate_store_readiness(tmp_path) == []


def test_render_store_test_protocol_uses_repo_relative_paths_and_marks_wack_gate(tmp_path):
    module = load_module()
    make_store_readiness_fixture(tmp_path)

    text = module.render_store_test_protocol(tmp_path, generated_at="2026-06-25T00:00:00Z")

    assert "# ProfiPrompt Windows Store Testprotokoll" in text
    assert "releases/ProfiPrompt.msix" in text
    assert "SHA256:" in text
    assert "Status: WARN - WACK-XML fehlt." in text
    assert "releases/windowsstore/test_reports/wack_YYYYMMDD_HHMMSS.xml" in text
    assert str(tmp_path.resolve()) not in text


def test_write_store_test_protocol_creates_timestamped_markdown(tmp_path):
    module = load_module()
    make_store_readiness_fixture(tmp_path)

    target = module.write_store_test_protocol(tmp_path, generated_at="2026-06-25T00:00:00Z")

    assert target.name == "store_readiness_20260625_000000.md"
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "Erzeugt: 2026-06-25T00:00:00Z" in text
    assert "Store-Materialien sind lokal vollständig" in text
