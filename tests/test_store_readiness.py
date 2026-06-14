from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "check_store_readiness.py"
    spec = importlib.util.spec_from_file_location("check_store_readiness", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    (tmp_path / "README" / "screenshots" / "store").mkdir(parents=True)
    (tmp_path / "releases" / "GitHub" / "v1.0.1").mkdir(parents=True)
    (tmp_path / "releases" / "windowsstore" / "test_reports").mkdir(parents=True)
    (tmp_path / "releases").mkdir(exist_ok=True)

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
        "\n".join(
            [
                "Web/PWA-Companion",
                "profiprompt-library-v1.json",
                "https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md",
                "https://github.com/file-bricks/ProfiPrompt/issues",
                    "41 Python-Tests",
                "30 Web/PWA-Smoke-Tests",
            ]
        ),
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

    assert module.evaluate_store_readiness(tmp_path) == []
