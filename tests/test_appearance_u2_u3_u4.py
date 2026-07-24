# -*- coding: utf-8 -*-
"""Regressionstests: Welle-1 U2 (Theme Hell/Dunkel), U3 (Kachelfarben),
U4 (transparente UI-Icons) fuer ProfiPrompt.

Deckt Persistenz (QSettings), die Theme-/Farb-Helfer aus theme.py, den
Appearance-Dialog und das Vorhandensein transparenter Icons ab. Laeuft headless
(offscreen) ueber die conftest-Fixtures.
"""
import os

from PySide6 import QtCore, QtGui

import theme as theme_mod
from settings_manager import SettingsManager

ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "icons")


def _isolated_settings(tmp_path):
    """SettingsManager mit temporaerem Ini-Backend (kein echtes %APPDATA%)."""
    sm = SettingsManager()
    sm.qs = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.IniFormat)
    return sm


# --- U2: Theme-Persistenz -----------------------------------------------------
def test_theme_default_is_dark(tmp_path):
    sm = _isolated_settings(tmp_path)
    assert sm.get_theme() == "dark"


def test_theme_roundtrip_persists(tmp_path):
    ini = tmp_path / "settings.ini"
    sm = SettingsManager()
    sm.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    sm.set_theme("light")
    assert sm.get_theme() == "light"
    # "Neustart"-Simulation
    sm2 = SettingsManager()
    sm2.qs = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
    assert sm2.get_theme() == "light"
    # Ungueltiges Theme wird ignoriert
    sm2.set_theme("solarized")
    assert sm2.get_theme() == "light"


# --- U3: Kachelfarben-Persistenz ---------------------------------------------
def test_tile_color_defaults_match_previous(tmp_path):
    sm = _isolated_settings(tmp_path)
    assert sm.get_tile_color("main") == theme_mod.DEFAULT_TILE_MAIN
    assert sm.get_tile_color("version") == theme_mod.DEFAULT_TILE_VERSION


def test_tile_color_roundtrip_and_reset(tmp_path):
    sm = _isolated_settings(tmp_path)
    sm.set_tile_color("main", "#123456")
    sm.set_tile_color("version", "#abcdef")
    assert sm.get_tile_color("main") == "#123456"
    assert sm.get_tile_color("version") == "#ABCDEF"  # normalisiert auf Grossbuchstaben
    sm.reset_tile_colors()
    assert sm.get_tile_color("main") == theme_mod.DEFAULT_TILE_MAIN
    assert sm.get_tile_color("version") == theme_mod.DEFAULT_TILE_VERSION


# --- theme.py Farb-Helfer -----------------------------------------------------
def test_color_helpers():
    assert theme_mod.lighten("#000000", 1.0) == "#FFFFFF"
    assert theme_mod.darken("#FFFFFF", 1.0) == "#000000"
    assert theme_mod.lighten("#808080", 0.0) == "#808080"
    # Luminanz: Weiss hell, Schwarz dunkel
    assert theme_mod.relative_luminance("#FFFFFF") > 0.9
    assert theme_mod.relative_luminance("#000000") < 0.1
    # Kontrasttext: heller Text auf dunkel, dunkler auf hell
    assert theme_mod.contrast_text("#000000") == "#F5F5F5"
    assert theme_mod.contrast_text("#FFFFFF") == "#1A1A1A"
    # Normalisierung + Fallback
    assert theme_mod.normalize_hex("#abc", "#000000") == "#AABBCC"
    assert theme_mod.normalize_hex("kaputt", "#5D4037") == "#5D4037"


def test_derive_tile_palette_structure():
    pal = theme_mod.derive_tile_palette(theme_mod.DEFAULT_TILE_MAIN)
    for key in ("base", "bg_top", "bg_bottom", "border", "badge_bg",
                "badge_text", "text_col", "sub_col"):
        assert key in pal, f"Palette-Schluessel fehlt: {key}"
    # Farbverlauf: unten dunkler als oben
    assert theme_mod.relative_luminance(pal["bg_bottom"]) < \
        theme_mod.relative_luminance(pal["bg_top"])
    # Dunkle Basisfarbe -> heller Text (Lesbarkeit)
    assert pal["text_col"] == "#F5F5F5"


def test_tile_stylesheet_contains_chosen_color():
    pal = theme_mod.derive_tile_palette("#123456")
    css = theme_mod.tile_stylesheet(pal, None)
    assert "#123456" in css
    assert "QFrame#PromptTile" in css


def test_board_surface_color_theme_dependent():
    assert theme_mod.board_surface_color("dark") != theme_mod.board_surface_color("light")


# --- U2: apply_theme (braucht QApplication) ----------------------------------
def test_apply_theme_switches_palette(qapp):
    applied_light = theme_mod.apply_theme(qapp, "light")
    assert applied_light == "light"
    light_window = qapp.palette().color(QtGui.QPalette.Window).name()

    applied_dark = theme_mod.apply_theme(qapp, "dark")
    assert applied_dark == "dark"
    dark_window = qapp.palette().color(QtGui.QPalette.Window).name()

    assert light_window != dark_window
    # Hell muss wirklich heller sein als Dunkel
    assert theme_mod.relative_luminance(light_window) > theme_mod.relative_luminance(dark_window)

    # Ungueltiges Theme faellt auf dark zurueck
    assert theme_mod.apply_theme(qapp, "unbekannt") == "dark"


def test_apply_dark_theme_wrapper(qapp):
    import profiprompt
    assert profiprompt.apply_dark_theme(qapp) == "dark"


# --- U4: transparente Icons ---------------------------------------------------
def test_ui_icons_exist_and_have_alpha(qapp):
    for name in ("clipboard-light", "clipboard-dark",
                 "paperclip-light", "paperclip-dark"):
        path = os.path.join(ICON_DIR, name + ".png")
        assert os.path.exists(path), f"Icon fehlt: {name}.png"
        img = QtGui.QImage(path)
        assert not img.isNull(), f"Icon nicht ladbar: {name}.png"
        assert img.hasAlphaChannel(), f"Icon ohne Alphakanal: {name}.png"


def test_old_nontransparent_icons_removed():
    for old in ("clipboard.ico", "clipboard.jpg", "paperclip.ico", "paperclip.jpg"):
        assert not os.path.exists(os.path.join(ICON_DIR, old)), \
            f"Altes nicht-transparentes Icon noch vorhanden: {old}"


# --- Appearance-Dialog --------------------------------------------------------
def test_appearance_dialog_persists(qapp, tmp_path):
    from appearance_dialog import AppearanceDialog
    sm = _isolated_settings(tmp_path)
    dlg = AppearanceDialog(sm)
    # Theme auf Hell stellen
    idx = dlg.theme_combo.findData("light")
    dlg.theme_combo.setCurrentIndex(idx)
    # Kachelfarben setzen
    dlg._set_current_color("main", "#654321")
    dlg._set_current_color("version", "#0A0B0C")
    dlg.accept()
    assert sm.get_theme() == "light"
    assert sm.get_tile_color("main") == "#654321"
    assert sm.get_tile_color("version") == "#0A0B0C"


def test_appearance_dialog_reset(qapp, tmp_path):
    from appearance_dialog import AppearanceDialog
    sm = _isolated_settings(tmp_path)
    sm.set_tile_color("main", "#111111")
    dlg = AppearanceDialog(sm)
    dlg._reset_colors()
    dlg.accept()
    assert sm.get_tile_color("main") == theme_mod.DEFAULT_TILE_MAIN
    assert sm.get_tile_color("version") == theme_mod.DEFAULT_TILE_VERSION


# --- Regressionsschutz: keine hart kodierten Kachel-/Flaechenfarben mehr ------
def test_board_manager_no_hardcoded_surface():
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "board_manager.py"),
               encoding="utf-8").read()
    # #252525 (Flaeche) + die alte harte Kachel-Basisfarbe sind in theme.py gewandert
    assert "#252525" not in src, "board_manager: harte Flaechenfarbe #252525 noch vorhanden"
    assert "stop:0 #5D4037" not in src, "board_manager: harte Kachelfarbe noch vorhanden"


def test_dashboard_uses_transparent_png_icons():
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "dashboard.py"),
               encoding="utf-8").read()
    assert "paperclip.ico" not in src and "clipboard.ico" not in src, \
        "dashboard: alte .ico-Icons noch referenziert"
    assert "paperclip-" in src and "clipboard-" in src, \
        "dashboard: theme-passende PNG-Icons nicht referenziert"
