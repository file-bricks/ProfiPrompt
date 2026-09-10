"""Regressionstests — ProfiPrompt Clipboard & Library-Export Bugsweep 2026-09-10.

Geprüfte Bugs:
  BUG-CE01 (HOCH): ClipboardManager.build_copy_text() stürzt mit TypeError ab,
                   wenn title, text oder tags None enthalten oder tags nicht-Strings sind.
                   In CopyMode.ALL wurde zudem literal "None" ausgegeben.
                   build_copy_text(None, None) stürzte mit AttributeError ab.
  BUG-CE02 (HOCH): _collect_tags() in library_export.py stürzt mit TypeError ab,
                   wenn prompt.tags oder version.tags None sind oder nicht-Strings enthalten.
                   write_library_export() stürzt mit FileNotFoundError ab, wenn Zielordner
                   noch nicht existieren.
  BUG-CE03 (MITTEL): prompt_from_dict() setzte tags=None und stürzte bei versions=None
                     (JSON null) ab, inkonsistent zu version_from_dict().
"""

import importlib
import json
import os
import sys
from pathlib import Path
import pytest

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models as _models
import clipboard_manager as _cm
import library_export as _lib_exp
from storage import Storage


class MockSettings:
    def __init__(self, mode=_models.CopyMode.TEXT, include_meta=False):
        self.mode = mode
        self.include_meta = include_meta

    def get_copy_mode(self):
        return self.mode

    def get_include_metadata(self):
        return self.include_meta


# ---------------------------------------------------------------------------
# BUG-CE01: ClipboardManager.build_copy_text Robustheit
# ---------------------------------------------------------------------------

def test_ce01_clipboard_title_none_no_type_error():
    """CopyMode.TITLE mit title=None darf keinen TypeError werfen."""
    clip = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.TITLE))
    p = _models.Prompt(id="p1", title=None, purpose="", text="Hallo")
    out = clip.build_copy_text(p)
    assert out == ""


def test_ce01_clipboard_text_none_no_type_error():
    """CopyMode.TEXT mit text=None darf keinen TypeError werfen."""
    clip = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.TEXT))
    p = _models.Prompt(id="p2", title="Titel", purpose="", text=None)
    out = clip.build_copy_text(p)
    assert out == ""


def test_ce01_clipboard_version_none_fields_no_crash():
    """Version mit title=None/text=None darf in keinem Modus crashen."""
    p = _models.Prompt(id="p1", title="Haupttitel", purpose="", text="Haupttext")
    v = _models.Version(id="v1", prompt_id="p1", version_number=1, title=None, text=None)

    clip_title = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.TITLE))
    assert clip_title.build_copy_text(p, v) == ""

    clip_text = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.TEXT))
    assert clip_text.build_copy_text(p, v) == ""


def test_ce01_clipboard_all_mode_no_literal_none():
    """CopyMode.ALL mit None-Feldern darf kein wörtliches 'None' ausgeben."""
    clip = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.ALL))
    p = _models.Prompt(id="p1", title=None, purpose="", text="Text ohne Titel")
    out = clip.build_copy_text(p)
    assert "None" not in out
    assert out == "Text ohne Titel"


def test_ce01_clipboard_tags_with_none_and_non_str():
    """Metadaten mit None oder nicht-String Tags dürfen nicht abstürzen."""
    clip = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.TEXT, include_meta=True))
    p = _models.Prompt(id="p1", title="T", purpose="", text="Inhalt", tags=[None, "gueltig", 123, ""])
    out = clip.build_copy_text(p)
    assert "gueltig" in out
    assert "123" in out
    assert "None" not in out


def test_ce01_clipboard_none_prompts_safe():
    """Aufruf von build_copy_text mit None darf keinen AttributeError werfen."""
    clip = _cm.ClipboardManager(MockSettings(mode=_models.CopyMode.ALL))
    assert clip.build_copy_text(None, None) == ""

    v = _models.Version(id="v1", prompt_id="p1", version_number=1, title="V-Titel", text="V-Text")
    out = clip.build_copy_text(None, v)
    assert "V-Titel" in out
    assert "V-Text" in out


# ---------------------------------------------------------------------------
# BUG-CE02: library_export Tags & Pfaderstellung
# ---------------------------------------------------------------------------

def test_ce02_collect_tags_handles_none_and_non_str():
    """_collect_tags() muss None-Tags und numerische Tags sauber verarbeiten."""
    p1 = _models.Prompt(id="p1", title="P1", purpose="", text="", tags=None)
    p2 = _models.Prompt(
        id="p2", title="P2", purpose="", text="", tags=["Beta", 99],
        versions=[_models.Version(id="v1", prompt_id="p2", version_number=1, title="", text="", tags=None)]
    )
    tags = _lib_exp._collect_tags([p1, p2])
    assert tags == ["99", "Beta"]


def test_ce02_write_library_export_creates_parent_directories(tmp_path):
    """write_library_export muss übergeordnete Verzeichnisse bei Bedarf anlegen."""
    store = Storage(tmp_path / "data")
    p = _models.Prompt(id="p1", title="Test", purpose="P", text="Txt")
    store.upsert_prompt(p)

    target_file = tmp_path / "exports" / "2026" / "deep_folder" / "library.json"
    assert not target_file.parent.exists()

    payload = _lib_exp.write_library_export(store, target_file)
    assert target_file.is_file()
    assert payload["stats"]["prompt_count"] == 1


# ---------------------------------------------------------------------------
# BUG-CE03: models.prompt_from_dict Robustheit
# ---------------------------------------------------------------------------

def test_ce03_prompt_from_dict_null_tags_and_versions():
    """prompt_from_dict darf bei tags=None oder versions=None nicht versagen."""
    d = {
        "id": "p_null",
        "title": "Null-Test",
        "tags": None,
        "versions": None,
    }
    p = _models.prompt_from_dict(d)
    assert p.id == "p_null"
    assert p.tags == []
    assert p.versions == []
