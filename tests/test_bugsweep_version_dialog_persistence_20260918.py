"""Regressionstests — ProfiPrompt VersionDialog & Storage Persistence Bugsweep 2026-09-18.

Gepruefte Bugs:
  BUG-VD01 (KRIT): In VersionDialog._on_save_update() werden Aenderungen an einer bestehenden
                   Version nicht in storage persistiert, weil VersionDialog mit get_prompt() und
                   get_version() zwei unterschiedliche Instanzen erhaelt und Version-Edits in-place
                   an dem losgeloesten Objekt vorgenommen wurden. storage.upsert_prompt(self.prompt)
                   schrieb den Prompt mit dem unmodifizierten Altzustand zurueck; Edits gingen verloren.
  BUG-VD02 (HOCH): Storage hatte keine dedizierte upsert_version() und delete_version() Methode.
  BUG-VD03 (MITTEL): Storage.delete_prompt() und delete_version() entfernten verwaiste BoardItems
                     nicht aus boards.json, wodurch tote Referenzen akkumulierten.
  BUG-VD04 (MITTEL): Storage.add_item_to_board() validierte nicht die Existenz von prompt_id
                     bzw. version_id, wodurch ungueltige Drops persistiert wurden.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest
from PySide6 import QtWidgets

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models as _models
import storage as _storage
import prompt_dialog as _prompt_dialog

@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


def test_vd01_version_dialog_save_persists_version_updates_to_storage(qapp, tmp_path):
    """BUG-VD01: Aenderungen in VersionDialog muessen in Storage gespeichert werden."""
    st = _storage.Storage(tmp_path)
    pid = _models.gen_id()
    vid = _models.gen_id()
    v1 = _models.Version(
        id=vid, prompt_id=pid, version_number=1,
        title="Alte Version", text="Alter Text", tags=["alt"], result="Altes Ergebnis"
    )
    p = _models.Prompt(
        id=pid, title="Hauptprompt", purpose="Zweck", text="Prompttext",
        tags=["p"], versions=[v1]
    )
    st.upsert_prompt(p)

    # Simuliere UI-Flow wie in Dashboard / BoardManager:
    p_inst = st.get_prompt(pid)
    v_inst = st.get_version(pid, vid)

    dlg = _prompt_dialog.VersionDialog(st, p_inst, v_inst)
    dlg.title_edit.setText("Neuer Versionstitel")
    dlg.text_edit.setPlainText("Neuer Versionstext")
    dlg.tags_edit.setText("neu, frisch")
    dlg.result_edit.setPlainText("Neues Ergebnis")

    dlg._on_save_update()

    # Nach dem Speichern muss die Version in storage aktualisiert sein:
    reloaded_p = st.get_prompt(pid)
    assert len(reloaded_p.versions) == 1
    reloaded_v = reloaded_p.versions[0]
    assert reloaded_v.title == "Neuer Versionstitel"
    assert reloaded_v.text == "Neuer Versionstext"
    assert reloaded_v.tags == ["neu", "frisch"]
    assert reloaded_v.result == "Neues Ergebnis"


def test_vd02_storage_upsert_version(tmp_path):
    """BUG-VD02: Storage.upsert_version aktualisiert gezielt die Version und Prompt.updated_at."""
    st = _storage.Storage(tmp_path)
    pid = _models.gen_id()
    vid = _models.gen_id()
    v = _models.Version(id=vid, prompt_id=pid, version_number=1, title="V1", text="T1")
    p = _models.Prompt(id=pid, title="P", purpose="", text="", versions=[v])
    st.upsert_prompt(p)

    v_mod = _models.Version(id=vid, prompt_id=pid, version_number=1, title="V1-Updated", text="T1-Updated")
    ok = st.upsert_version(pid, v_mod)
    assert ok is True

    loaded = st.get_version(pid, vid)
    assert loaded is not None
    assert loaded.title == "V1-Updated"
    assert loaded.text == "T1-Updated"


def test_vd03_storage_delete_version_cleans_boards(tmp_path):
    """BUG-VD03: Storage.delete_version loescht Version und bereinigt Board-Referenzen."""
    st = _storage.Storage(tmp_path)
    pid = _models.gen_id()
    vid = _models.gen_id()
    v = _models.Version(id=vid, prompt_id=pid, version_number=1, title="V1", text="T1")
    p = _models.Prompt(id=pid, title="P", purpose="", text="", versions=[v])
    st.upsert_prompt(p)

    bid = _models.gen_id()
    board = _models.Board(id=bid, title="TestBoard")
    st.upsert_board(board)
    ok, item_id = st.add_item_to_board(bid, pid, vid)
    assert ok is True
    assert len(st.load_boards()[0].items) == 1

    del_ok = st.delete_version(pid, vid)
    assert del_ok is True
    assert st.get_version(pid, vid) is None

    # BoardItem muss aus dem Board bereinigt worden sein:
    boards = st.load_boards()
    assert len(boards[0].items) == 0


def test_vd03_storage_delete_prompt_cleans_boards(tmp_path):
    """BUG-VD03: Storage.delete_prompt loescht Prompt und alle Board-Referenzen."""
    st = _storage.Storage(tmp_path)
    pid = _models.gen_id()
    p = _models.Prompt(id=pid, title="P", purpose="", text="")
    st.upsert_prompt(p)

    bid = _models.gen_id()
    board = _models.Board(id=bid, title="TestBoard")
    st.upsert_board(board)
    ok, _ = st.add_item_to_board(bid, pid, None)
    assert ok is True
    assert len(st.load_boards()[0].items) == 1

    st.delete_prompt(pid)
    assert st.get_prompt(pid) is None

    boards = st.load_boards()
    assert len(boards[0].items) == 0


def test_vd04_storage_add_item_to_board_validation(tmp_path):
    """BUG-VD04: add_item_to_board verweigert leere/Whitespace-IDs und validiert bei Bedarf."""
    st = _storage.Storage(tmp_path)
    pid = _models.gen_id()
    p = _models.Prompt(id=pid, title="P", purpose="", text="")
    st.upsert_prompt(p)

    bid = _models.gen_id()
    board = _models.Board(id=bid, title="TestBoard")
    st.upsert_board(board)

    # 1. Leere oder reine Whitespace-IDs werden abgewiesen:
    ok_empty, _ = st.add_item_to_board(bid, "", None)
    assert ok_empty is False
    ok_ws, _ = st.add_item_to_board(bid, "   ", None)
    assert ok_ws is False

    # 2. Mit validate_prompt=True werden nicht existierende Prompts/Versionen abgewiesen:
    ok_nonexistent, _ = st.add_item_to_board(bid, "nonexistent-pid", None, validate_prompt=True)
    assert ok_nonexistent is False

    ok_bad_ver, _ = st.add_item_to_board(bid, pid, "nonexistent-vid", validate_prompt=True)
    assert ok_bad_ver is False

    # 3. Existierender Prompt:
    ok, item_id = st.add_item_to_board(bid, pid, None, validate_prompt=True)
    assert ok is True
    assert item_id is not None


def test_vd05_board_manager_dropevent_rejects_ghost_and_whitespace_prompts(qapp, tmp_path):
    """BUG-VD04/BM: BoardManager.dropEvent ignoriert ungültige/unbekannte Prompts und Whitespace."""
    import settings_manager as _settings_manager
    import board_manager as _board_manager
    from PySide6 import QtCore, QtGui

    st = _storage.Storage(tmp_path)
    sm = _settings_manager.SettingsManager()
    bm = _board_manager.BoardManager(st, sm)

    # Erstelle ein Board
    bid = _models.gen_id()
    b = _models.Board(id=bid, title="TestBoard")
    st.upsert_board(b)
    bm.reload()

    # Drop ungültigen Text (z.B. Whitespace)
    md = QtCore.QMimeData()
    md.setText("   |   ")
    event = QtGui.QDropEvent(QtCore.QPointF(10, 10), QtCore.Qt.DropAction.CopyAction, md, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
    bm.dropEvent(event)
    assert len(st.load_boards()[0].items) == 0

    # Drop nicht existierenden Prompt
    md2 = QtCore.QMimeData()
    md2.setText("nonexistent_id|")
    event2 = QtGui.QDropEvent(QtCore.QPointF(10, 10), QtCore.Qt.DropAction.CopyAction, md2, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
    bm.dropEvent(event2)
    assert len(st.load_boards()[0].items) == 0
