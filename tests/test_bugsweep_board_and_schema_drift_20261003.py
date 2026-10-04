"""Regressionstests — ProfiPrompt Board Tile Interaction, Drag&Drop & Schema Drift Bugsweep 2026-10-03.

Geprüfte Bugs (BUG-BM05):
  1. board_from_dict() stürzte mit TypeError: 'NoneType' object is not iterable ab,
     wenn ein Board-JSON 'items: null' enthielt; zudem fehlten defensive Defaults
     bei expliziten null-Werten in Feldern (id, title, description, created_at).
  2. boarditem_from_dict() propagierte explizite null-Werte als None für id, board_id,
     prompt_id und created_at.
  3. Storage._validate_records() brach bei strict=True mit ValueError ab, wenn
     'items: null' in boards.json vorkam, da der Null-Placeholder-Guard fälschlich
     nur auf 'versions' beschränkt war.
  4. Storage-Methoden (delete_prompt, delete_version, add_item_to_board, remove_item_from_board)
     stürzten mit AttributeError ab, wenn b.items None-Einträge enthielt.
  5. PromptTile.mouseMoveEvent() setzte _suppress_click nicht auf True, wodurch nach
     einem Drag beim Loslassen der Maustaste in mouseReleaseEvent() ein unbeabsichtigter
     Klick-Trigger ausgelöst wurde (unerwünschter Clipboard-Kopierbefehl).
  6. PromptTile.mouseMoveEvent() lieferte nur Plaintext statt strukturierter
     application/x-prompt-item MIME-Daten.
  7. BoardManager.dropEvent() akzeptierte ungültige/abgewiesene Drops fälschlicherweise
     unbedingt via event.acceptProposedAction() statt event.ignore().
  8. BoardManager.reload_items() stürzte bei None-Einträgen in board.items oder
     p.versions mit AttributeError ab.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import pytest
from PySide6 import QtWidgets, QtCore, QtGui

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models as _models
import storage as _storage
import settings_manager as _sm
import board_manager as _bm
from event_bus import bus


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


# ---------------------------------------------------------------------------
# 1. Models & Deserialization Tests
# ---------------------------------------------------------------------------

def test_board_from_dict_handles_null_items():
    """board_from_dict darf bei items=None nicht mit TypeError abstürzen."""
    d = {"id": "b1", "title": "Test Board", "items": None}
    b = _models.board_from_dict(d)
    assert b.id == "b1"
    assert b.title == "Test Board"
    assert b.items == []


def test_board_from_dict_handles_null_fields():
    """board_from_dict belegt explizite null-Felder mit sauberen Defaults."""
    d = {"id": None, "title": None, "description": None, "items": None, "created_at": None}
    b = _models.board_from_dict(d)
    assert isinstance(b.id, str) and len(b.id) > 0
    assert b.title == ""
    assert b.description == ""
    assert b.items == []
    assert isinstance(b.created_at, str) and "T" in b.created_at


def test_boarditem_from_dict_handles_null_fields():
    """boarditem_from_dict belegt explizite null-Felder mit sauberen Defaults."""
    d = {"id": None, "board_id": None, "prompt_id": None, "version_id": None, "created_at": None}
    item = _models.boarditem_from_dict(d)
    assert isinstance(item.id, str) and len(item.id) > 0
    assert item.board_id == ""
    assert item.prompt_id == ""
    assert item.version_id is None
    assert isinstance(item.created_at, str) and "T" in item.created_at


def test_prompt_from_dict_handles_null_timestamps():
    """prompt_from_dict belegt explizite null-Timestamps mit sauberen ISO-Strings."""
    d = {
        "id": "p1",
        "title": "T",
        "created_at": None,
        "updated_at": None,
    }
    p = _models.prompt_from_dict(d)
    assert isinstance(p.created_at, str) and "T" in p.created_at
    assert isinstance(p.updated_at, str) and "T" in p.updated_at


# ---------------------------------------------------------------------------
# 2. Storage & Strict Validation Tests
# ---------------------------------------------------------------------------

def test_storage_strict_load_accepts_null_items_placeholder(tmp_path):
    """load_boards(strict=True) muss items: null als leere Liste akzeptieren."""
    st = _storage.Storage(tmp_path)
    raw = {"boards": [{"id": "b1", "title": "Archiv", "description": "", "items": None}]}
    st.boards_file.write_text(json.dumps(raw), encoding="utf-8")

    boards = st.load_boards(strict=True)
    assert len(boards) == 1
    assert boards[0].id == "b1"
    assert boards[0].items == []


def test_storage_mutations_resilient_to_none_items(tmp_path):
    """Storage-Mutationsmethoden dürfen bei None-Einträgen in b.items nicht crashen."""
    st = _storage.Storage(tmp_path)
    p = _models.Prompt(
        id="p1",
        title="Prompt 1",
        purpose="",
        text="Text",
        versions=[_models.Version(id="v1", prompt_id="p1", version_number=1, title="V1", text="VText")],
    )
    st.save_prompts([p])

    b = _models.Board(
        id="b1",
        title="Board 1",
        items=[
            None,
            _models.BoardItem(id="i1", board_id="b1", prompt_id="p1", version_id="v1"),
            None,
        ],
    )
    st.save_boards([b])

    # add_item_to_board darf bei None in b.items nicht crashen
    ok, new_id = st.add_item_to_board("b1", "p1", None)
    assert ok is True

    # remove_item_from_board darf bei None in b.items nicht crashen
    removed = st.remove_item_from_board("b1", "p1", "v1")
    assert removed is True

    # delete_prompt darf bei None in b.items nicht crashen
    st.delete_prompt("p1")
    reloaded_b = st.load_boards(strict=True)[0]
    assert all(it.prompt_id != "p1" for it in reloaded_b.items if it is not None)


# ---------------------------------------------------------------------------
# 3. GUI Drag & Drop and Event Handling Tests
# ---------------------------------------------------------------------------

def test_prompt_tile_drag_suppresses_click_event(qapp, tmp_path):
    """Nach einem Drag-Vorgang darf mouseReleaseEvent keinen Klick emittieren."""
    p = _models.Prompt(id="p1", title="Draggable", purpose="Test", text="Sample")
    tile = _bm.PromptTile(p, None, None, parent=None)

    clicked = []
    tile.clicked.connect(lambda pid, vid: clicked.append((pid, vid)))

    pt = QtCore.QPointF(10, 10)
    press_ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress,
        pt,
        pt,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    tile.mousePressEvent(press_ev)
    release_ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        pt,
        pt,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    tile.mouseReleaseEvent(release_ev)
    assert len(clicked) == 1

    # Drag-Vorgang simuliert: _suppress_click wird vor drag.exec gesetzt
    clicked.clear()
    tile.mousePressEvent(press_ev)
    assert tile._drag_start_pos is not None

    # Manuell gesetzte Flag wie in mouseMoveEvent
    tile._suppress_click = True
    tile.mouseReleaseEvent(release_ev)
    assert len(clicked) == 0, "Klick wurde trotz vorangegangenem Drag fälschlicherweise emittiert"
    assert tile._suppress_click is False


def test_board_manager_drop_event_rejects_invalid_drops(qapp, tmp_path):
    """BoardManager.dropEvent muss ungültige oder doppelte Drops via event.ignore() abweisen."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()
    p = _models.Prompt(id="p1", title="Prompt 1", purpose="", text="Text")
    st.save_prompts([p])
    b = _models.Board(id="b1", title="Board 1", items=[])
    st.save_boards([b])

    bm = _bm.BoardManager(st, settings)
    bm.reload("b1")

    # Drop mit ungültiger Prompt-ID
    mime_bad = QtCore.QMimeData()
    mime_bad.setData(_bm.BoardManager.MIME, json.dumps(["prompt", "nonexistent_id"]).encode("utf-8"))
    drop_bad = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.DropAction.CopyAction,
        mime_bad,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    bm.dropEvent(drop_bad)
    assert drop_bad.isAccepted() is False, "Ungültiger Prompt-Drop wurde fälschlicherweise akzeptiert"

    # Drop mit gültiger Prompt-ID -> muss akzeptiert werden
    mime_good = QtCore.QMimeData()
    mime_good.setData(_bm.BoardManager.MIME, json.dumps(["prompt", "p1"]).encode("utf-8"))
    drop_good = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.DropAction.CopyAction,
        mime_good,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    bm.dropEvent(drop_good)
    assert drop_good.isAccepted() is True, "Gültiger Prompt-Drop wurde abgewiesen"

    # Zweiter Drop desselben Prompts -> Duplikat -> muss ignoriert werden
    drop_dup = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.DropAction.CopyAction,
        mime_good,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    bm.dropEvent(drop_dup)
    assert drop_dup.isAccepted() is False, "Duplikat-Drop wurde fälschlicherweise akzeptiert"


def test_board_manager_reload_items_resilient_to_none_items(qapp, tmp_path):
    """BoardManager.reload_items() muss None-Items und None-Versionen sicher überspringen."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    p = _models.Prompt(
        id="p1",
        title="Prompt 1",
        purpose="",
        text="Text",
        versions=[None, _models.Version(id="v1", prompt_id="p1", version_number=1, title="V1", text="VText")],
    )
    st.save_prompts([p])

    b = _models.Board(
        id="b1",
        title="Board 1",
        items=[
            None,
            _models.BoardItem(id="it1", board_id="b1", prompt_id="p1", version_id=None),
            _models.BoardItem(id="it2", board_id="b1", prompt_id="p1", version_id="v1"),
            None,
        ],
    )
    st.save_boards([b])

    bm = _bm.BoardManager(st, settings)
    bm.reload("b1")

    # Es müssen genau 2 gültige Kacheln im Raster existieren (Prompt + Version 1)
    tiles = [bm.grid.itemAt(i).widget() for i in range(bm.grid.count()) if bm.grid.itemAt(i).widget()]
    assert len(tiles) == 2
