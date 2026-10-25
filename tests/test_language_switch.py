# -*- coding: utf-8 -*-
"""Regressionstests: persistente World-Set-Sprachauswahl (ProfiPrompt).

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
from models import Board, Prompt, Version  # noqa: E402
from storage import Storage  # noqa: E402
import i18n  # noqa: E402


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

    expected_file_labels = {
        "fr": "Fichier",
        "hi": "फ़ाइल",
        "ar": "الملف",
        "bn": "ফাইল",
        "pt": "Arquivo",
    }
    for lang, expected in expected_file_labels.items():
        assert tr.set_language(lang) is True
        assert tr.t("Datei") == expected


def test_all_worldset_locales_are_complete():
    tr = TranslationSystem("de", auto_register=False)
    expected = ["en", "de", "es", "zh", "ja", "ru", "fr", "hi", "ar", "bn", "pt"]
    assert tr.get_available_languages() == expected
    assert all(tr.is_language_complete(lang) for lang in expected)


def test_settings_language_roundtrip(tmp_path):
    ini = tmp_path / "settings.ini"
    sm = SettingsManager()
    sm.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    # Default
    assert sm.get_language() == "de"
    # Speichern und Neustart-Roundtrip für alle 11 World-Set-Sprachen
    for lang in ("en", "de", "es", "zh", "ja", "ru", "fr", "hi", "ar", "bn", "pt"):
        assert sm.set_language(lang) is True
        assert sm.get_language() == lang
        sm2 = SettingsManager()
        sm2.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
        assert sm2.get_language() == lang  # "Neustart"-Simulation
    # Ungueltige Codes werden abgelehnt; kaputte gespeicherte Werte fallen auf Deutsch zurück.
    assert sm.get_language() == "pt"
    assert sm.set_language("xx") is False
    assert sm.get_language() == "pt"
    sm.qs.setValue("ui/language", "xx")
    assert sm.get_language() == "de"


def test_translator_guard_handles_corrupt_entry(tmp_path):
    # Isoliertes app_dir, damit der Test nie die echte translations.json anfasst;
    # Key ohne Deutsch-Heuristik-Treffer, damit kein Auto-Add ausgeloest wird.
    tr = TranslationSystem("de", app_dir=tmp_path)
    tr.translations["corrupt-entry-xyz"] = "not-a-dict"
    assert tr.t("corrupt-entry-xyz") == "corrupt-entry-xyz"

def test_ui_language_switch_keeps_collision_named_library_data_unchanged(tmp_path):
    store = Storage(tmp_path / "library")
    prompt = Prompt(
        id="prompt-1",
        title="Datei",
        purpose="Schließen",
        text="Nicht verändern",
        tags=["Schließen", "Datei"],
        created_at="2026-10-25T10:00:00+00:00",
        updated_at="2026-10-25T10:00:00+00:00",
        versions=[Version(
            id="version-1",
            prompt_id="prompt-1",
            version_number=1,
            title="Schließen",
            text="Datei bleibt Nutzerdatum",
            tags=["Datei"],
            created_at="2026-10-25T10:00:00+00:00",
            updated_at="2026-10-25T10:00:00+00:00",
        )],
    )
    board = Board(
        id="board-1",
        title="Schließen",
        description="Datei",
        created_at="2026-10-25T10:00:00+00:00",
    )
    store.upsert_prompt(prompt)
    store.upsert_board(board)
    prompts_before = store.prompts_file.read_bytes()
    boards_before = store.boards_file.read_bytes()
    original_language = i18n.get_language()
    try:
        for language in ("en", "de", "es", "zh", "ja", "ru", "fr", "hi", "ar", "bn", "pt"):
            assert i18n.set_language(language) is True
            prompts, boards = store.load_library()
            assert prompts[0].id == "prompt-1"
            assert prompts[0].title == "Datei"
            assert prompts[0].purpose == "Schließen"
            assert prompts[0].tags == ["Schließen", "Datei"]
            assert prompts[0].versions[0].title == "Schließen"
            assert prompts[0].versions[0].tags == ["Datei"]
            assert boards[0].id == "board-1"
            assert boards[0].title == "Schließen"
            assert boards[0].description == "Datei"
            assert store.prompts_file.read_bytes() == prompts_before
            assert store.boards_file.read_bytes() == boards_before
    finally:
        i18n.init(original_language)
