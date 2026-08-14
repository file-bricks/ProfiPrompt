from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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

# Microsoft Store: maximal 7 Suchbegriffe je Sprach-Listing.
MAX_STORE_KEYWORDS = 7

# Fremde Produkttitel duerfen nach Store-Policy 10.1.3 (Search Terms) NICHT als
# Suchbegriff verwendet werden. Die Einreichung vom 2026-08-10 wurde am
# 2026-08-11 genau deshalb abgelehnt ("ChatGPT", "Claude" in allen Listings).
FOREIGN_BRAND_TERMS = (
    "ChatGPT", "OpenAI", "GPT-4", "GPT-5", "Claude", "Anthropic", "Gemini",
    "Bard", "Copilot", "Llama", "Mistral", "Perplexity", "Midjourney",
    "Notion", "Obsidian", "Evernote", "OneNote", "Grok", "DeepSeek",
)


def matched_foreign_brand(text: str) -> str | None:
    """Gibt den ersten gefundenen fremden Produkttitel zurueck, sonst None.

    Vergleich auf Wortgrenzen, damit z. B. "Prompt Template" nicht anschlaegt.
    """
    for brand in FOREIGN_BRAND_TERMS:
        if re.search(rf"(?<!\w){re.escape(brand)}(?!\w)", text, re.IGNORECASE):
            return brand
    return None


def keyword_policy_findings(
    keywords: str, source: str, *, require_minimum: bool = True
) -> list[str]:
    """Prueft eine Suchbegriff-Liste gegen die Store-Policy.

    Wird von JEDER Datei genutzt, aus der Suchbegriffe in die Einreichung
    gelangen koennen. Die Ablehnung vom 2026-08-11 entstand, weil die Pruefung
    nur an STORE_LISTING.md hing, die Einreichung ihre Suchbegriffe aber aus
    mehreren Quellen zieht.

    `source` benennt die geprueste Datei/Stelle fuer die Meldung.
    `require_minimum` steuert die Untergrenze (nur fuer das Haupt-Listing
    sinnvoll, in dem die Suchbegriffe redaktionell gepflegt werden).
    """
    if not keywords:
        return []

    parts = [part.strip() for part in re.split(r"[,;]", keywords) if part.strip()]
    findings = []

    if require_minimum and len(parts) < 5:
        findings.append(f"{source} hat zu wenige Schlüsselwörter: {len(parts)}")
    if len(parts) > MAX_STORE_KEYWORDS:
        findings.append(
            f"{source} hat zu viele Schlüsselwörter: {len(parts)} "
            f"(Microsoft erlaubt maximal {MAX_STORE_KEYWORDS})"
        )
    for part in parts:
        hit = matched_foreign_brand(part)
        if hit:
            findings.append(
                f"{source} nennt den fremden Produkttitel \"{hit}\" als Suchbegriff "
                f"(\"{part}\") — verstößt gegen Store-Policy 10.1.3 (Search Terms) "
                f"und führte am 2026-08-11 zur Ablehnung."
            )

    return findings


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


def store_test_protocol_dir(root: Path | None = None) -> Path:
    return project_root(root) / "releases" / "windowsstore" / "test_reports"


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

    # Aus dieser Datei ziehen der MSIX-Build und das Submission-Sheet ihre
    # Suchbegriffe. Sie muss deshalb dieselbe Policy-Pruefung durchlaufen wie
    # STORE_LISTING.md - sonst bleibt genau der Weg offen, ueber den der
    # Verstoss vom 2026-08-10 in die Einreichung gelangte.
    findings.extend(
        keyword_policy_findings(
            str(settings.get("keywords", "")),
            "releases/windowsstore/store_settings.json",
            require_minimum=False,
        )
    )

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

        findings.extend(
            keyword_policy_findings(
                parsed.get("keywords", ""),
                f"STORE_LISTING.md (Abschnitt {language})",
            )
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


def display_path(path: Path, root: Path | None = None) -> str:
    base = project_root(root).resolve()
    resolved = path.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(resolved)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_protocol_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def protocol_filename(timestamp: str) -> str:
    compact = timestamp.replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
    return f"store_readiness_{compact}.md"


def _safe_findings(label: str, validator: Any, root: Path | None = None) -> list[str]:
    try:
        return list(validator(root))
    except Exception as exc:  # pragma: no cover - defensive report path
        return [f"{label}: {exc}"]


def protocol_message(message: str, root: Path | None = None) -> str:
    base = str(project_root(root).resolve())
    return message.replace(base, ".").replace("\\", "/")


def store_material_findings(root: Path | None = None) -> dict[str, list[str]]:
    validators: tuple[tuple[str, Any], ...] = (
        ("Pflichtdateien", validate_required_docs),
        ("Store-Paket", validate_store_package),
        ("Store-Settings", validate_windowsstore_settings),
        ("Store-Listing", validate_store_listing),
        ("Screenshots", validate_screenshots),
        ("MSIX", validate_msix),
        ("Build-Anleitung", validate_build_guide),
    )
    return {label: _safe_findings(label, validator, root) for label, validator in validators}


def render_status_list(findings: list[str], root: Path | None = None) -> list[str]:
    if not findings:
        return ["  - OK"]
    return [f"  - WARN: {protocol_message(finding, root)}" for finding in findings]


def render_store_test_protocol(root: Path | None = None, generated_at: str | None = None) -> str:
    base = project_root(root)
    package = load_store_package(root)
    generated = generated_at or current_protocol_timestamp()
    package_path = msix_path(root)
    materials = store_material_findings(root)

    lines = [
        "# ProfiPrompt Windows Store Testprotokoll",
        "",
        f"Erzeugt: {generated}",
        "Scope: Lokales Pre-Submission-Protokoll. Ein echter WACK-XML-Report bleibt das finale Gate.",
        "",
        "## Paket",
        "",
        f"- App: {package.get('app_name', 'unbekannt')}",
        f"- Identity: {package.get('identity_name', 'unbekannt')}",
        f"- Store-Version: {package.get('version', 'unbekannt')}",
        f"- Kategorie: {package.get('category', 'unbekannt')}",
        f"- Privacy URL: {package.get('privacy_url', 'unbekannt')}",
        f"- Support URL: {package.get('support_url', 'unbekannt')}",
        "",
        "## MSIX",
        "",
        f"- Pfad: {display_path(package_path, root)}",
    ]

    if package_path.exists():
        lines.extend(
            [
                f"- Größe: {package_path.stat().st_size} Bytes",
                f"- SHA256: {file_sha256(package_path)}",
            ]
        )
    else:
        lines.append("- Status: WARN - MSIX fehlt lokal.")

    lines.extend(["", "## Materialien", ""])
    for label, findings in materials.items():
        lines.append(f"- {label}:")
        lines.extend(render_status_list(findings, root))

    lines.extend(["", "## WACK", ""])
    try:
        report = latest_wack_report(root)
        summary = summarize_wack_report(report)
        lines.extend(
            [
                f"- Report: {display_path(report, root)}",
                f"- Gesamtergebnis: {summary['overall_result']}",
                f"- Zählung: PASS {summary['pass_count']} | FAIL {summary['fail_count']} | WARNING {summary['warning_count']}",
            ]
        )
        for requirement in summary["requirements"]:
            if requirement["result"] != "PASS":
                lines.append(f"- {requirement['result']}: {requirement['title']}")
                for detail in requirement["details"]:
                    lines.append(f"  - {detail}")
    except FileNotFoundError:
        lines.extend(
            [
                "- Status: WARN - WACK-XML fehlt.",
                "- Blocker: Keine WACK-XML-Reports im Testreport-Verzeichnis gefunden.",
                f"- Zielpfad: {display_path(store_test_protocol_dir(root), root)}/wack_YYYYMMDD_HHMMSS.xml",
            ]
        )

    all_findings = [finding for findings in materials.values() for finding in findings]
    lines.extend(["", "## Nächstes Gate", ""])
    if all_findings:
        lines.append("- Material-Warnungen zuerst beheben, dann WACK erneut ausführen.")
    else:
        lines.append("- Store-Materialien sind lokal vollständig; als Nächstes WACK als Administrator ausführen.")
    lines.append("- Danach: `python scripts/check_store_readiness.py review-wack-report`.")
    lines.append("- Finaler Preflight: `python scripts/check_store_readiness.py`.")
    lines.append("")

    # The protocol is safe to keep locally: paths are repo-relative and no user prompt data is included.
    text = "\n".join(lines)
    if str(base.resolve()) in text:
        raise ValueError("Testprotokoll enthält einen absoluten Projektpfad.")
    return text


def write_store_test_protocol(
    root: Path | None = None,
    output: Path | None = None,
    generated_at: str | None = None,
) -> Path:
    generated = generated_at or current_protocol_timestamp()
    target = output or (store_test_protocol_dir(root) / protocol_filename(generated))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_store_test_protocol(root, generated_at=generated), encoding="utf-8")
    return target.resolve()


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
        choices=("check", "review-wack-report", "write-test-protocol"),
        help=(
            "check = kompletter Store-Preflight, review-wack-report = XML-Report auswerten, "
            "write-test-protocol = lokales Store-Testprotokoll schreiben"
        ),
    )
    parser.add_argument("--report", help="Pfad zu einem konkreten WACK-XML-Report")
    parser.add_argument("--report-dir", help="Alternatives WACK-Report-Verzeichnis")
    parser.add_argument("--output", help="Zielpfad für write-test-protocol")
    parser.add_argument("--generated-at", help="ISO-Zeitstempel für reproduzierbare Protokolle")
    args = parser.parse_args(argv)

    if args.command == "review-wack-report":
        report_dir = Path(args.report_dir).resolve() if args.report_dir else None
        report = Path(args.report).resolve() if args.report else latest_wack_report(report_dir=report_dir)
        print(format_wack_summary(summarize_wack_report(report)))
        return 0

    if args.command == "write-test-protocol":
        output = Path(args.output).resolve() if args.output else None
        target = write_store_test_protocol(output=output, generated_at=args.generated_at)
        print(f"STORE TESTPROTOKOLL: {target}")
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
