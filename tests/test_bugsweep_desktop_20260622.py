"""Regressionstests — ProfiPrompt Desktop-Bugsweep 2026-06-22 (Loop-Lauf 19, erste Durchfuehrung).

models = echte Round-Trip-Tests (importierbar, reines Python) — fangen stillen Feldverlust,
den eine statische Assertion NICHT erkennen wuerde. GUI-Guards (dashboard/board_manager/
profiprompt) = statische Quelltext-Assertions. Red-on-revert: PP_SRC -> PRE-Backup-src.

  models BUG-01 (KRIT): Version(**v)/BoardItem(**i) -> feldweise from_dict (schema-drift).
  board_manager BUG-04 (KRIT): dropEvent json.loads/arr[1] ungeschuetzt -> try/except.
  dashboard BUG-01 (KRIT): mimeData items[0] ohne Leer-Check.
  dashboard BUG-02 (KRIT): open_context_menu data-None Unpack.
  dashboard BUG-07/03: p/v-None + rest[0]-Guard.
  profiprompt BUG-06: doppelte bus-reload-Connections entfernt.
  clipboard BUG-05/06: clipboard()/widget None-Guards.
"""
import os
import sys
from pathlib import Path

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

DASH = (_SRC / "dashboard.py").read_text(encoding="utf-8")
BM = (_SRC / "board_manager.py").read_text(encoding="utf-8")
PP = (_SRC / "profiprompt.py").read_text(encoding="utf-8")


def has(src, n):
    return n in src


# --- models: ECHTE Round-Trip-Tests (BUG-01) ---
def test_version_roundtrip_preserves_all_fields():
    import importlib, models
    importlib.reload(models)
    d = {
        "id": "vid1", "prompt_id": "pid1", "version_number": 7,
        "title": "T", "text": "X", "result": "R",
        "tags": ["a", "b"], "created_at": "2020-01-01T00:00:00+00:00",
        "updated_at": "2021-02-02T00:00:00+00:00",
    }
    v = models.version_from_dict(d)
    out = models.version_to_dict(v) if hasattr(models, "version_to_dict") else __import__("dataclasses").asdict(v)
    for k, val in d.items():
        assert out[k] == val, f"Feld {k} ging verloren/veraendert: {out.get(k)!r} != {val!r}"


def test_version_from_dict_survives_unknown_and_missing_key():
    import importlib, models
    importlib.reload(models)
    # Extra-Key (Forward-Compat) + fehlendes optionales Feld -> darf NICHT werfen (Version(**v) tat es).
    v = models.version_from_dict({"id": "i", "prompt_id": "p", "future_field": 1})
    assert v.id == "i" and v.prompt_id == "p"
    assert v.tags == [] and v.title == ""


def test_boarditem_roundtrip_and_unknown_key():
    import importlib, models
    importlib.reload(models)
    d = {"id": "b1", "board_id": "bd1", "prompt_id": "p1",
         "version_id": "v1", "created_at": "2020-01-01T00:00:00+00:00"}
    bi = models.boarditem_from_dict(d)
    out = __import__("dataclasses").asdict(bi)
    for k, val in d.items():
        assert out[k] == val, f"BoardItem-Feld {k} verloren: {out.get(k)!r}"
    # Extra-Key darf nicht crashen
    bi2 = models.boarditem_from_dict({"id": "b", "board_id": "x", "prompt_id": "p", "junk": 9})
    assert bi2.version_id is None


# --- clipboard: echter None-Guard-Test (BUG-05/06) ---
def test_clipboard_no_qapp_no_crash():
    import importlib, clipboard_manager, settings_manager
    importlib.reload(clipboard_manager)
    # ohne QApplication darf copy_to_clipboard nicht crashen (clipboard()/widget None)
    cm = clipboard_manager.ClipboardManager.__new__(clipboard_manager.ClipboardManager)
    cm.copy_to_clipboard(None, "hallo")  # darf nicht werfen


# --- GUI: statische Assertions ---
def test_dash_mimedata_empty_guard():
    assert has(DASH, "if not items:"), "mimeData Leer-Guard fehlt"


def test_dash_context_data_none_guard():
    assert has(DASH, "data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)") and \
        has(DASH, "if p is None or (kind == \"version\" and v is None):"), "context p/v-None-Guard fehlt"


def test_bm_dropevent_try_except():
    assert has(BM, "except (json.JSONDecodeError, IndexError, TypeError, KeyError, UnicodeDecodeError):"), \
        "dropEvent try/except fehlt"


def test_profiprompt_no_double_reload_connect():
    assert not has(PP, "bus.promptsChanged.connect(self.dashboard.reload)"), "doppelte promptsChanged-Connection noch da"
    assert not has(PP, "bus.boardsChanged.connect(self.boardManager.reload)"), "doppelte boardsChanged-Connection noch da"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
