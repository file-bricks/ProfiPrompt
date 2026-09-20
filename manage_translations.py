"""
manage_translations.py - Multi-Language Scanner & Parity Validator
===================================================================
Policy P-006 Tier-2 6-Sprachen-Standard (DE, EN, ES, ZH, JA, RU).

Verwendung:
    python manage_translations.py --check
    python manage_translations.py --scan [--dir PROJEKTDIR]
    python manage_translations.py [--dir PROJEKTDIR]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from translator import TranslationSystem

SUPPORTED_LANGUAGES = TranslationSystem.SUPPORTED_LANGUAGES
TRANSLATION_FILE = "locales/translations.json"


def check_translations(source_dir: str = ".") -> int:
    """Prüft translations.json auf 100% Parität über alle 6 Sprachen."""
    trans_file = Path(source_dir) / TRANSLATION_FILE
    if not trans_file.is_file():
        print(f"[!] Übersetzungsdatei nicht gefunden: {trans_file}")
        return 1

    try:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[!] Fehler beim Lesen von {trans_file}: {exc}")
        return 1

    total_keys = len(data)
    print(f"=== Translation Parity Check: {total_keys} Keys in {trans_file} ===")

    missing: Dict[str, List[str]] = {lang: [] for lang in SUPPORTED_LANGUAGES}
    for key, trans in data.items():
        if not isinstance(trans, dict):
            print(f"[!] Ungültiger Eintrag (kein dict) für Key: {key}")
            return 1
        for lang in SUPPORTED_LANGUAGES:
            val = trans.get(lang)
            if not val or not isinstance(val, str) or not val.strip():
                missing[lang].append(key)

    has_error = False
    for lang in SUPPORTED_LANGUAGES:
        lang_missing = missing[lang]
        status = "OK" if not lang_missing else f"FEHLEN {len(lang_missing)}"
        print(f"  [{status}] {lang} ({TranslationSystem.LANGUAGE_NAMES.get(lang, lang)}): {total_keys - len(lang_missing)}/{total_keys}")
        if lang_missing:
            has_error = True
            for m in lang_missing[:5]:
                print(f"       - {m}")
            if len(lang_missing) > 5:
                print(f"       ... und {len(lang_missing) - 5} weitere")

    if has_error:
        print("\n[!] Translation Parity Check FEHLGESCHLAGEN.")
        return 1

    print("\n[ok] 100% Parität über alle 6 Sprachen nach Policy P-006.")
    return 0


def scan_and_update(source_dir: str = ".") -> int:
    ts = TranslationSystem("de", app_dir=Path(source_dir))
    stats = ts.scan_and_update(Path(source_dir))
    print(f"[+] Gesamt: {stats['total']} Keys in {ts.translations_file}")
    if stats["added"]:
        print(f"[+] {len(stats['added'])} neue Keys hinzugefügt.")
    else:
        print("[i] Keine neuen Keys gefunden.")

    has_missing = False
    for lang, items in stats["missing"].items():
        if items:
            has_missing = True
            print(f"[!] {lang}: {len(items)} fehlende Übersetzungen")

    if not has_missing:
        print("[ok] Alle Keys sind vollständig übersetzt.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ProfiPrompt Translation Manager & Parity Validator")
    parser.add_argument("--check", action="store_true", help="Prüfe 100% Parität über alle 6 Sprachen")
    parser.add_argument("--scan", action="store_true", help="Scanne Python-Dateien nach neuen Strings")
    parser.add_argument("--dir", default=".", help="Projektverzeichnis (Default: .)")

    args, unknown = parser.parse_known_args()

    # Fallback wenn positional dir übergeben wurde
    source_dir = args.dir
    if unknown and not source_dir:
        source_dir = unknown[0]

    if args.check:
        return check_translations(source_dir)
    if args.scan:
        return scan_and_update(source_dir)

    # Standard wenn keine Flags: scan_and_update + check
    scan_res = scan_and_update(source_dir)
    check_res = check_translations(source_dir)
    return 1 if (scan_res != 0 or check_res != 0) else 0


if __name__ == "__main__":
    sys.exit(main())
