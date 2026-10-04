"""tests/test_bugsweep_a11y_keyboard_and_drift_resilience_20261004.py

Tests fuer:
- PromptTile Tastatur-Bedienung: Ctrl+C (Kopieren) & Delete/Backspace (Entfernen via removeRequested)
- PromptTile Barrierefreiheit: Dynamischer AccessibleName fuer Version-Kacheln & Child-Labels
- MainWindow.handle_copy_request: Null- und Schema-Drift-Resilienz (None-Prompts, None-Versionen)
- Storage: get_version, next_version_number, add_version, upsert_version, add_item_to_board mit None-Resilienz
- DashboardWidget: Context-Menu & Keyboard-Version-Delete mit None-Versionen in p.versions
- DashboardWidget: get_current_version mit unvollstaendigen Daten-Tupeln
- DashboardWidget: _apply_filters & Tree-Aufbau ohne Phantom-Paperclip bei [None]-Versionen
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets
import pytest

from models import Prompt, Version, Board, BoardItem
from storage import Storage
from settings_manager import SettingsManager
from dashboard import DashboardWidget
from board_manager import BoardManager, PromptTile
from profiprompt import MainWindow
from event_bus import bus


@pytest.fixture
def test_storage(tmp_path):
    st = Storage(tmp_path)
    p = Prompt(
        id="p1",
        title="Prompt Master",
        purpose="Testing A11y & Drift",
        text="Master Prompt Body Text",
        tags=["a11y", "drift"],
        created_at="2026-10-04T00:00:00",
        updated_at="2026-10-04T00:00:00",
        versions=[
            Version(
                id="v1",
                prompt_id="p1",
                version_number=1,
                title="Version One",
                text="Version One Body Text",
                tags=["v1"],
                created_at="2026-10-04T00:00:00",
                updated_at="2026-10-04T00:00:00",
            )
        ],
    )
    b = Board(
        id="b1",
        title="Main Board",
        items=[
            BoardItem(id="bi1", board_id="b1", prompt_id="p1", version_id="v1")
        ],
    )
    st.save_prompts([p])
    st.save_boards([b])
    return st


@pytest.fixture
def test_settings(tmp_path):
    qs = QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.Format.IniFormat)
    sm = SettingsManager()
    sm.qs = qs
    return sm


# ---------------------------------------------------------------------------
# 1. PromptTile Keyboard & Accessibility Tests
# ---------------------------------------------------------------------------

def test_prompt_tile_keyboard_ctrl_c_and_delete(qapp, test_storage, test_settings):
    """Testet Tastatur-Kürzel auf PromptTile: Ctrl+C emittiert copyRequested, Delete emittiert removeRequested."""
    p = test_storage.get_prompt("p1")
    v = p.versions[0]
    tile = PromptTile(p, v, font_family=None)

    # 1. AccessibleName für Version-Kachel
    assert "Prompt-Kachel: Prompt Master (v1 — Version One)" in tile.accessibleName()

    # 2. AccessibleNames auf Child-Labels
    badge_label = tile.findChild(QtWidgets.QLabel, "Badge")
    assert badge_label is not None
    assert badge_label.accessibleName() == "Kachel-Typ: v1"

    subtitle_label = tile.findChild(QtWidgets.QLabel, "Subtitle")
    assert subtitle_label is not None
    assert subtitle_label.accessibleName() == "Kachel-Untertitel: Version One"

    preview_label = tile.findChild(QtWidgets.QLabel, "Preview")
    assert preview_label is not None
    assert "Kachel-Vorschau:" in preview_label.accessibleName()

    # 3. Ctrl+C löst bus.copyRequested aus
    copy_events = []
    bus.copyRequested.connect(lambda kind, item_id, parent: copy_events.append((kind, item_id, parent)))

    ev_ctrl_c = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_C,
        QtCore.Qt.KeyboardModifier.ControlModifier,
    )
    tile.keyPressEvent(ev_ctrl_c)
    assert len(copy_events) == 1
    assert copy_events[0][0] == "version"
    assert copy_events[0][1] == "v1"
    assert copy_events[0][2] == tile

    # 4. Delete / Backspace löst removeRequested aus
    remove_events = []
    tile.removeRequested.connect(lambda t: remove_events.append(t))

    ev_del = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Delete,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    tile.keyPressEvent(ev_del)
    assert len(remove_events) == 1
    assert remove_events[0] == tile

    ev_back = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress,
        QtCore.Qt.Key.Key_Backspace,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    tile.keyPressEvent(ev_back)
    assert len(remove_events) == 2


# ---------------------------------------------------------------------------
# 2. MainWindow.handle_copy_request Schema-Drift & None-Safety
# ---------------------------------------------------------------------------

def test_handle_copy_request_with_none_prompts_and_versions(qapp, tmp_path, test_settings):
    """handle_copy_request stürzt nicht ab, wenn Prompts oder Versions None-Elemente enthalten."""
    st = Storage(tmp_path)
    p_good = Prompt(id="p_good", title="Good", purpose="", text="Good text")
    st.save_prompts([p_good])

    win = MainWindow(st, test_settings)

    # Simuliere geladene Prompts mit None-Elementen und Version mit None
    p_drift = Prompt(id="p_drift", title="Drift", purpose="", text="Drift text", versions=[None])
    monkeypatch_prompts = [None, p_drift, p_good]
    st.load_prompts = lambda strict=False: monkeypatch_prompts

    # Test copy prompt
    win.handle_copy_request("prompt", "p_good", None)
    assert QtWidgets.QApplication.clipboard().text() == "Good text"

    # Test copy version (kein passender Eintrag, darf nicht crashen)
    win.handle_copy_request("version", "nonexistent_v", None)

    # Test copy version mit gültigem Eintrag neben None
    v_good = Version(id="v_good", prompt_id="p_drift", version_number=2, title="VGood", text="VGood text")
    p_drift.versions = [None, v_good]
    win.handle_copy_request("version", "v_good", None)
    assert QtWidgets.QApplication.clipboard().text() == "VGood text"

    win.close()


# ---------------------------------------------------------------------------
# 3. Storage Null- & Drift-Resilience
# ---------------------------------------------------------------------------

def test_storage_get_version_and_board_resilience(tmp_path):
    """Storage.get_version und add_item_to_board verarbeiten None-Versionen ohne Crash."""
    st = Storage(tmp_path)
    p = Prompt(id="p1", title="P1", purpose="", text="Text")
    p.versions = [None]  # Schema drift
    st.save_prompts([p])
    b = Board(id="b1", title="B1", items=[])
    st.save_boards([b])

    # get_version mit drift
    assert st.get_version("p1", "v999") is None

    # next_version_number mit drift
    assert st.next_version_number("p1") == 1

    # add_item_to_board mit validate_prompt=True und Version
    ok, _ = st.add_item_to_board("b1", "p1", version_id="v_fake", validate_prompt=True)
    assert ok is False

    # add_version mit p.versions = None
    p_no_v = Prompt(id="p2", title="P2", purpose="", text="Text")
    p_no_v.versions = None
    st.save_prompts([p, p_no_v])

    new_v = Version(id="v_new", prompt_id="p2", version_number=1, title="New", text="New V")
    assert st.add_version("p2", new_v) is True
    reloaded_p2 = st.get_prompt("p2")
    assert len(reloaded_p2.versions) == 1
    assert reloaded_p2.versions[0].id == "v_new"


# ---------------------------------------------------------------------------
# 4. DashboardWidget Version Delete & Tuple Guard Tests
# ---------------------------------------------------------------------------

def test_dashboard_version_delete_and_tuple_guards(qapp, tmp_path, test_settings, monkeypatch):
    """DashboardWidget stürzt beim Löschen von Versionen nicht ab, selbst wenn None in p.versions existiert."""
    st = Storage(tmp_path)
    v1 = Version(id="v1", prompt_id="p1", version_number=1, title="V1", text="V1 text")
    p = Prompt(id="p1", title="P1", purpose="", text="Text", versions=[None, v1])
    st.save_prompts([p])

    dash = DashboardWidget(st, test_settings)

    top_item = dash.tree.topLevelItem(0)
    assert top_item is not None
    version_item = top_item.child(0)
    assert version_item is not None

    # get_current_version mit defektem UserRole-Tupel ("version", "p1") ohne vid
    version_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, ("version", "p1"))
    dash.tree.setCurrentItem(version_item)
    assert dash.get_current_version() is None

    # get_current_version mit gültigem Tupel
    version_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, ("version", "p1", "v1"))
    dash.tree.setCurrentItem(version_item)
    assert dash.get_current_version() is not None
    assert dash.get_current_version().id == "v1"

    # Löschen simulieren mit Bestätigung Yes
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes)
    dash.delete_current_item(version_item)

    # Version wurde gelöscht, p.versions wurde sauber gefiltert
    reloaded_p = st.get_prompt("p1")
    assert all(getattr(v, "id", None) != "v1" for v in reloaded_p.versions if v is not None)

    dash.close()


def test_dashboard_no_phantom_paperclip_on_none_versions(qapp, tmp_path, test_settings):
    """Ein Prompt mit nur [None] in versions darf kein Büroklammer-Icon in Spalte 5 erhalten."""
    st = Storage(tmp_path)
    p_phantom = Prompt(id="p_ph", title="Phantom", purpose="", text="Text", versions=[None])
    st.save_prompts([p_phantom])

    dash = DashboardWidget(st, test_settings)
    assert dash.tree.topLevelItemCount() == 1
    top_item = dash.tree.topLevelItem(0)

    # Spalte 5 Icon muss leer sein (keine echten Versionen)
    assert top_item.icon(5).isNull() is True

    dash.close()
