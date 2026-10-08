# -*- coding: utf-8 -*-
"""Regressionstests 2026-10-06: Sprachwechsel live, Kachel-Transfer zwischen Boards, Kachelfarben.

Gepruefte Punkte:
  I18N-01 (HOCH): Sprachwechsel auf Englisch wurde nur fuer die Menueleiste uebernommen.
                  Tabellenkoepfe (Prompt-Baum, Shortcut-Tabelle), Filterleiste, Board-Leiste,
                  Kacheln, Kontextmenues und Dialoge blieben deutsch.
  I18N-02 (HOCH): Dashboard-Kontextmenue verglich Aktionen per deutschem Text
                  (chosen.text().startswith("Prompt exportieren")) -> nach Uebersetzung
                  waeren alle Exporte stumm wirkungslos gewesen.
  I18N-03 (MITTEL): Laufzeit-Lookups durften fehlende Keys mit leeren Uebersetzungen in die
                  gebuendelte translations.json schreiben (Paritaets-Bruch).
  I18N-04: Jeder im Code verwendete tr()-Key existiert in allen 6 Sprachen mit gleichen
           Platzhaltern.
  BOARD-01 (Regression): Kacheln liessen sich nicht mehr auf ein anderes Board senden
           (verschieben) oder dorthin duplizieren.
  TILE-01 (Feature): individuelle Kachelfarbe pro Board-Kachel (persistiert, validiert).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from PySide6 import QtCore, QtWidgets

import i18n
from models import Board, BoardItem, Prompt, Version, boarditem_from_dict, board_to_dict
from storage import Storage
from settings_manager import SettingsManager
from board_manager import BoardManager
from dashboard import DashboardWidget
from shortcuts_dialog import ShortcutsDialog
from profiprompt import MainWindow
from translator import TranslationSystem

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "en", "es", "zh", "ja", "ru")


# --------------------------------------------------------------------------- fixtures
@pytest.fixture
def settings(tmp_path):
    sm = SettingsManager()
    sm.qs = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.Format.IniFormat)
    return sm


@pytest.fixture
def storage(tmp_path):
    st = Storage(tmp_path / "data")
    p1 = Prompt(id="p1", title="Alpha", purpose="Zweck A", text="Text A", tags=["x"],
                versions=[Version(id="v1", prompt_id="p1", version_number=1, title="Kurz", text="VT")])
    p2 = Prompt(id="p2", title="Beta", purpose="Zweck B", text="Text B")
    st.save_prompts([p1, p2])
    st.save_boards([
        Board(id="b1", title="Eins", items=[
            BoardItem(id="i1", board_id="b1", prompt_id="p1"),
            BoardItem(id="i2", board_id="b1", prompt_id="p1", version_id="v1", color="#2F5D9E"),
        ]),
        Board(id="b2", title="Zwei", items=[]),
    ])
    return st


def _tiles(bm: BoardManager):
    return [bm.grid.itemAt(i).widget() for i in range(bm.grid.count()) if bm.grid.itemAt(i).widget()]


def _board(st: Storage, bid: str) -> Board:
    return next(b for b in st.load_boards() if b.id == bid)


# --------------------------------------------------------------------------- I18N
def test_i18n_01_language_switch_translates_tables_boards_and_filters(qapp, storage, settings):
    win = MainWindow(storage, settings)
    try:
        tree = win.dashboard.tree
        de_headers = [tree.headerItem().text(c) for c in range(5)]
        assert de_headers == ["Titel", "Zweck", "Tags", "Erstellt", "Aktualisiert"]

        win.change_language("en")

        en_headers = [tree.headerItem().text(c) for c in range(5)]
        assert en_headers == ["Title", "Purpose", "Tags", "Created", "Updated"]
        assert win.dashboard.lbl_search.text() == "Search:"
        assert win.dashboard.btn_clear.text() == "Reset Filter"
        assert win.dashboard.tag_combo.itemText(0) == "All tags"
        assert tree.accessibleName() == "Prompt Overview"

        bm = win.boardManager
        assert bm.lbl_board.text() == "Board:"
        assert bm.btn_new_board.text() == "New"
        assert bm.btn_del_board.text() == "Delete"
        assert bm.btn_ren_board.text() == "Rename"
        assert bm.btn_font.text() == "Font"
        assert win.boardDock.windowTitle() == "Boards"
        assert win.statusBar().accessibleName() == "Status bar"

        # Kacheln wurden mit englischen Accessible-Names neu aufgebaut
        for tile in _tiles(bm):
            assert tile.accessibleName().startswith("Prompt tile:")

        # Kopier-Buttons in den Baumzeilen (Unterzeilen = Versionen)
        top = tree.topLevelItem(0)
        btn = tree.itemWidget(top, 6)
        assert btn.toolTip().startswith("Copy prompt:")

        # Menueleiste ebenfalls englisch
        titles = [a.text() for a in win.menuBar().actions()]
        assert "&File" in titles and "&Edit" in titles

        # Zurueck auf Deutsch
        win.change_language("de")
        assert [tree.headerItem().text(c) for c in range(5)] == de_headers
        assert bm.btn_new_board.text() == "Neu"
    finally:
        win.close()


@pytest.mark.parametrize("lang", LANGS)
def test_i18n_01_dashboard_headers_in_every_language(qapp, storage, settings, lang):
    i18n.init(lang)
    dash = DashboardWidget(storage, settings)
    try:
        headers = [dash.tree.headerItem().text(c) for c in range(5)]
        assert all(headers)
        if lang != "de":
            assert headers[0] != "Titel"
    finally:
        dash.close()


def test_i18n_01_shortcut_table_key_names_translated(qapp):
    i18n.init("en")
    dlg = ShortcutsDialog()
    try:
        keys = [dlg._table.item(r, 0).text() for r in range(dlg._table.rowCount())]
        assert "Enter / Return" in keys
        assert "Space" in keys
        assert not any(k in keys for k in ("Leertaste", "Entf / Backspace"))
        scopes = {dlg._table.item(r, 2).text() for r in range(dlg._table.rowCount())}
        assert "Prompt List" in scopes
    finally:
        dlg.close()


def test_i18n_02_dashboard_context_menu_not_dispatched_by_text():
    src = (ROOT / "src" / "dashboard.py").read_text(encoding="utf-8")
    assert "chosen.text()" not in src, "Kontextmenue-Aktionen duerfen nicht per (uebersetztem) Text verglichen werden"


def test_i18n_03_runtime_lookup_never_writes_translation_file(tmp_path):
    (tmp_path / "locales").mkdir()
    f = tmp_path / "locales" / "translations.json"
    f.write_text("{}", encoding="utf-8")
    tr_obj = TranslationSystem("en", app_dir=tmp_path, auto_register=False)
    assert tr_obj.t("Völlig unbekannter Schlüssel") == "Völlig unbekannter Schlüssel"
    assert f.read_text(encoding="utf-8") == "{}"
    # Shared App-Translator ist ebenfalls ohne Auto-Registrierung
    assert i18n.get_translator().auto_register is False


def _collect_tr_keys():
    keys = {}
    for f in sorted((ROOT / "src").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name in ("tr", "_t") and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                keys.setdefault(node.args[0].value, f.name)
    # nicht-literale Keys (Tabellen/Presets/Modi)
    from dashboard import PromptTree
    for k in PromptTree.HEADER_KEYS:
        keys.setdefault(k, "dashboard.py")
    for name, _ in BoardManager.TILE_COLOR_PRESETS:
        keys.setdefault(name, "board_manager.py")
    for k in ("Nur Titel", "Nur Prompt-Text", "Nur Ergebnis", "Alles"):
        keys.setdefault(k, "copy_settings_dialog.py")
    for combo, action, scope in ShortcutsDialog.SHORTCUTS:
        keys.setdefault(action, "shortcuts_dialog.py")
        keys.setdefault(scope, "shortcuts_dialog.py")
    return keys


def test_i18n_04_every_ui_key_translated_in_all_languages():
    data = json.loads((ROOT / "locales" / "translations.json").read_text(encoding="utf-8"))
    keys = _collect_tr_keys()
    assert len(keys) > 150
    missing = sorted(k for k in keys if k not in data)
    assert not missing, f"Fehlende Uebersetzungs-Keys: {missing}"
    for key in keys:
        placeholders = set(re.findall(r"\{(\w+)\}", key))
        for lang in LANGS:
            value = data[key][lang]
            assert value.strip(), f"{key!r} leer in {lang}"
            assert set(re.findall(r"\{(\w+)\}", value)) == placeholders, (key, lang, value)


# --------------------------------------------------------------------------- Storage transfer
def test_board_01_copy_item_keeps_source_and_color(storage):
    ok, reason = storage.copy_item_to_board("b1", "b2", "p1", "v1")
    assert (ok, reason) == (True, "ok")
    assert len(_board(storage, "b1").items) == 2
    dst = _board(storage, "b2").items
    assert len(dst) == 1 and dst[0].version_id == "v1" and dst[0].board_id == "b2"
    assert dst[0].color == "#2F5D9E"
    # zweites Duplizieren wird abgewiesen
    assert storage.copy_item_to_board("b1", "b2", "p1", "v1") == (False, "duplicate")


def test_board_01_move_item_removes_from_source(storage):
    ok, reason = storage.move_item_to_board("b1", "b2", "p1", None)
    assert ok and reason == "ok"
    assert [(i.prompt_id, i.version_id) for i in _board(storage, "b1").items] == [("p1", "v1")]
    assert [(i.prompt_id, i.version_id) for i in _board(storage, "b2").items] == [("p1", None)]


def test_board_01_transfer_rejects_invalid_targets(storage):
    assert storage.move_item_to_board("b1", "b1", "p1") == (False, "same_board")
    assert storage.move_item_to_board("b1", "nope", "p1") == (False, "target_missing")
    assert storage.move_item_to_board("nope", "b2", "p1") == (False, "source_missing")
    assert storage.move_item_to_board("b1", "b2", "p2") == (False, "source_missing")
    # Nichts wurde veraendert
    assert len(_board(storage, "b1").items) == 2 and not _board(storage, "b2").items


def test_board_01_move_duplicate_keeps_source(storage):
    storage.add_item_to_board("b2", "p1", None)
    assert storage.move_item_to_board("b1", "b2", "p1", None) == (False, "duplicate")
    assert len(_board(storage, "b1").items) == 2


def test_board_rename(storage):
    assert storage.rename_board("b2", "  Neu  ") is True
    assert _board(storage, "b2").title == "Neu"
    assert storage.rename_board("b2", "   ") is False
    assert storage.rename_board("missing", "X") is False


# --------------------------------------------------------------------------- Tile colors
def test_tile_01_set_and_reset_item_color(storage):
    assert storage.set_item_color("b1", "p1", None, "#b23a48") is True
    item = next(i for i in _board(storage, "b1").items if i.version_id is None)
    assert item.color == "#B23A48"
    assert storage.set_item_color("b1", "p1", None, None) is True
    item = next(i for i in _board(storage, "b1").items if i.version_id is None)
    assert item.color is None
    # Ungueltige Farbe wird abgewiesen und nichts geschrieben
    assert storage.set_item_color("b1", "p1", None, "red; background: url(x)") is False
    assert storage.set_item_color("b1", "p2", None, "#000000") is False


@pytest.mark.parametrize("raw,expected", [
    ("#abcdef", "#ABCDEF"), ("#ABCDEF", "#ABCDEF"), ("abcdef", None), ("#abc", None),
    ("#12345G", None), (123, None), (None, None), ("#000000; color:red", None),
])
def test_tile_01_color_schema_validation(raw, expected):
    item = boarditem_from_dict({"id": "i", "board_id": "b", "prompt_id": "p", "color": raw})
    assert item.color == expected


def test_tile_01_color_roundtrips_and_old_json_without_color(storage):
    d = board_to_dict(_board(storage, "b1"))
    assert any(i.get("color") == "#2F5D9E" for i in d["items"])
    old = boarditem_from_dict({"id": "i", "board_id": "b", "prompt_id": "p"})
    assert old.color is None


# --------------------------------------------------------------------------- BoardManager UI
def _menu_titles(menu: QtWidgets.QMenu):
    return [a.text() for a in menu.actions() if not a.isSeparator()]


def test_board_01_tile_context_menu_offers_move_and_duplicate(qapp, storage, settings):
    bm = BoardManager(storage, settings)
    try:
        bm.board_combo.setCurrentIndex(bm.board_combo.findData("b1"))
        tile = _tiles(bm)[0]
        menu = bm.build_tile_context_menu(tile)
        titles = _menu_titles(menu)
        assert "Auf Board verschieben" in titles
        assert "Auf Board duplizieren" in titles
        menu_actions = menu.actions()
        sub_action = next(a for a in menu_actions if a.text() == "Auf Board verschieben")
        sub = sub_action.menu()
        sub_titles = _menu_titles(sub)
        assert "Zwei" in sub_titles and "Eins" not in sub_titles
        assert "Neues Board …" in sub_titles
    finally:
        bm.close()


def test_board_01_transfer_tile_move_and_copy(qapp, storage, settings):
    bm = BoardManager(storage, settings)
    try:
        bm.board_combo.setCurrentIndex(bm.board_combo.findData("b1"))
        version_tile = next(t for t in _tiles(bm) if t.version is not None)
        assert bm.transfer_tile(version_tile, "b2", move=False) is True
        qapp.processEvents()
        assert len(_board(storage, "b1").items) == 2
        assert len(_board(storage, "b2").items) == 1

        main_tile = next(t for t in _tiles(bm) if t.version is None)
        assert bm.transfer_tile(main_tile, "b2", move=True) is True
        assert [(i.prompt_id, i.version_id) for i in _board(storage, "b1").items] == [("p1", "v1")]
        assert len(_board(storage, "b2").items) == 2
    finally:
        bm.close()


def test_board_01_transfer_tile_to_new_board(qapp, storage, settings, monkeypatch):
    bm = BoardManager(storage, settings)
    try:
        bm.board_combo.setCurrentIndex(bm.board_combo.findData("b1"))
        monkeypatch.setattr(QtWidgets.QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("Drei", True)))
        tile = next(t for t in _tiles(bm) if t.version is None)
        assert bm.transfer_tile_to_new_board(tile, move=False) is True
        new_board = next(b for b in storage.load_boards() if b.title == "Drei")
        assert [(i.prompt_id, i.version_id) for i in new_board.items] == [("p1", None)]
    finally:
        bm.close()


def test_tile_01_set_tile_color_rerenders_with_color(qapp, storage, settings):
    bm = BoardManager(storage, settings)
    try:
        bm.board_combo.setCurrentIndex(bm.board_combo.findData("b1"))
        tile = next(t for t in _tiles(bm) if t.version is None)
        assert tile.color is None
        assert bm.set_tile_color(tile, "#3E7D4F") is True
        qapp.processEvents()
        tile = next(t for t in _tiles(bm) if t.version is None)
        assert tile.color == "#3E7D4F"
        assert "#3E7D4F" in tile.styleSheet()
        # Version-Kachel mit gespeicherter Farbe
        vtile = next(t for t in _tiles(bm) if t.version is not None)
        assert vtile.color == "#2F5D9E" and "#2F5D9E" in vtile.styleSheet()
        # Zuruecksetzen auf Standardfarbe
        assert bm.set_tile_color(tile, None) is True
        tile = next(t for t in _tiles(bm) if t.version is None)
        assert tile.color is None
    finally:
        bm.close()


def test_board_rename_via_ui(qapp, storage, settings, monkeypatch):
    bm = BoardManager(storage, settings)
    try:
        bm.board_combo.setCurrentIndex(bm.board_combo.findData("b2"))
        monkeypatch.setattr(QtWidgets.QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("Zwei neu", True)))
        bm.rename_current_board()
        qapp.processEvents()
        assert _board(storage, "b2").title == "Zwei neu"
        assert bm.board_combo.currentData() == "b2"
        assert bm.board_combo.currentText() == "Zwei neu"
    finally:
        bm.close()


# --------------------------------------------------------------------------- Responsive grid
def test_grid_columns_follow_viewport_width_without_overlap(qapp, qtbot, tmp_path, settings):
    st = Storage(tmp_path / "grid")
    st.save_prompts([Prompt(id=f"p{i}", title=f"T{i}", purpose="", text="x") for i in range(5)])
    st.save_boards([Board(id="b", title="B", items=[
        BoardItem(id=f"i{i}", board_id="b", prompt_id=f"p{i}") for i in range(5)])])
    bm = BoardManager(st, settings)
    try:
        def settled(columns):
            visible = [tile for tile in _tiles(bm) if tile.isVisible()]
            rects = [tile.geometry() for tile in visible]
            return bm._layout_cols == columns and len(visible) == 5 and all(
                not a.intersects(b) for i, a in enumerate(rects) for b in rects[i + 1:]
            )

        # Top-level minimum width depends on theme, font and native platform.
        # Test the grid's actual viewport and wait for Qt's queued layout work.
        bm.scroll.setFixedWidth(340)
        bm.resize(340, 600)
        bm.show()
        qapp.processEvents()
        bm.reload_items()
        qtbot.waitUntil(lambda: settled(1), timeout=1000)
        bm.scroll.setFixedWidth(1000)
        bm.resize(1000, 600)
        qtbot.waitUntil(lambda: settled(3), timeout=1000)
        visible = [t for t in _tiles(bm) if t.isVisible()]
        assert len(visible) == 5
        rects = [t.geometry() for t in visible]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert not a.intersects(b), "Kacheln duerfen sich nicht ueberlappen"
        # Nach Reload sind alte Kacheln sofort unsichtbar (kein Geister-Overlap)
        old = _tiles(bm)
        bm.reload_items()
        assert all(not t.isVisible() for t in old)
    finally:
        bm.close()
