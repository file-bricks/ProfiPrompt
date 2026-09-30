from __future__ import annotations

import os
import stat
from pathlib import Path
import pytest

from atomic_io import (
    atomic_publish_file,
    atomic_write_json,
    atomic_write_text,
    is_protected_path,
)
from library_export import write_library_export
from models import Board, Prompt, Version, gen_id
from pdf_exporter import _export_html_to_pdf, export_single_prompt
from profiprompt import MainWindow
from storage import Storage


def test_is_protected_path_resolution(tmp_path: Path):
    target = tmp_path / "prompts.json"
    target.touch()
    protected = [str(tmp_path / "prompts.json"), tmp_path / "boards.json"]

    assert is_protected_path(target, protected) is True
    assert is_protected_path(tmp_path / "other.txt", protected) is False
    assert is_protected_path(target, None) is False


def test_atomic_write_text_creates_parent_dir_and_file(tmp_path: Path):
    dest = tmp_path / "nested" / "deeply" / "test_output.txt"
    content = "Hello World! Prüftext mit Umlauten äöüß."

    atomic_write_text(dest, content)

    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == content

    # Ensure no lingering temp files in directory
    parent_files = list(dest.parent.iterdir())
    assert parent_files == [dest]


def test_atomic_write_text_preserves_original_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dest = tmp_path / "existing.txt"
    dest.write_text("Original uncorrupted content", encoding="utf-8")

    def broken_replace(src, dst):
        raise OSError("Simulated disk error during replace")

    monkeypatch.setattr(os, "replace", broken_replace)

    with pytest.raises(OSError, match="Simulated disk error"):
        atomic_write_text(dest, "New corrupted text")

    # Original content must remain intact
    assert dest.read_text(encoding="utf-8") == "Original uncorrupted content"

    # No leftover .tmp files
    leftovers = [p for p in tmp_path.iterdir() if p.name != "existing.txt"]
    assert leftovers == []


def test_atomic_write_text_rejects_protected_path(tmp_path: Path):
    protected_file = tmp_path / "prompts.json"
    protected_file.write_text('{"prompts": []}', encoding="utf-8")

    with pytest.raises(PermissionError, match="geschützte Bibliotheksdatei"):
        atomic_write_text(
            protected_file,
            "Malicious overwrite",
            protected_paths=[protected_file],
        )

    assert protected_file.read_text(encoding="utf-8") == '{"prompts": []}'


def test_atomic_write_json_roundtrip_and_readonly_handling(tmp_path: Path):
    dest = tmp_path / "data.json"
    data = {"key": "Wert mit Umlauten: äöü", "numbers": [1, 2, 3]}

    atomic_write_json(dest, data)
    assert dest.exists()

    # Mark destination file read-only on Windows
    os.chmod(dest, stat.S_IREAD)

    # Overwrite read-only file atomically
    updated_data = {"key": "Neuer Wert", "numbers": [4, 5]}
    atomic_write_json(dest, updated_data)

    import json
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded == updated_data


def test_atomic_publish_file_success_and_cleanup(tmp_path: Path):
    src = tmp_path / "source.tmp"
    src.write_text("Staged payload", encoding="utf-8")

    target = tmp_path / "published.txt"
    target.write_text("Old payload", encoding="utf-8")

    atomic_publish_file(src, target)

    assert not src.exists()
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "Staged payload"


def test_storage_atomic_writes_and_temp_cleanup(tmp_path: Path):
    store = Storage(data_dir=tmp_path)
    prompts_file = store.prompts_file
    boards_file = store.boards_file

    assert prompts_file.exists()
    assert boards_file.exists()

    p = Prompt(id=gen_id(), title="Test Prompt", purpose="Atomic Test", text="Body text")
    store.upsert_prompt(p)

    loaded = store.get_prompt(p.id)
    assert loaded is not None
    assert loaded.title == "Test Prompt"

    b = Board(id=gen_id(), title="Work Board", items=[])
    store.upsert_board(b)

    loaded_b = next((x for x in store.load_boards() if x.id == b.id), None)
    assert loaded_b is not None
    assert loaded_b.title == "Work Board"

    # Verify no temp files left behind in storage directory
    all_files = list(tmp_path.iterdir())
    assert set(all_files) == {prompts_file, boards_file}


def test_library_export_protects_storage_files(tmp_path: Path):
    store = Storage(data_dir=tmp_path)
    prompts_file = store.prompts_file

    p = Prompt(id=gen_id(), title="Export Me", purpose="Testing", text="Payload")
    store.upsert_prompt(p)

    out_json = tmp_path / "export.json"
    data = write_library_export(store, out_json)

    assert out_json.exists()
    assert data["stats"]["prompt_count"] == 1
    assert data["prompts"][0]["title"] == "Export Me"

    # Attempting to export onto prompts.json must be blocked
    with pytest.raises(PermissionError, match="geschützte Bibliotheksdatei"):
        write_library_export(store, prompts_file)


def test_pdf_export_rejects_protected_path(tmp_path: Path):
    protected_target = tmp_path / "prompts.json"
    protected_target.write_text("{}", encoding="utf-8")

    result = _export_html_to_pdf(
        "<html><body>Denied</body></html>",
        str(protected_target),
        protected_paths=[protected_target],
    )
    assert result is False
    assert protected_target.read_text(encoding="utf-8") == "{}"


def test_pdf_export_preserves_target_on_invalid_pdf_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target_pdf = tmp_path / "valid.pdf"
    target_pdf.write_bytes(b"%PDF-1.4\nExisting valid PDF content")

    # Mock printer so print_ produces corrupt non-PDF output into tmp file
    class FakePrinter:
        def __init__(self, filename):
            self.filename = filename

    import pdf_exporter

    def fake_init_printer(path: str):
        # Write corrupted non-PDF payload into the temporary destination
        with open(path, "wb") as f:
            f.write(b"Not A Valid PDF File Header")
        return FakePrinter(path)

    monkeypatch.setattr(pdf_exporter, "_init_printer", fake_init_printer)

    success = _export_html_to_pdf("<html><body>Error Test</body></html>", str(target_pdf))
    assert success is False

    # Target PDF must remain untouched
    assert target_pdf.read_bytes() == b"%PDF-1.4\nExisting valid PDF content"

    # No leftover .tmp files
    leftover = [p for p in tmp_path.iterdir() if p.name.endswith(".pdf.tmp") or ".tmp." in p.name]
    assert leftover == []


def test_mainwindow_protected_paths_helper(tmp_path: Path):
    store = Storage(data_dir=tmp_path)

    window = MainWindow.__new__(MainWindow)
    # 1. Uninitialized without storage attribute
    assert window._protected_paths() == []

    # 2. With initialized storage
    window.storage = store
    paths = window._protected_paths()
    assert len(paths) == 2
    assert Path(store.prompts_file) in [Path(p) for p in paths]
    assert Path(store.boards_file) in [Path(p) for p in paths]
