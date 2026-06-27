"""Regressionstests — ProfiPrompt Storage/Persistenz Bugsweep 2026-06-28.

Geprüfte Bugs:
  BUG-PS01 (KRIT): prompt_from_dict kracht auf fehlendem 'title'-Key (KeyError).
                   Inkonsistent mit version_from_dict (bereits in Sweep 19 gehärtet).
                   Repro: prompt_from_dict({"id": "x"}) → KeyError: 'title'.
  BUG-PS02 (MITTEL): load_prompts / load_boards fangen kein UnicodeDecodeError /
                      OSError → Windows cp1252-Datei oder gelöschte Datei crasht App.
                      Repro: prompts_file mit b'...\\xe9...' → UnicodeDecodeError ungefangen.
"""

import dataclasses
import importlib
import json
import os
import sys
from pathlib import Path

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models as _models_mod
import storage as _storage_mod


# ---------------------------------------------------------------------------
# BUG-PS01: prompt_from_dict — 'title' hart (d["title"]) statt .get()
# ---------------------------------------------------------------------------

def test_ps01_prompt_from_dict_missing_title_no_crash():
    """Fehlendes 'title'-Feld darf keinen KeyError auslösen (BUG-PS01).

    version_from_dict wurde in Sweep 19 auf .get() gehärtet; prompt_from_dict
    blieb dabei inkonsistent und kracht auf alten/fremden JSON-Exporten.
    """
    importlib.reload(_models_mod)
    p = _models_mod.prompt_from_dict({"id": "x"})
    assert p.id == "x"
    assert p.title == ""


def test_ps01_prompt_from_dict_unknown_key_no_crash():
    """Unbekannter Schlüssel darf nicht crashen (Forward-Compat, bereits OK)."""
    importlib.reload(_models_mod)
    p = _models_mod.prompt_from_dict({"id": "y", "title": "OK", "zukunftsfeld": 99})
    assert p.id == "y" and p.title == "OK"


def test_ps01_prompt_from_dict_missing_id_raises():
    """Fehlendes 'id' soll einen KeyError auslösen — id ist bewusst hart (kein Zombie)."""
    import pytest
    importlib.reload(_models_mod)
    with pytest.raises(KeyError):
        _models_mod.prompt_from_dict({"title": "Kein ID"})


def test_ps01_prompt_from_dict_preserves_all_known_fields():
    """Alle bekannten Felder bleiben beim Round-Trip erhalten."""
    importlib.reload(_models_mod)
    d = {
        "id": "abc",
        "title": "Mein Prompt",
        "purpose": "Testen",
        "text": "Hallo Welt mit Umlauten: äöü",
        "tags": ["tag1", "tag2"],
        "last_result": "Ergebnis",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2025-06-01T00:00:00+00:00",
        "versions": [],
    }
    p = _models_mod.prompt_from_dict(d)
    out = dataclasses.asdict(p)
    for k, val in d.items():
        assert out[k] == val, f"Feld '{k}' verloren/geändert: {out.get(k)!r} != {val!r}"


def test_ps01_prompt_from_dict_nested_versions_survive():
    """Verschachtelte Versionen werden korrekt deserialisiert."""
    importlib.reload(_models_mod)
    d = {
        "id": "p1",
        "title": "Prompt mit Versionen",
        "versions": [
            {
                "id": "v1", "prompt_id": "p1",
                "version_number": 1, "title": "v1-Titel", "text": "Inhalt"
            }
        ],
    }
    p = _models_mod.prompt_from_dict(d)
    assert len(p.versions) == 1
    assert p.versions[0].id == "v1"


def test_ps01_load_prompts_survives_prompt_without_title(tmp_path):
    """load_prompts() muss einen Prompt ohne 'title'-Feld laden können (BUG-PS01).

    Repro: JSON-Datei mit {"prompts": [{"id": "x"}]} → load_prompts crasht.
    """
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    # JSON mit fehlendem 'title' direkt in die Datei schreiben
    s.prompts_file.write_text(
        json.dumps({"prompts": [{"id": "ohne-titel"}]}),
        encoding="utf-8",
    )
    result = s.load_prompts()
    assert len(result) == 1
    assert result[0].id == "ohne-titel"
    assert result[0].title == ""


# ---------------------------------------------------------------------------
# BUG-PS02: load_prompts / load_boards — UnicodeDecodeError / OSError ungefangen
# ---------------------------------------------------------------------------

def test_ps02_load_prompts_survives_invalid_utf8(tmp_path):
    """Datei mit ungültigen UTF-8-Bytes (z.B. cp1252) darf nicht crashen (BUG-PS02).

    Repro: 0xe9 ist gültiges cp1252 (é), aber invalides Ein-Byte UTF-8 →
    read_text(encoding='utf-8') wirft UnicodeDecodeError — nicht gefangen.
    """
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    s.prompts_file.write_bytes(b'{"prompts": [{"id": "x", "title": "caf\xe9"}]}')
    result = s.load_prompts()
    assert isinstance(result, list)


def test_ps02_load_boards_survives_invalid_utf8(tmp_path):
    """boards.json mit ungültigen UTF-8-Bytes darf nicht crashen (BUG-PS02)."""
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    s.boards_file.write_bytes(b'{"boards": [{"id": "b1", "title": "caf\xe9"}]}')
    result = s.load_boards()
    assert isinstance(result, list)


def test_ps02_load_prompts_survives_deleted_file(tmp_path):
    """Gelöschte prompts.json (z.B. nach fehlgeschlagenem .tmp-Rename) darf
    nicht crashen (FileNotFoundError ist Unterklasse von OSError) (BUG-PS02)."""
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    s.prompts_file.unlink()
    result = s.load_prompts()
    assert isinstance(result, list)


def test_ps02_load_boards_survives_deleted_file(tmp_path):
    """Gelöschte boards.json darf nicht crashen (BUG-PS02)."""
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    s.boards_file.unlink()
    result = s.load_boards()
    assert isinstance(result, list)


def test_ps02_load_prompts_recovers_after_corrupt_file(tmp_path):
    """Nach Reparatur (upsert) einer korrupten Datei werden Prompts korrekt geladen."""
    importlib.reload(_models_mod)
    importlib.reload(_storage_mod)
    s = _storage_mod.Storage(tmp_path)
    # 1. Kaputte Datei → load_prompts muss leer zurückgeben (nicht crashen)
    s.prompts_file.write_bytes(b"\xff\xfe invalid utf-8")
    empty = s.load_prompts()
    assert empty == []
    # 2. Reparatur über upsert → Datei wird korrekt (neu) geschrieben
    p = _models_mod.Prompt(
        id=_models_mod.gen_id(),
        title="Wiederhergestellt",
        purpose="",
        text="",
        tags=[],
    )
    s.upsert_prompt(p)
    result = s.load_prompts()
    assert len(result) == 1
    assert result[0].title == "Wiederhergestellt"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
