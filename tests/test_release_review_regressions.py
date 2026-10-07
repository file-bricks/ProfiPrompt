"""Release regressions: confirmation before mutation and durable writes."""
import errno
import pytest
from PySide6 import QtCore, QtGui, QtWidgets
import atomic_io
from storage import Storage
from settings_manager import SettingsManager
from models import Board, BoardItem, Prompt
from board_manager import BoardManager

@pytest.mark.parametrize("key", [QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace])
@pytest.mark.parametrize("answer", [QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.Yes])
def test_tile_removal_waits_for_confirmation(qapp, tmp_path, monkeypatch, key, answer):
    storage = Storage(tmp_path / "data")
    storage.save_prompts([Prompt(id="p1", title="Gruß", purpose="", text="äöü", tags=[], versions=[])])
    storage.save_boards([Board(id="b1", title="Board", items=[BoardItem(id="i1", board_id="b1", prompt_id="p1")])])
    settings = SettingsManager()
    settings.qs = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.IniFormat)
    manager = BoardManager(storage, settings)
    original = storage.boards_file.read_bytes()
    calls = []
    def question(*args):
        calls.append(len(storage.load_boards()[0].items))
        assert storage.boards_file.read_bytes() == original
        return answer
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", question)
    tile = manager._tiles[0]
    tile.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, QtCore.Qt.NoModifier))
    assert calls == [1]
    assert len(storage.load_boards()[0].items) == int(answer == QtWidgets.QMessageBox.StandardButton.No)
    if answer == QtWidgets.QMessageBox.StandardButton.No:
        assert storage.boards_file.read_bytes() == original
    manager.deleteLater()
    qapp.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

@pytest.mark.parametrize("error", [errno.EIO, errno.ENOSPC])
def test_fsync_failure_preserves_original(tmp_path, monkeypatch, error):
    target = tmp_path / "backup.json"
    target.write_bytes(b"previous durable data")
    replaced = []
    monkeypatch.setattr(atomic_io.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError(error, "disk failure")))
    monkeypatch.setattr(atomic_io.os, "replace", lambda *args: replaced.append(args))
    with pytest.raises(OSError):
        atomic_io.atomic_write_text(target, "unconfirmed replacement")
    assert target.read_bytes() == b"previous durable data"
    assert replaced == []
    assert list(tmp_path.glob(".*.tmp.*")) == []
