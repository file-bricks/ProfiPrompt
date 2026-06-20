from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README_STORE_DIR = PROJECT_ROOT / "README" / "screenshots" / "store"
WACK_REPORT_DIR = PROJECT_ROOT / "releases" / "windowsstore" / "test_reports"

REQUIRED_DOCS = (
    "STORE_LISTING.md",
    "PRIVACY_POLICY.md",
    "SECURITY.md",
    "THIRD_PARTY_LICENSES.txt",
)
REQUIRED_SCREENSHOTS = {
    "main-window",
    "search-and-versions",
    "boards-and-launch",
    "support-focus",
}
REQUIRED_LISTING_MARKERS = (
    "Web/PWA-Companion",
    "profiprompt-library-v1.json",
    "https://github.com/file-bricks/ProfiPrompt/blob/master/PRIVACY_POLICY.md",
    "https://github.com/file-bricks/ProfiPrompt/issues",
)
LISTING_FIELD_LABELS = {
    "Deutsch": {
        "short_description": "Kurzbeschreibung",
        "description": "Beschreibung",
        "keywords": "Schlüsselwörter",
        "category": "Kategorie",
    },
    "English": {
        "short_description": "Short Description",
        "description": "Description",
        "keywords": "Keywords",
        "category": "Category",
    },
}


def project_root(root: Path | None = None) -> Path:
    return root or PROJECT_ROOT


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Ungültige JSON-Struktur in {path}")
    return data


def store_package_path(root: Path | None = None) -> Path:
    return project_root(root) / "store_package.json"


def windowsstore_settings_path(root: Path | None = None) -> Path:
    return project_root(root) / "releases" / "windowsstore" / "store_settings.json"


def msix_path(root: Path | None = None) -> Path:
    return project_root(root) / "releases" / "ProfiPrompt.msix"


def screenshot_summary_path(root: Path | None = None) -> Path:
    return project_root(root) / "README" / "screenshots" / "store" / "summary.json"


def build_guide_path(root: Path | None = None) -> Path:
    return project_root(root) / "releases" / "windowsstore" / "BUILD.md"


def latest_release_version(root: Path | None = None) -> str:
    release_root = project_root(root) / "releases" / "GitHub"
    versions: list[tuple[int, ...]] = []
    version_map: dict[tuple[int, ...], str] = {}
    for entry in release_root.iterdir():
        if not entry.is_dir():
            continue
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", entry.name)
        if match is None:
            continue
        key = tuple(int(part) for part in match.groups())
        versions.append(key)
        version_map[key] = ".".join(match.groups())
    if not versions:
        raise FileNotFoundError(f"Keine GitHub-Release-Ordner gefunden in {release_root}")
    return version_map[max(versions)]


def expected_store_version(root: Path | None = None) -> str:
    return f"{latest_release_version(root)}.0"


def load_store_package(root: Path | None = None) -> dict[str, Any]:
    return read_json(store_package_path(root))


def load_windowsstore_settings(root: Path | None = None) -> dict[str, Any]:
    return read_json(windowsstore_settings_path(root))


def load_screenshot_summary(root: Path | None = None) -> dict[str, Any]:
    return read_json(screenshot_summary_path(root))


def listing_text(root: Path | None = None) -> str:
    return (project_root(root) / "STORE_LISTING.md").read_text(encoding="utf-8")


def parse_store_listing_sections(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {language: {} for language in LISTING_FIELD_LABELS}
    current_language: str | None = None
    current_field: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if current_language is None or current_field is None:
            buffer = []
            return
        value = "\n".join(buffer).strip()
        if value:
            sections[current_language][current_field] = value
        buffer = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            flush()
            candidate = stripped[3:].strip()
            current_language = candidate if candidate in LISTING_FIELD_LABELS else None
            current_field = None
            continue
        if current_language and stripped.startswith("### "):
            flush()
            heading = stripped[4:].strip()
            current_field = next(
                (
                    field
                    for field, label in LISTING_FIELD_LABELS[current_language].items()
                    if heading.startswith(label)
                ),
                None,
            )
            continue
        if stripped == "---":
            flush()
            current_language = None
            current_field = None
            continue
        if current_language and current_field:
            buffer.append(raw_line)

    flush()
    return sections


def validate_required_docs(root: Path | None = None) -> list[str]:
    base = project_root(root)
    findings = []
    for relative in REQUIRED_DOCS:
        if not (base / relative).exists():
            findings.append(f"Fehlende Store-Datei: {relative}")
    return findings


def validate_store_package(root: Path | None = None) -> list[str]:
    package = load_store_package(root)
    findings = []

    if package.get("app_name") != "ProfiPrompt":
        findings.append("store_package.json hat einen unerwarteten App-Namen.")
    if package.get("identity_name") != "Geiger.ProfiPrompt":
        findings.append("store_package.json hat einen unerwarteten Identity-Namen.")
    if package.get("version") != expected_store_version(root):
        findings.append(
            f"Store-Version stimmt nicht: {package.get('version')} != {expected_store_version(root)}"
        )

    capabilities = {part.strip() for part in str(package.get("capabilities", "")).split(",") if part.strip()}
    if "runFullTrust" not in capabilities:
        findings.append("Store-Paket muss runFullTrust enthalten.")

    return findings


def validate_windowsstore_settings(root: Path | None = None) -> list[str]:
    settings_path = windowsstore_settings_path(root)
    if not settings_path.exists():
        return []
    package = load_store_package(root)
    settings = read_json(settings_path)
    findings = []

    for key in ("app_name", "publisher_display", "identity_name", "category", "age_rating"):
        if settings.get(key) != package.get(key):
            findings.append(f"Store-Settings weichen bei {key} von store_package.json ab.")

    if settings.get("version") != package.get("version"):
        findings.append("Store-Settings verwenden nicht die aktuelle Store-Version.")
    if settings.get("privacy_url") != package.get("privacy_url"):
        findings.append("Store-Settings verwenden nicht die aktuelle Privacy-URL.")
    if settings.get("support_url") != package.get("support_url"):
        findings.append("Store-Settings verwenden nicht die aktuelle Support-URL.")
    if settings.get("capabilities") != package.get("capabilities"):
        findings.append("Store-Settings verwenden nicht die aktuellen Capabilities.")

    return findings


def validate_store_listing(root: Path | None = None) -> list[str]:
    text = listing_text(root)
    sections = parse_store_listing_sections(text)
    expected_category = str(load_store_package(root).get("category", "")).strip()
    findings = []

    for marker in REQUIRED_LISTING_MARKERS:
        if marker not in text:
            findings.append(f"STORE_LISTING.md erwähnt nicht: {marker}")

    if "41 Python-Tests" not in text:
        findings.append("STORE_LISTING.md nennt nicht den aktuellen Python-Teststand.")
    if "30 Web/PWA-Smoke-Tests" not in text and "30 Web/PWA smoke tests" not in text:
        findings.append("STORE_LISTING.md nennt nicht den aktuellen Web/PWA-Teststand.")

    for language, labels in LISTING_FIELD_LABELS.items():
        parsed = sections.get(language, {})
        for field, label in labels.items():
            value = parsed.get(field, "")
            if not value:
                findings.append(f"STORE_LISTING.md fehlt im Abschnitt {language}: {label}")
                continue
            if "TODO" in value:
                findings.append(f"STORE_LISTING.md enthält TODO-Platzhalter im Abschnitt {language}: {label}")

        short_description = parsed.get("short_description", "")
        if short_description:
            if "\n" in short_description:
                findings.append(
                    f"STORE_LISTING.md Kurzbeschreibung ist im Abschnitt {language} mehrzeilig."
                )
            if len(short_description) > 100:
                findings.append(
                    f"STORE_LISTING.md Kurzbeschreibung überschreitet 100 Zeichen im Abschnitt {language}."
                )

        description = parsed.get("description", "")
        if description and "ProfiPrompt" not in description:
            findings.append(f"STORE_LISTING.md nennt den App-Namen nicht im Abschnitt {language}.")

        keywords = parsed.get("keywords", "")
        if keywords:
            keyword_count = len([part.strip() for part in re.split(r"[,;]", keywords) if part.strip()])
            if keyword_count < 5:
                findings.append(
                    f"STORE_LISTING.md hat zu wenige Schlüsselwörter im Abschnitt {language}: {keyword_count}"
                )

        category = parsed.get("category", "")
        if category and expected_category and expected_category not in category:
            findings.append(
                f"STORE_LISTING.md Kategorie enthält nicht {expected_category} im Abschnitt {language}."
            )

    return findings


def validate_screenshots(root: Path | None = None) -> list[str]:
    summary = load_screenshot_summary(root)
    findings = []
    screenshots = summary.get("screenshots", {})
    if set(screenshots) != REQUIRED_SCREENSHOTS:
        findings.append("Store-Screenshot-Summary ist unvollständig oder enthält unerwartete Keys.")
        return findings

    for key, raw_path in screenshots.items():
        path = Path(raw_path)
        if not path.is_absolute():
            path = project_root(root) / path
        if not path.exists():
            findings.append(f"Store-Screenshot fehlt: {key} -> {path}")

    return findings


def validate_msix(root: Path | None = None) -> list[str]:
    package_path = msix_path(root)
    if not package_path.exists():
        return [f"MSIX fehlt: {package_path}"]
    if package_path.stat().st_size <= 0:
        return [f"MSIX ist leer: {package_path}"]
    return []


def build_guide_text(root: Path | None = None) -> str:
    return build_guide_path(root).read_text(encoding="utf-8")


def validate_build_guide(root: Path | None = None) -> list[str]:
    guide_path = build_guide_path(root)
    if not guide_path.exists():
        return []
    text = build_guide_text(root)
    findings = []
    for marker in (
        "build_exe.bat",
        "check_store_readiness.py",
        "test_reports",
        "ProfiPrompt.msix",
    ):
        if marker not in text:
            findings.append(f"BUILD.md erwähnt nicht: {marker}")
    return findings


def latest_wack_report(root: Path | None = None, report_dir: Path | None = None) -> Path:
    target_dir = report_dir or (project_root(root) / "releases" / "windowsstore" / "test_reports")
    if not target_dir.exists():
        raise FileNotFoundError(f"WACK-Report-Verzeichnis fehlt: {target_dir}")

    candidates = sorted(
        target_dir.glob("wack_*.xml"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"Keine WACK-XML-Reports gefunden in: {target_dir}")
    return candidates[0].resolve()


def summarize_wack_report(report_path: str | Path) -> dict[str, Any]:
    resolved = Path(report_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"WACK-Report nicht gefunden: {resolved}")

    root = ET.fromstring(resolved.read_text(encoding="utf-8"))
    requirements = []
    counts = {"PASS": 0, "FAIL": 0, "WARNING": 0}

    for requirement in root.findall("./REQUIREMENTS/REQUIREMENT"):
        title = (requirement.findtext("TITLE") or "").strip() or "Unbenannter Test"
        result = (requirement.findtext("OVERALL_RESULT") or "UNKNOWN").strip() or "UNKNOWN"
        details = []
        for test in requirement.findall("TEST"):
            test_result = (test.findtext("RESULT") or "").strip()
            description = (test.findtext("DESCRIPTION") or "").strip()
            if test_result in {"FAIL", "WARNING"} and description:
                details.append(description)
        requirements.append({"title": title, "result": result, "details": details})
        if result in counts:
            counts[result] += 1

    return {
        "report_path": str(resolved),
        "overall_result": (root.findtext("OVERALL_RESULT") or "UNKNOWN").strip() or "UNKNOWN",
        "pass_count": counts["PASS"],
        "fail_count": counts["FAIL"],
        "warning_count": counts["WARNING"],
        "requirements": requirements,
    }


def format_wack_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"Report: {summary['report_path']}",
        f"Gesamtergebnis: {summary['overall_result']}",
        f"PASS {summary['pass_count']} | FAIL {summary['fail_count']} | WARNING {summary['warning_count']}",
    ]
    for requirement in summary["requirements"]:
        if requirement["result"] == "PASS":
            continue
        lines.append(f"- {requirement['result']}: {requirement['title']}")
        for detail in requirement["details"]:
            lines.append(f"  -> {detail}")
    return "\n".join(lines)


def evaluate_store_readiness(root: Path | None = None) -> list[str]:
    findings: list[str] = []
    for validator in (
        validate_required_docs,
        validate_store_package,
        validate_windowsstore_settings,
        validate_store_listing,
        validate_screenshots,
        validate_msix,
        validate_build_guide,
    ):
        findings.extend(validator(root))

    try:
        summary = summarize_wack_report(latest_wack_report(root))
    except FileNotFoundError as exc:
        findings.append(str(exc))
        return findings

    if summary["overall_result"] != "PASS":
        findings.append(
            f"WACK-Gesamtergebnis ist {summary['overall_result']} statt PASS: {summary['report_path']}"
        )
    if summary["fail_count"] or summary["warning_count"]:
        findings.append(
            "WACK-Report enthält offene Befunde: "
            f"{summary['fail_count']} FAIL / {summary['warning_count']} WARNING"
        )
    return findings


def render_findings(findings: Iterable[str]) -> str:
    return "\n".join(f"- {finding}" for finding in findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ProfiPrompt Windows-Store-Readiness prüfen")
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "review-wack-report"),
        help="check = kompletter Store-Preflight, review-wack-report = XML-Report auswerten",
    )
    parser.add_argument("--report", help="Pfad zu einem konkreten WACK-XML-Report")
    parser.add_argument("--report-dir", help="Alternatives WACK-Report-Verzeichnis")
    args = parser.parse_args(argv)

    if args.command == "review-wack-report":
        report_dir = Path(args.report_dir).resolve() if args.report_dir else None
        report = Path(args.report).resolve() if args.report else latest_wack_report(report_dir=report_dir)
        print(format_wack_summary(summarize_wack_report(report)))
        return 0

    findings = evaluate_store_readiness()
    if findings:
        print("STORE READINESS: WARN")
        print(render_findings(findings))
        return 1

    print("STORE READINESS: OK")
    print(f"- store_version: {expected_store_version()}")
    print(f"- msix: {msix_path().resolve()}")
    print(f"- screenshots: {screenshot_summary_path().resolve()}")
    print(f"- latest_wack: {latest_wack_report().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
