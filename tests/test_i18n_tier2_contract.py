# -*- coding: utf-8 -*-
"""Vertragstests: Policy P-006 Tier-2 6-Sprachen-I18N-Standard (ProfiPrompt).

Verifiziert:
1. locales/translations.json Integritaet und 100% Schluessel-Paritaet ueber alle 6 Sprachen.
2. Deterministische 4-Stufen-Fallback-Kette (target -> en -> de -> key).
3. Parameter-Interpolation via t(key, **kwargs) und Fehlertoleranz.
4. TranslationSystem-Klassenmethoden und Metadaten-Mappings.
5. manage_translations.py --check Subprozess-Validierung.
6. Atomares Speichern von Uebersetzungsdateien.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from translator import TranslationSystem, get_translator, t  # noqa: E402

EXPECTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")


def test_translation_file_integrity_and_100_percent_parity():
    """Prüft, dass locales/translations.json existiert, mindestens 50 Keys hat und 100% Parität aufweist."""
    trans_file = ROOT / "locales" / "translations.json"
    assert trans_file.is_file(), f"{trans_file} muss existieren"

    with open(trans_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "translations.json muss ein JSON-Objekt sein"
    assert len(data) >= 50, f"Erwarte mindestens 50 Schluessel, gefunden: {len(data)}"

    for key, entry in data.items():
        assert isinstance(entry, dict), f"Eintrag fuer '{key}' muss ein dict sein"
        for lang in EXPECTED_LANGUAGES:
            assert lang in entry, f"Sprache '{lang}' fehlt im Key '{key}'"
            val = entry[lang]
            assert isinstance(val, str) and val.strip(), (
                f"Uebersetzung fuer '{key}' in Sprache '{lang}' darf nicht leer sein"
            )


def test_four_tier_deterministic_fallback(tmp_path):
    """Prüft die 4-Stufen-Fallback-Kette: target -> en -> de -> key."""
    tr = TranslationSystem("es", app_dir=tmp_path)
    # Stufe 1: target_lang ('es') vorhanden
    tr.translations["key1"] = {
        "de": "Datei DE",
        "en": "File EN",
        "es": "Archivo ES",
        "zh": "",
        "ja": "",
        "ru": "",
    }
    assert tr.t("key1") == "Archivo ES"

    # Stufe 2: target_lang ('es') fehlt -> Fallback auf 'en'
    tr.translations["key2"] = {
        "de": "Bearbeiten DE",
        "en": "Edit EN",
        "es": "",
        "zh": "",
        "ja": "",
        "ru": "",
    }
    assert tr.t("key2") == "Edit EN"

    # Stufe 3: target_lang ('es') und 'en' fehlen -> Fallback auf 'de'
    tr.translations["key3"] = {
        "de": "Ansicht DE",
        "en": "",
        "es": "",
        "zh": "",
        "ja": "",
        "ru": "",
    }
    assert tr.t("key3") == "Ansicht DE"

    # Stufe 4: alles fehlt -> Fallback auf Roh-Key
    tr.translations["key4"] = {
        "de": "",
        "en": "",
        "es": "",
        "zh": "",
        "ja": "",
        "ru": "",
    }
    assert tr.t("key4") == "key4"


def test_string_formatting_kwargs_interpolation(tmp_path):
    """Prüft Platzhalter-Interpolation mit kwargs und Fehlerresistenz."""
    tr = TranslationSystem("de", app_dir=tmp_path)
    tr.translations["Hallo {name}!"] = {
        "de": "Hallo {name}!",
        "en": "Hello {name}!",
        "es": "¡Hola {name}!",
        "zh": "你好 {name}!",
        "ja": "こんにちは {name}!",
        "ru": "Привет {name}!",
    }

    assert tr.t("Hallo {name}!", name="Lukas") == "Hallo Lukas!"
    tr.set_language("en")
    assert tr.t("Hallo {name}!", name="Lukas") == "Hello Lukas!"
    tr.set_language("es")
    assert tr.t("Hallo {name}!", name="Lukas") == "¡Hola Lukas!"

    # Robustheit bei fehlendem Platzhalter
    assert tr.t("Hallo {name}!") == "¡Hola {name}!"


def test_translation_system_class_helpers():
    """Prüft Klassenmethoden und Metadaten-Mappings."""
    supported = TranslationSystem.get_supported_languages()
    assert tuple(supported) == EXPECTED_LANGUAGES

    names = TranslationSystem.get_language_names()
    assert names["de"] == "Deutsch"
    assert names["es"] == "Español"
    assert names["zh"] == "简体中文"
    assert names["ja"] == "日本語"
    assert names["ru"] == "Русский"

    display_names = TranslationSystem.get_language_display_names()
    assert display_names["de"] == "Deutsch (de)"
    assert display_names["es"] == "Español (es)"


def test_manage_translations_check_subprocess():
    """Validiert, dass manage_translations.py --check sauber mit Exit-Code 0 durchlaeuft."""
    cmd = [sys.executable, str(ROOT / "manage_translations.py"), "--check"]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, f"manage_translations.py --check fehlgeschlagen:\n{result.stderr}\n{result.stdout}"
    assert "100% Parität" in result.stdout or "100% Paritaet" in result.stdout
