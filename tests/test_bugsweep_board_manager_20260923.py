"""Regressionstests — ProfiPrompt BoardManager & Board Lifecycle Bugsweep 2026-09-23.

Gepruefte Bugs:
  BUG-BM01 (HOCH): In BoardManager.reload_items() wird ein BoardItem mit ungueltiger/geloeschter
                   version_id faelschlicherweise als Haupt-Prompt-Kachel gerendert (PromptTile(p, None)),
                   was zu irrefuehrender Anzeige, fehlerhaftem Kopieren und Unloeschbarkeit fuehrt.
  BUG-BM02 (MITTEL): BoardManager.create_board() behaelt in reload() die alte Board-Auswahl bei;
                     das neu erstellte Board wird nicht aktiviert.
  BUG-BM03 (MITTEL): Wenn alle Boards geloescht werden, bleibt btn_del_board faelschlicherweise aktiv.
  BUG-BM04 (HOCH): In dropEvent() faellt ungueltige vid stillschweigend auf vid=None zurueck und
                   fuegt den Hauptprompt hinzu; zudem fehlt bei dropEvent() und _remove_item_from_board()
                   das bus.boardsChanged Signal.
  BUG-ST01 (HOCH): Storage.next_version_number() stuerzt mit TypeError ab, wenn version_number
                   einer Version None ist oder Versionen None enthalten.
"""

import os
import sys
import json
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


def test_bm01_ghost_tile_not_rendered_when_version_deleted(qapp, tmp_path):
    """BUG-BM01: Verwaiste Version-Items duerfen nicht als Hauptprompt-Kacheln gerendert werden."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    p1 = _models.Prompt(id="p1", title="Hauptprompt", purpose="Test", text="Prompt Text")
    st.upsert_prompt(p1)

    # Board enthaelt ein Item mit nicht-existierender Version "v-deleted"
    b1 = _models.Board(id="b1", title="Board 1", items=[
        _models.BoardItem(id="item-orphan", board_id="b1", prompt_id="p1", version_id="v-deleted")
    ])
    st.upsert_board(b1)

    bm = _bm.BoardManager(st, settings)
    # Es darf keine Geister-Kachel als "PROMPT" gerendert werden
    tiles = [bm.grid.itemAt(i).widget() for i in range(bm.grid.count()) if bm.grid.itemAt(i).widget()]
    assert len(tiles) == 0, "Verwaiste Versions-Kachel wurde faelschlicherweise als Prompt gerendert"


def test_bm02_create_board_selects_newly_created_board(qapp, tmp_path, monkeypatch):
    """BUG-BM02: Nach create_board() muss das neue Board im Dropdown ausgewaehlt sein."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    b1 = _models.Board(id="b1", title="Board 1", items=[])
    b2 = _models.Board(id="b2", title="Board 2", items=[])
    st.upsert_board(b1)
    st.upsert_board(b2)

    bm = _bm.BoardManager(st, settings)
    idx1 = bm.board_combo.findData("b1")
    bm.board_combo.setCurrentIndex(idx1)
    assert bm.current_board().id == "b1"

    # Simuliere QInputDialog: Name eingeben und bestaetigen
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText",
        lambda *args, **kwargs: ("Neues Projektboard", True)
    )

    bm.create_board()

    # Das aktuell selektierte Board muss jetzt das neu erstellte sein
    cur = bm.current_board()
    assert cur is not None
    assert cur.title == "Neues Projektboard"
    assert bm.board_combo.currentText() == "Neues Projektboard"


def test_bm03_delete_button_disabled_when_zero_boards(qapp, tmp_path):
    """BUG-BM03: btn_del_board muss deaktiviert sein, wenn keine Boards existieren."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    b1 = _models.Board(id="b1", title="Board 1", items=[])
    st.upsert_board(b1)

    bm = _bm.BoardManager(st, settings)
    assert bm.btn_del_board.isEnabled() is True

    # Loesche das einzige Board
    st.delete_board("b1")
    bus.boardsChanged.emit()

    assert bm.board_combo.count() == 0
    assert bm.current_board() is None
    assert bm.btn_del_board.isEnabled() is False


def test_bm04_drop_event_rejects_nonexistent_version(qapp, tmp_path):
    """BUG-BM04: Drop einer ungueltigen Version darf nicht stillschweigend den Hauptprompt anlegen."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    p1 = _models.Prompt(id="p1", title="Hauptprompt", purpose="Test", text="Prompt Text")
    st.upsert_prompt(p1)

    b1 = _models.Board(id="b1", title="Board 1", items=[])
    st.upsert_board(b1)

    bm = _bm.BoardManager(st, settings)

    # Erzeuge MimeData mit ungueltiger version_id
    mime = QtCore.QMimeData()
    payload = json.dumps(["version", "p1", "v-nonexistent"]).encode("utf-8")
    mime.setData(_bm.BoardManager.MIME, payload)

    # Simuliere Drop-Event
    event = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.DropAction.CopyAction,
        mime,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )

    bm.dropEvent(event)

    # Board darf kein Item enthalten
    boards = st.load_boards()
    assert len(boards[0].items) == 0, "Ungueltiger Versions-Drop hat faelschlicherweise Item angelegt"


def test_bm04_remove_item_emits_boards_changed(qapp, tmp_path):
    """BUG-BM04: _remove_item_from_board() muss bus.boardsChanged emittieren."""
    st = _storage.Storage(tmp_path)
    settings = _sm.SettingsManager()

    p1 = _models.Prompt(id="p1", title="Hauptprompt", purpose="Test", text="Prompt Text")
    st.upsert_prompt(p1)

    b1 = _models.Board(id="b1", title="Board 1", items=[
        _models.BoardItem(id="item-1", board_id="b1", prompt_id="p1", version_id=None)
    ])
    st.upsert_board(b1)

    bm = _bm.BoardManager(st, settings)
    tiles = [bm.grid.itemAt(i).widget() for i in range(bm.grid.count()) if bm.grid.itemAt(i).widget()]
    assert len(tiles) == 1

    signal_received = []
    bus.boardsChanged.connect(lambda: signal_received.append(True))

    try:
        bm._remove_item_from_board(tiles[0])
        assert len(signal_received) > 0, "_remove_item_from_board() hat boardsChanged nicht emittiert"
    finally:
        pass


def test_st01_next_version_number_handles_none_version_number(tmp_path):
    """BUG-ST01: next_version_number() muss robust gegen None/null VersionNumbers sein."""
    st = _storage.Storage(tmp_path)
    v1 = _models.Version(
        id="v1", prompt_id="p1", version_number=None,
        title="Version ohne Nummer", text="Text"
    )
    v2 = _models.Version(
        id="v2", prompt_id="p1", version_number=3,
        title="Version 3", text="Text"
    )
    p1 = _models.Prompt(
        id="p1", title="Hauptprompt", purpose="Test", text="Text",
        versions=[v1, v2]
    )
    st.upsert_prompt(p1)

    # Darf nicht mit TypeError abstuerzen, sondern muss max(3, 0) + 1 = 4 liefern
    next_num = st.next_version_number("p1")
    assert next_num == 4
