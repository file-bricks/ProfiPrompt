# -*- coding: utf-8 -*-
"""Regressionstests: Welle-1 U1 — sichtbarer DE/EN-Sprachschalter (ProfiPrompt).

Prueft die Menue-Uebersetzungen, die Persistenz der Spracheinstellung in den
QSettings und den isinstance-Guard des TranslationSystem (headless, ohne GUI).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PySide6 import QtCore  # noqa: E402
import profiprompt  # noqa: E402
from settings_manager import SettingsManager  # noqa: E402
from translator import TranslationSystem  # noqa: E402


def test_menu_keys_translate():
    tr = profiprompt.make_translator("de")
    assert tr is not None, "TranslationSystem sollte verfuegbar sein"
    # Default DE = Originaltext
    assert tr.t("Datei") == "Datei"
    assert tr.t("Beenden") == "Beenden"
    # Umschalten auf EN
    tr.set_language("en")
    assert tr.t("Datei") == "File"
    assert tr.t("Beenden") == "Quit"
    assert tr.t("Bearbeiten") == "Edit"
    assert tr.t("Über Prompt Manager") == "About Prompt Manager"
    # Umschalten auf ES (Tier-2)
    tr.set_language("es")
    assert tr.t("Datei") == "Archivo"
    assert tr.t("Beenden") == "Salir"
    assert tr.t("Hilfe") == "Ayuda"
    # Umschalten auf ZH (Tier-2)
    tr.set_language("zh")
    assert tr.t("Datei") == "文件"
    assert tr.t("Hilfe") == "帮助"
    # Umschalten auf JA (Tier-2)
    tr.set_language("ja")
    assert tr.t("Datei") == "ファイル"
    assert tr.t("Hilfe") == "ヘルプ"
    # Umschalten auf RU (Tier-2)
    tr.set_language("ru")
    assert tr.t("Datei") == "Файл"
    assert tr.t("Hilfe") == "Справка"


def test_settings_language_roundtrip(tmp_path):
    ini = tmp_path / "settings.ini"
    sm = SettingsManager()
    sm.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    # Default
    assert sm.get_language() == "de"
    # Speichern + persistiert auf Platte fuer alle 6 Sprachen
    for lang in ("en", "es", "zh", "ja", "ru", "de"):
        sm.set_language(lang)
        assert sm.get_language() == lang
        sm2 = SettingsManager()
        sm2.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
        assert sm2.get_language() == lang  # "Neustart"-Simulation
    # Ungueltige Sprache wird abgelehnt
    sm.set_language("fr")
    assert sm.get_language() == "de"


def test_translator_guard_handles_corrupt_entry(tmp_path):
    # Isoliertes app_dir, damit der Test nie die echte translations.json anfasst;
    # Key ohne Deutsch-Heuristik-Treffer, damit kein Auto-Add ausgeloest wird.
    tr = TranslationSystem("de", app_dir=tmp_path)
    tr.translations["corrupt-entry-xyz"] = "not-a-dict"
    assert tr.t("corrupt-entry-xyz") == "corrupt-entry-xyz"
