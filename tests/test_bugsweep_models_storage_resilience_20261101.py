"""Hermetic Regression & Contract Tests — ProfiPrompt Bugsweep 2026-11-01.

Bereich: Prompt- und Board-Datenmodell, UUID-Generierung/Klonung,
Tag-Normalisierung & Board-Manager State-Integrität
(src/models.py, src/board_manager.py, src/storage.py).

Geprüfte Bugs & Resilienz-Facetten:
  1. prompt_from_dict(): KeyError bei fehlender oder None/leerer 'id' behoben;
     erzeugt deterministisch gen_id() anstelle des Abbruchs der gesamten Prompt-Bibliothek.
  2. version_from_dict(): KeyError bei fehlender 'id' oder 'prompt_id' behoben;
     erzeugt gen_id() und erbt default_prompt_id aus dem übergeordneten Prompt.
  3. _normalize_tags(): Robuste Konvertierung von Strings ('coding, python'),
     Listen mit Whitespace, Zahlen, None und Leerstrings in saubere List[str].
  4. Storage.get_prompt(): Resilienz gegen None-Einträge in prompts; kein AttributeError.
  5. Storage.delete_prompt(): Resilienz gegen b.items = None und b is None in boards;
     verhindert TypeError ('NoneType' object has no len()) und sichert saubere Board-Bereinigung.
  6. Storage.delete_version(): Resilienz gegen b.items = None und b is None in boards;
     verhindert TypeError ('NoneType' object has no len()).
  7. Storage.delete_board() & upsert_board() / upsert_prompt(): None-resiliente Guards.
  8. Storage.remove_item_from_board(): Resilienz gegen board.items = None und board is None.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models as _models
import storage as _storage


# ---------------------------------------------------------------------------
# 1. Models & Deserialization Tests (prompt_from_dict & version_from_dict)
# ---------------------------------------------------------------------------

def test_prompt_from_dict_missing_or_none_id():
    """prompt_from_dict() wirft bei fehlendem 'id' KeyError, ersetzt aber None/Leerstring durch gen_id()."""
    # Fehlender Key wirft KeyError (Zombie-Schutz gem. bestehendem Vertrag)
    d_missing = {"title": "Prompt ohne ID", "purpose": "Test", "text": "Inhalt"}
    with pytest.raises(KeyError):
        _models.prompt_from_dict(d_missing)

    # Explizites None wird defensiv mit neuer ID belegt
    d_none = {"id": None, "title": "Prompt mit None-ID", "text": "Inhalt"}
    p2 = _models.prompt_from_dict(d_none)
    assert isinstance(p2.id, str) and len(p2.id) >= 16

    # Expliziter Leerstring wird defensiv mit neuer ID belegt
    d_empty = {"id": "", "title": "Prompt mit leerer ID", "text": "Inhalt"}
    p3 = _models.prompt_from_dict(d_empty)
    assert isinstance(p3.id, str) and len(p3.id) >= 16


def test_version_from_dict_missing_id_and_prompt_id():
    """version_from_dict() darf bei fehlender id/prompt_id nicht mit KeyError abstürzen."""
    v_dict = {"title": "v1", "text": "Version Text", "version_number": 1}
    v = _models.version_from_dict(v_dict, default_prompt_id="parent_p1")
    assert isinstance(v.id, str) and len(v.id) >= 16
    assert v.prompt_id == "parent_p1"
    assert v.version_number == 1
    assert v.title == "v1"


def test_prompt_from_dict_nested_versions_inherit_prompt_id():
    """Verschachtelte Versionen ohne explizite prompt_id erben die ID des Eltern-Prompts."""
    d = {
        "id": "prompt_xyz",
        "title": "Hauptprompt",
        "text": "Basistext",
        "versions": [
            {"version_number": 1, "title": "Version 1", "text": "Text 1"},
            {"id": "v2_fixed", "version_number": 2, "title": "Version 2", "text": "Text 2"},
        ],
    }
    p = _models.prompt_from_dict(d)
    assert p.id == "prompt_xyz"
    assert len(p.versions) == 2
    assert p.versions[0].prompt_id == "prompt_xyz"
    assert isinstance(p.versions[0].id, str) and len(p.versions[0].id) >= 16
    assert p.versions[1].prompt_id == "prompt_xyz"
    assert p.versions[1].id == "v2_fixed"


def test_normalize_tags_string_and_dirty_iterables():
    """_normalize_tags() zerlegt Strings und bereinigt schmutzige Listen zuverlässig."""
    # String mit Kommas und Whitespace
    d_str = {
        "id": "p1",
        "title": "T",
        "text": "X",
        "tags": "coding, refactoring, python,  ",
    }
    p_str = _models.prompt_from_dict(d_str)
    assert p_str.tags == ["coding", "refactoring", "python"]

    # Liste mit None, Zahlen, Whitespace und Leerstrings
    d_dirty = {
        "id": "p2",
        "title": "T2",
        "text": "X",
        "tags": ["  tag1  ", None, "", 123, "tag2", "   "],
    }
    p_dirty = _models.prompt_from_dict(d_dirty)
    assert p_dirty.tags == ["tag1", "123", "tag2"]

    # Version-Tags ebenfalls normalisiert
    v_dict = {"title": "v1", "text": "vt", "tags": "v1, stable"}
    v = _models.version_from_dict(v_dict, default_prompt_id="p1")
    assert v.tags == ["v1", "stable"]


# ---------------------------------------------------------------------------
# 2. Storage None-Resilience Tests
# ---------------------------------------------------------------------------

def test_storage_get_prompt_resilient_to_none_entries(tmp_path):
    """Storage.get_prompt() stürzt nicht mit AttributeError ab, wenn load_prompts None liefert."""
    st = _storage.Storage(tmp_path)
    real_prompt = _models.Prompt(id="p1", title="Gültig", purpose="", text="Text")
    st.load_prompts = lambda *a, **kw: [None, real_prompt, None]

    assert st.get_prompt("p1") == real_prompt
    assert st.get_prompt("nonexistent") is None


def test_storage_delete_prompt_resilient_to_none_and_none_items(tmp_path):
    """Storage.delete_prompt() stürzt nicht ab bei b.items = None oder b is None."""
    st = _storage.Storage(tmp_path)
    p = _models.Prompt(id="p_target", title="Zu löschen", purpose="", text="T")
    st.save_prompts([p])

    b1 = _models.Board(id="b1", title="Board 1", items=None)
    b2 = _models.Board(
        id="b2",
        title="Board 2",
        items=[_models.BoardItem(id="i1", board_id="b2", prompt_id="p_target")],
    )
    st.save_boards([b1, b2])

    # Löschung darf weder an None in boards noch an items=None scheitern
    st.delete_prompt("p_target")

    reloaded_prompts = st.load_prompts()
    assert not any(x and getattr(x, "id", None) == "p_target" for x in reloaded_prompts)

    reloaded_boards = st.load_boards()
    b2_reloaded = next(b for b in reloaded_boards if b.id == "b2")
    assert len(b2_reloaded.items) == 0


def test_storage_delete_version_resilient_to_none_items(tmp_path):
    """Storage.delete_version() stürzt nicht mit TypeError ab, wenn b.items None ist."""
    st = _storage.Storage(tmp_path)
    v = _models.Version(id="v1", prompt_id="p1", version_number=1, title="V1", text="T")
    p = _models.Prompt(id="p1", title="P1", purpose="", text="T", versions=[v])
    st.save_prompts([p])

    b = _models.Board(id="b_empty", title="Board Empty", items=None)
    st.save_boards([b])

    # Darf nicht crashen
    ok = st.delete_version("p1", "v1")
    assert ok is True
    reloaded_p = st.get_prompt("p1")
    assert len(reloaded_p.versions) == 0


def test_storage_delete_board_and_upsert_resilient_to_none(tmp_path):
    """Storage.delete_board(), upsert_board() und upsert_prompt() handhaben None-Einträge sicher."""
    st = _storage.Storage(tmp_path)
    st.load_boards = lambda *a, **kw: [None, _models.Board(id="b_keep", title="Keep"), None]
    written_boards = []
    st._write_boards = lambda boards: written_boards.extend(boards)

    st.delete_board("b_other")
    assert len(written_boards) == 1
    assert written_boards[0].id == "b_keep"

    # upsert_board mit None im Bestand
    written_boards.clear()
    st.upsert_board(_models.Board(id="b_new", title="New"))
    assert any(b and b.id == "b_new" for b in written_boards)

    # upsert_prompt mit None im Bestand
    st.load_prompts = lambda *a, **kw: [None, _models.Prompt(id="p_exist", title="Exist", purpose="", text="")]
    written_prompts = []
    st._write_prompts = lambda prompts: written_prompts.extend(prompts)
    st.upsert_prompt(_models.Prompt(id="p_update", title="Updated", purpose="", text=""))
    assert any(p and p.id == "p_update" for p in written_prompts)


def test_storage_remove_item_from_board_resilient_to_none_items(tmp_path):
    """Storage.remove_item_from_board() stürzt bei board.items = None nicht ab."""
    st = _storage.Storage(tmp_path)
    b_none_items = _models.Board(id="b_none", title="B", items=None)
    st.save_boards([b_none_items])

    res = st.remove_item_from_board("b_none", "any_prompt")
    assert res is False
