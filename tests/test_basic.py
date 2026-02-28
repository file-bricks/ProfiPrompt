# -*- coding: utf-8 -*-
"""Grundlegende Tests fuer ProfiPrompt."""

import sys
import os
import json
import tempfile
from pathlib import Path

# src-Verzeichnis zum Importpfad hinzufuegen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ===== Import-Tests =====

def test_import_models():
    """Prueft, ob models.py importierbar ist."""
    from models import Prompt, Version, Board, BoardItem, CopyMode
    assert Prompt is not None
    assert Version is not None
    assert Board is not None
    assert BoardItem is not None
    assert CopyMode is not None


def test_import_storage():
    """Prueft, ob storage.py importierbar ist."""
    from storage import Storage
    assert Storage is not None


def test_import_event_bus():
    """Prueft, ob event_bus.py importierbar ist."""
    from event_bus import EventBus, bus
    assert EventBus is not None
    assert bus is not None


# ===== Klassen-Instanziierung =====

def test_create_prompt():
    """Prueft, ob ein Prompt-Objekt erstellt werden kann."""
    from models import Prompt, gen_id, now_iso
    p = Prompt(id=gen_id(), title="Test", purpose="Testzweck", text="Hallo Welt")
    assert p.title == "Test"
    assert p.purpose == "Testzweck"
    assert p.text == "Hallo Welt"
    assert isinstance(p.versions, list)
    assert len(p.versions) == 0


def test_create_version():
    """Prueft, ob ein Version-Objekt erstellt werden kann."""
    from models import Version, gen_id
    v = Version(id=gen_id(), prompt_id="p1", version_number=1, title="V1", text="Text v1")
    assert v.version_number == 1
    assert v.title == "V1"
    assert v.result == ""


def test_create_board():
    """Prueft, ob ein Board-Objekt erstellt werden kann."""
    from models import Board, gen_id
    b = Board(id=gen_id(), title="Mein Board")
    assert b.title == "Mein Board"
    assert isinstance(b.items, list)


def test_copy_mode_enum():
    """Prueft die CopyMode-Enum-Werte."""
    from models import CopyMode
    assert CopyMode.TITLE.value == "title"
    assert CopyMode.TEXT.value == "text"
    assert CopyMode.RESULT.value == "result"
    assert CopyMode.ALL.value == "all"


# ===== Basis-Funktionalitaet =====

def test_gen_id_unique():
    """Prueft, ob gen_id() eindeutige IDs erzeugt."""
    from models import gen_id
    ids = {gen_id() for _ in range(100)}
    assert len(ids) == 100


def test_now_iso_format():
    """Prueft, ob now_iso() einen ISO-Zeitstempel liefert."""
    from models import now_iso
    ts = now_iso()
    assert "T" in ts
    assert len(ts) >= 19


def test_prompt_serialization():
    """Prueft Prompt-Serialisierung und Deserialisierung."""
    from models import Prompt, Version, gen_id, prompt_to_dict, prompt_from_dict
    v = Version(id=gen_id(), prompt_id="p1", version_number=1, title="V1", text="t")
    p = Prompt(id="p1", title="Test", purpose="Zweck", text="Text", versions=[v])
    d = prompt_to_dict(p)
    assert isinstance(d, dict)
    assert d["title"] == "Test"
    assert len(d["versions"]) == 1

    p2 = prompt_from_dict(d)
    assert p2.id == p.id
    assert p2.title == p.title
    assert len(p2.versions) == 1
    assert p2.versions[0].title == "V1"


def test_storage_crud(tmp_path):
    """Prueft grundlegende Storage-Operationen (CRUD)."""
    from storage import Storage
    from models import Prompt, gen_id

    store = Storage(tmp_path)

    # Anfangs leer
    assert len(store.load_prompts()) == 0

    # Erstellen
    p = Prompt(id=gen_id(), title="Mein Prompt", purpose="Test", text="Inhalt")
    store.upsert_prompt(p)
    loaded = store.load_prompts()
    assert len(loaded) == 1
    assert loaded[0].title == "Mein Prompt"

    # Aktualisieren
    p.title = "Geaendert"
    store.upsert_prompt(p)
    loaded = store.load_prompts()
    assert len(loaded) == 1
    assert loaded[0].title == "Geaendert"

    # Loeschen
    store.delete_prompt(p.id)
    assert len(store.load_prompts()) == 0


def test_storage_boards(tmp_path):
    """Prueft Board-Operationen im Storage."""
    from storage import Storage
    from models import Board, gen_id

    store = Storage(tmp_path)
    assert len(store.load_boards()) == 0

    b = Board(id=gen_id(), title="Board 1")
    store.upsert_board(b)
    assert len(store.load_boards()) == 1

    store.delete_board(b.id)
    assert len(store.load_boards()) == 0


def test_storage_add_item_to_board(tmp_path):
    """Prueft das Hinzufuegen von Items zu einem Board."""
    from storage import Storage
    from models import Board, gen_id

    store = Storage(tmp_path)
    b = Board(id=gen_id(), title="Board")
    store.upsert_board(b)

    success, item_id = store.add_item_to_board(b.id, "prompt_1")
    assert success is True
    assert item_id is not None

    # Duplikat wird abgelehnt
    success2, _ = store.add_item_to_board(b.id, "prompt_1")
    assert success2 is False


# ===== Erweiterte Tests =====

def test_board_serialization():
    """Prueft Board-Serialisierung und Deserialisierung."""
    from models import Board, BoardItem, gen_id, board_to_dict, board_from_dict
    item = BoardItem(id=gen_id(), board_id="b1", prompt_id="p1", version_id="v1")
    b = Board(id="b1", title="Test Board", description="Beschreibung", items=[item])
    d = board_to_dict(b)
    assert isinstance(d, dict)
    assert d["title"] == "Test Board"
    assert len(d["items"]) == 1

    b2 = board_from_dict(d)
    assert b2.id == b.id
    assert b2.title == b.title
    assert b2.description == "Beschreibung"
    assert len(b2.items) == 1
    assert b2.items[0].prompt_id == "p1"
    assert b2.items[0].version_id == "v1"


def test_prompt_default_values():
    """Prueft, ob Default-Werte korrekt gesetzt werden."""
    from models import Prompt, gen_id
    p = Prompt(id=gen_id(), title="T", purpose="P", text="X")
    assert isinstance(p.tags, list)
    assert len(p.tags) == 0
    assert p.last_result == ""
    assert "T" in p.created_at  # ISO-Format enthaelt 'T'
    assert "T" in p.updated_at


def test_version_with_tags():
    """Prueft Version mit Tags."""
    from models import Version, gen_id
    v = Version(id=gen_id(), prompt_id="p1", version_number=2,
                title="V2", text="Text", tags=["tag1", "tag2"], result="Ergebnis")
    assert v.tags == ["tag1", "tag2"]
    assert v.result == "Ergebnis"
    assert v.version_number == 2


def test_storage_add_version(tmp_path):
    """Prueft das Hinzufuegen einer Version zu einem Prompt."""
    from storage import Storage
    from models import Prompt, Version, gen_id

    store = Storage(tmp_path)
    p = Prompt(id=gen_id(), title="Prompt", purpose="Test", text="Inhalt")
    store.upsert_prompt(p)

    v = Version(id=gen_id(), prompt_id=p.id, version_number=1, title="V1", text="Version 1")
    store.add_version(p.id, v)

    loaded = store.load_prompts()
    assert len(loaded) == 1
    assert len(loaded[0].versions) == 1
    assert loaded[0].versions[0].title == "V1"


def test_storage_next_version_number(tmp_path):
    """Prueft die Berechnung der naechsten Versionsnummer."""
    from storage import Storage
    from models import Prompt, Version, gen_id

    store = Storage(tmp_path)
    p = Prompt(id=gen_id(), title="P", purpose="T", text="X")
    store.upsert_prompt(p)

    assert store.next_version_number(p.id) == 1

    v1 = Version(id=gen_id(), prompt_id=p.id, version_number=1, title="V1", text="T1")
    store.add_version(p.id, v1)
    assert store.next_version_number(p.id) == 2

    v3 = Version(id=gen_id(), prompt_id=p.id, version_number=3, title="V3", text="T3")
    store.add_version(p.id, v3)
    assert store.next_version_number(p.id) == 4


def test_storage_get_version(tmp_path):
    """Prueft get_version()."""
    from storage import Storage
    from models import Prompt, Version, gen_id

    store = Storage(tmp_path)
    p = Prompt(id=gen_id(), title="P", purpose="T", text="X")
    store.upsert_prompt(p)

    v = Version(id=gen_id(), prompt_id=p.id, version_number=1, title="V1", text="T1")
    store.add_version(p.id, v)

    found = store.get_version(p.id, v.id)
    assert found is not None
    assert found.title == "V1"

    # Nicht existierender Prompt
    assert store.get_version("nonexistent", v.id) is None
    # Nicht existierende Version
    assert store.get_version(p.id, "nonexistent") is None


def test_storage_multiple_prompts(tmp_path):
    """Prueft Storage mit mehreren Prompts."""
    from storage import Storage
    from models import Prompt, gen_id

    store = Storage(tmp_path)
    ids = []
    for i in range(5):
        p = Prompt(id=gen_id(), title=f"Prompt {i}", purpose="T", text=f"Text {i}")
        store.upsert_prompt(p)
        ids.append(p.id)

    loaded = store.load_prompts()
    assert len(loaded) == 5

    # Einen loeschen
    store.delete_prompt(ids[2])
    loaded = store.load_prompts()
    assert len(loaded) == 4
    assert all(p.id != ids[2] for p in loaded)


def test_storage_board_item_with_version(tmp_path):
    """Prueft Board-Item mit Version-ID."""
    from storage import Storage
    from models import Board, gen_id

    store = Storage(tmp_path)
    b = Board(id=gen_id(), title="Board")
    store.upsert_board(b)

    ok1, id1 = store.add_item_to_board(b.id, "p1", version_id="v1")
    assert ok1 is True

    # Gleicher Prompt, andere Version = kein Duplikat
    ok2, id2 = store.add_item_to_board(b.id, "p1", version_id="v2")
    assert ok2 is True

    # Gleicher Prompt + gleiche Version = Duplikat
    ok3, _ = store.add_item_to_board(b.id, "p1", version_id="v1")
    assert ok3 is False

    boards = store.load_boards()
    assert len(boards[0].items) == 2


def test_storage_nonexistent_board(tmp_path):
    """Prueft Verhalten bei nicht existierendem Board."""
    from storage import Storage

    store = Storage(tmp_path)
    ok, item_id = store.add_item_to_board("nonexistent", "p1")
    assert ok is False
    assert item_id is None


def test_prompt_from_dict_missing_fields():
    """Prueft prompt_from_dict() mit fehlenden optionalen Feldern."""
    from models import prompt_from_dict
    d = {"id": "x1", "title": "Minimal"}
    p = prompt_from_dict(d)
    assert p.id == "x1"
    assert p.title == "Minimal"
    assert p.purpose == ""
    assert p.text == ""
    assert p.tags == []
    assert p.versions == []


def test_clipboard_manager_build_copy_text():
    """Prueft ClipboardManager.build_copy_text() ohne GUI."""
    from models import Prompt, Version, CopyMode, gen_id

    class MockSettings:
        def get_copy_mode(self):
            return CopyMode.ALL
        def get_include_metadata(self):
            return True

    from clipboard_manager import ClipboardManager
    clip = ClipboardManager(MockSettings())

    p = Prompt(id=gen_id(), title="Titel", purpose="Zweck", text="Mein Text",
               tags=["ai", "test"], last_result="Ergebnis")
    result = clip.build_copy_text(p)
    assert "Titel" in result
    assert "Mein Text" in result
    assert "Ergebnis" in result
    assert "ai" in result

    # Version-Modus
    v = Version(id=gen_id(), prompt_id=p.id, version_number=1,
                title="V1", text="Version Text", tags=["v1tag"], result="V-Result")
    result_v = clip.build_copy_text(p, v)
    assert "V1" in result_v
    assert "Version Text" in result_v


def test_clipboard_manager_text_mode():
    """Prueft ClipboardManager im TEXT-Modus."""
    from models import Prompt, CopyMode, gen_id

    class MockSettings:
        def get_copy_mode(self):
            return CopyMode.TEXT
        def get_include_metadata(self):
            return False

    from clipboard_manager import ClipboardManager
    clip = ClipboardManager(MockSettings())
    p = Prompt(id=gen_id(), title="T", purpose="P", text="Nur der Text")
    result = clip.build_copy_text(p)
    assert result == "Nur der Text"


def test_clipboard_manager_title_mode():
    """Prueft ClipboardManager im TITLE-Modus."""
    from models import Prompt, CopyMode, gen_id

    class MockSettings:
        def get_copy_mode(self):
            return CopyMode.TITLE
        def get_include_metadata(self):
            return False

    from clipboard_manager import ClipboardManager
    clip = ClipboardManager(MockSettings())
    p = Prompt(id=gen_id(), title="Nur Titel", purpose="P", text="Text")
    result = clip.build_copy_text(p)
    assert result == "Nur Titel"
