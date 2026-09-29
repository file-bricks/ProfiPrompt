"""tests/test_ui_accessibility.py — Barrierefreiheits- und UX-Vertragstests für ProfiPrompt.

Konformität: WCAG 2.1 AA / BITV 2.0
Geprüfte Aspekte:
- Tastaturbedienung & Navigation (PromptTree, PromptTile, MainWindow)
- Barrierefreier Hilfedialog mit F1 (ShortcutsDialog: Tabelle, Initialfokus, BITV-Hinweis)
- Menüleiste mit Mnemonics (&Datei, &Bearbeiten, &Ansicht, &Sprache, &Hilfe)
- Standard-Shortcuts (F1, Ctrl+F, Ctrl+N, Ctrl+B, Ctrl+1, Ctrl+2, Ctrl+Q, F5, Ctrl+,, Ctrl+Shift+C)
- Formular-Buddies (QLabel.setBuddy) & semantische Accessible Names/Descriptions
- Sichtbarer Tastatur-Fokusring (#PromptTile:focus)
- Tier-2 6-Sprachen-Parität für alle Barrierefreiheits- und Tastenkürzel-Texte
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets
import pytest

from models import Prompt, Version
from storage import Storage
from settings_manager import SettingsManager
from dashboard import DashboardWidget
from board_manager import BoardManager, PromptTile
from profiprompt import MainWindow, make_translator
from shortcuts_dialog import ShortcutsDialog
from theme import tile_stylesheet, derive_tile_palette, DEFAULT_TILE_MAIN


@pytest.fixture
def mock_storage(tmp_path):
    st = Storage(tmp_path)
    p = Prompt(
        id="p1",
        title="Test Prompt Alpha",
        purpose="Test Purpose for Accessibility",
        text="Hello Accessibility World!",
        tags=["a11y", "test"],
        created_at="2026-09-29T10:00:00",
        updated_at="2026-09-29T10:00:00",
    )
    st.save_prompts([p])
    return st


@pytest.fixture
def mock_settings(tmp_path):
    qs = QtCore.QSettings(str(tmp_path / "test_settings.ini"), QtCore.QSettings.Format.IniFormat)
    sm = SettingsManager()
    sm.qs = qs
    return sm


def test_shortcuts_dialog_structure_and_conformance_notice(qapp):
    """Prüft Struktur, Tabelle, BITV 2.0-Hinweis und Schließen-Button des ShortcutsDialog."""
    dlg = ShortcutsDialog()
    dlg.show()
    try:
        assert dlg.isModal() is True
        assert "Barrierefreiheit" in dlg.windowTitle()

        # BITV 2.0 / WCAG 2.1 AA Konformitätshinweis
        assert "BITV 2.0" in dlg._lbl_a11y.text()
        assert "WCAG 2.1 AA" in dlg._lbl_a11y.text()

        # Tabelle der Shortcuts
        table = dlg._table
        assert table.columnCount() == 3
        headers = [table.horizontalHeaderItem(i).text() for i in range(3)]
        assert headers == ["Tastenkombination", "Funktion / Aktion", "Bereich"]

        # Mindestens 20 registrierte Tastaturkürzel
        shortcuts = dlg.get_shortcuts_list()
        assert len(shortcuts) >= 20
        assert table.rowCount() == len(shortcuts)

        # Relevante Core-Shortcuts vorhanden
        keys = [s[0] for s in shortcuts]
        assert "F1" in keys
        assert "Ctrl+F" in keys
        assert "Ctrl+N" in keys
        assert "Ctrl+B" in keys
        assert "Ctrl+Q" in keys
        assert "F5" in keys

        # Schließen-Button mit Default- und Fokus-Einstellung
        assert dlg._btn_close.text() == "Schließen"
        assert dlg._btn_close.isDefault() is True
        assert dlg.focusWidget() == dlg._btn_close or dlg._btn_close.hasFocus()
    finally:
        dlg.close()


def test_shortcuts_dialog_multilingual_parity(qapp):
    """Verifiziert die Lokalisierung des ShortcutsDialog über alle 6 Sprachen."""
    langs = ["de", "en", "es", "zh", "ja", "ru"]
    for lang in langs:
        translator = make_translator(lang)
        dlg = ShortcutsDialog(translator=translator)
        try:
            assert dlg.windowTitle() != ""
            assert dlg._btn_close.text() != ""
            # Header in jeder Sprache vorhanden
            for c in range(3):
                hdr = dlg._table.horizontalHeaderItem(c).text()
                assert hdr != ""
            # Tabelleninhalte nicht leer
            for r in range(min(5, dlg._table.rowCount())):
                assert dlg._table.item(r, 0).text() != ""
                assert dlg._table.item(r, 1).text() != ""
                assert dlg._table.item(r, 2).text() != ""
        finally:
            dlg.close()


def test_dashboard_accessible_attributes_and_buddies(qapp, mock_storage, mock_settings):
    """Prüft Accessible Names, Descriptions und Label-Buddies im DashboardWidget."""
    dashboard = DashboardWidget(mock_storage, mock_settings)
    try:
        # PromptTree Accessibility
        tree = dashboard.tree
        assert tree.accessibleName() == "Prompt-Übersicht"
        assert "Tastaturbedienung" in tree.accessibleDescription()

        # Filter Widgets Accessibility
        assert dashboard.search_edit.accessibleName() == "Suchbegriff"
        assert "Volltextsuche" in dashboard.search_edit.accessibleDescription()

        assert dashboard.tag_combo.accessibleName() == "Tag-Filter"
        assert "Tags" in dashboard.tag_combo.accessibleDescription()

        assert dashboard.date_from.accessibleName() == "Startdatum"
        assert dashboard.date_to.accessibleName() == "Enddatum"
        assert dashboard.btn_clear.accessibleName() == "Filter zurücksetzen"

        # Label Buddies
        labels = dashboard.findChildren(QtWidgets.QLabel)
        buddy_map = {lbl.text(): lbl.buddy() for lbl in labels if lbl.buddy()}
        assert "Suche:" in buddy_map
        assert buddy_map["Suche:"] == dashboard.search_edit
        assert "Tag:" in buddy_map
        assert buddy_map["Tag:"] == dashboard.tag_combo
        assert "Von:" in buddy_map
        assert buddy_map["Von:"] == dashboard.date_from
        assert "Bis:" in buddy_map
        assert buddy_map["Bis:"] == dashboard.date_to
    finally:
        dashboard.close()


def test_prompt_tree_keyboard_navigation(qapp, mock_storage, mock_settings):
    """Testet Tastaturereignisse (Return, F2, F5, Ctrl+C, Entf) im PromptTree."""
    dashboard = DashboardWidget(mock_storage, mock_settings)
    tree = dashboard.tree
    try:
        assert tree.topLevelItemCount() > 0
        item = tree.topLevelItem(0)
        tree.setCurrentItem(item)

        # Tracking Flags
        events_called = []
        dashboard.edit_current_item = lambda it=None: events_called.append("edit")
        dashboard.delete_current_item = lambda it=None: events_called.append("delete")
        dashboard.copy_current_item_to_clipboard = lambda it=None: events_called.append("copy")
        dashboard.reload = lambda: events_called.append("reload")

        # 1. Return
        event_return = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Return, QtCore.Qt.KeyboardModifier.NoModifier)
        tree.keyPressEvent(event_return)
        assert "edit" in events_called

        # 2. F2
        events_called.clear()
        event_f2 = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_F2, QtCore.Qt.KeyboardModifier.NoModifier)
        tree.keyPressEvent(event_f2)
        assert "edit" in events_called

        # 3. Delete
        events_called.clear()
        event_del = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Delete, QtCore.Qt.KeyboardModifier.NoModifier)
        tree.keyPressEvent(event_del)
        assert "delete" in events_called

        # 4. Ctrl+C
        events_called.clear()
        event_copy = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
        tree.keyPressEvent(event_copy)
        assert "copy" in events_called

        # 5. F5
        events_called.clear()
        event_f5 = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_F5, QtCore.Qt.KeyboardModifier.NoModifier)
        tree.keyPressEvent(event_f5)
        assert "reload" in events_called
    finally:
        dashboard.close()


def test_board_manager_and_tile_accessibility(qapp, mock_storage, mock_settings):
    """Testet Accessible Names, Buddies, FocusPolicy und Tastatur auf BoardManager und PromptTile."""
    bm = BoardManager(mock_storage, mock_settings)
    try:
        # Label Buddy
        labels = bm.findChildren(QtWidgets.QLabel)
        buddy_map = {lbl.text(): lbl.buddy() for lbl in labels if lbl.buddy()}
        assert "Board:" in buddy_map
        assert buddy_map["Board:"] == bm.board_combo

        # Accessibility Attributes
        assert bm.board_combo.accessibleName() == "Aktives Board"
        assert bm.btn_new_board.accessibleName() == "Neues Board"
        assert bm.btn_del_board.accessibleName() == "Board löschen"
        assert bm.btn_font.accessibleName() == "Kachelschriftart wählen"
        assert bm.scroll.accessibleName() == "Board-Arbeitsfläche"
        assert bm.container.accessibleName() == "Kachel-Raster"

        # PromptTile Accessibility
        prompt = mock_storage.load_prompts()[0]
        tile = PromptTile(prompt, None, None, parent=bm.container)
        try:
            assert tile.focusPolicy() == QtCore.Qt.FocusPolicy.StrongFocus
            assert f"Prompt-Kachel: {prompt.title}" in tile.accessibleName()
            assert "PROMPT" in tile.accessibleDescription()

            # Tile Keypresses
            tile_events = []
            tile.doubleClicked.connect(lambda p_id, v_id: tile_events.append("double_click"))
            tile.clicked.connect(lambda p_id, v_id: tile_events.append("click"))

            # Return -> doubleClicked
            ev_ret = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Return, QtCore.Qt.KeyboardModifier.NoModifier)
            tile.keyPressEvent(ev_ret)
            assert "double_click" in tile_events

            # Space -> clicked
            tile_events.clear()
            ev_spc = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Space, QtCore.Qt.KeyboardModifier.NoModifier)
            tile.keyPressEvent(ev_spc)
            assert "click" in tile_events
        finally:
            tile.close()
    finally:
        bm.close()


def test_mainwindow_menubar_mnemonics_and_shortcuts(qapp, mock_storage, mock_settings):
    """Testet Menüleisten-Mnemonics (Alt+D, Alt+B, ...) und globale Shortcuts in MainWindow."""
    win = MainWindow(mock_storage, mock_settings)
    try:
        menubar = win.menuBar()
        actions = menubar.actions()
        menu_titles = [a.text() for a in actions]

        # Mnemonics prüfen
        assert any("&Datei" in t for t in menu_titles)
        assert any("&Bearbeiten" in t for t in menu_titles)
        assert any("&Ansicht" in t for t in menu_titles)
        assert any("&Hilfe" in t for t in menu_titles)

        # Alle Aktionen in Untermenüs auf Shortcuts prüfen
        sub_actions = win.findChildren(QtGui.QAction)
        shortcut_map = {a.text(): a.shortcut().toString() for a in sub_actions if not a.shortcut().isEmpty()}

        assert shortcut_map.get("Beenden") == "Ctrl+Q"
        assert shortcut_map.get("Neuen Prompt erstellen") == "Ctrl+N"
        assert shortcut_map.get("Kopier-Einstellungen …") == "Ctrl+Shift+C"
        assert shortcut_map.get("Darstellung …") == "Ctrl+,"
        assert shortcut_map.get("Boards anzeigen/ausblenden") == "Ctrl+B"
        assert shortcut_map.get("Suche fokussieren") == "Ctrl+F"
        assert shortcut_map.get("Prompt-Liste fokussieren") == "Ctrl+1"
        assert shortcut_map.get("Board-Bereich fokussieren") == "Ctrl+2"
        assert shortcut_map.get("Aktualisieren") == "F5"
        assert shortcut_map.get("Tastaturkürzel & Hilfe") == "F1"

        # StatusTips vorhanden
        status_tips = [a.statusTip() for a in sub_actions if a.statusTip()]
        assert len(status_tips) >= 10
    finally:
        win.close()


def test_mainwindow_navigation_and_shortcuts_dialog(qapp, mock_storage, mock_settings, monkeypatch):
    """Testet Fokus-Navigation (Suche, Prompt-Liste, Board) und Shortcuts-Dialog-Auslösung."""
    win = MainWindow(mock_storage, mock_settings)
    win.show()
    try:
        # Focus Search
        win.focus_search()
        assert win.focusWidget() == win.dashboard.search_edit or win.dashboard.search_edit.hasFocus()

        # Focus Prompt List
        win.focus_prompt_list()
        assert win.focusWidget() == win.dashboard.tree or win.dashboard.tree.hasFocus()

        # Focus Board
        win.focus_board()
        assert win.focusWidget() == win.boardManager.board_combo or win.boardManager.board_combo.hasFocus()

        # ShortcutsDialog open_shortcuts_dialog Bypass
        dialog_opened = []
        monkeypatch.setattr(ShortcutsDialog, "exec", lambda self: dialog_opened.append(True))
        dlg = win.open_shortcuts_dialog()
        assert len(dialog_opened) == 1
        assert isinstance(dlg, ShortcutsDialog)
    finally:
        win.close()


def test_theme_focus_ring_styling():
    """Testet, dass tile_stylesheet einen barrierefreien Tastatur-Fokusring enthält."""
    palette = derive_tile_palette(DEFAULT_TILE_MAIN)
    qss = tile_stylesheet(palette, "Segoe UI")
    assert "QFrame#PromptTile:focus" in qss
    assert "border: 2px solid" in qss
