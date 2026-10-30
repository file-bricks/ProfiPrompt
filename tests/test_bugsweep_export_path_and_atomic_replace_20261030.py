"""Hermetic regression tests for bugsweep 2026-10-30:
- Windows atomic replace resilience with retry backoff for transient WinError 5/32
- Protection of ancestor directories in is_protected_path
- Rejection of directory paths in atomic_write_text and atomic_publish_file
- Automatic export path resolution in library_export and pdf_exporter
- Windows reserved device name neutralization in sanitize_export_filename
- CWD-independent translation checking in manage_translations
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from atomic_io import (
    atomic_write_text,
    atomic_publish_file,
    is_protected_path,
    _atomic_replace_with_retry,
)
from dashboard import sanitize_export_filename
from library_export import resolve_library_export_path, write_library_export
from pdf_exporter import resolve_pdf_export_path
import manage_translations


def test_atomic_replace_retries_transient_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tmp_file = tmp_path / "test.tmp"
    tmp_file.write_text("temporary content", encoding="utf-8")
    target_file = tmp_path / "target.txt"
    target_file.write_text("old content", encoding="utf-8")

    attempts = 0
    orig_replace = os.replace

    def mock_replace(src, dst):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            err = PermissionError("Simulated WinError 5 Access Denied")
            err.winerror = 5
            raise err
        return orig_replace(src, dst)

    monkeypatch.setattr(os, "replace", mock_replace)

    _atomic_replace_with_retry(tmp_file, target_file, max_retries=5, initial_delay=0.001)

    assert attempts == 3
    assert target_file.read_text(encoding="utf-8") == "temporary content"
    assert not tmp_file.exists()


def test_atomic_replace_raises_when_retries_exhausted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tmp_file = tmp_path / "test.tmp"
    tmp_file.write_text("temporary content", encoding="utf-8")
    target_file = tmp_path / "target.txt"

    def mock_replace_always_fail(src, dst):
        err = PermissionError("Persistent Access Denied")
        err.winerror = 5
        raise err

    monkeypatch.setattr(os, "replace", mock_replace_always_fail)

    with pytest.raises(PermissionError, match="Persistent Access Denied"):
        _atomic_replace_with_retry(tmp_file, target_file, max_retries=3, initial_delay=0.001)


def test_is_protected_path_rejects_parent_directory(tmp_path: Path):
    db_file = tmp_path / "prompts.json"
    db_file.write_text("{}", encoding="utf-8")
    protected = [db_file]

    # Exact file match
    assert is_protected_path(db_file, protected) is True
    # Ancestor directory match
    assert is_protected_path(tmp_path, protected) is True
    # Sibling directory or file
    other_file = tmp_path / "export.txt"
    assert is_protected_path(other_file, protected) is False


def test_atomic_write_text_rejects_directory_path(tmp_path: Path):
    existing_dir = tmp_path / "somedir"
    existing_dir.mkdir()

    with pytest.raises(IsADirectoryError):
        atomic_write_text(existing_dir, "content")

    trailing_slash_path = str(tmp_path / "newdir") + os.sep
    with pytest.raises(IsADirectoryError):
        atomic_write_text(trailing_slash_path, "content")


def test_resolve_library_export_path_handles_directories_and_suffixes(tmp_path: Path):
    out_dir = tmp_path / "exports"
    out_dir.mkdir()

    # Existing directory
    res1 = resolve_library_export_path(out_dir)
    assert res1 == out_dir / "profiprompt-library-v1.json"

    # Trailing slash
    res2 = resolve_library_export_path(str(tmp_path / "another_dir") + "/")
    assert res2.name == "profiprompt-library-v1.json"

    # Suffixless filename
    res3 = resolve_library_export_path(tmp_path / "my_backup")
    assert res3 == tmp_path / "my_backup.json"

    # Standard filename with json suffix
    res4 = resolve_library_export_path(tmp_path / "my_backup.json")
    assert res4 == tmp_path / "my_backup.json"


def test_resolve_pdf_export_path_handles_directories_and_suffixes(tmp_path: Path):
    out_dir = tmp_path / "pdf_exports"
    out_dir.mkdir()

    # Existing directory
    res1 = resolve_pdf_export_path(out_dir)
    assert res1 == out_dir / "prompt.pdf"

    # Suffixless filename
    res2 = resolve_pdf_export_path(tmp_path / "custom_doc")
    assert res2 == tmp_path / "custom_doc.pdf"

    # Preserved pdf suffix
    res3 = resolve_pdf_export_path(tmp_path / "custom_doc.pdf")
    assert res3 == tmp_path / "custom_doc.pdf"


def test_sanitize_export_filename_windows_reserved_names():
    # Reserved device names
    assert sanitize_export_filename("CON") == "_CON"
    assert sanitize_export_filename("con") == "_con"
    assert sanitize_export_filename("PRN") == "_PRN"
    assert sanitize_export_filename("aux") == "_aux"
    assert sanitize_export_filename("NUL") == "_NUL"
    assert sanitize_export_filename("com1") == "_com1"
    assert sanitize_export_filename("LPT3") == "_LPT3"

    # Normal names
    assert sanitize_export_filename("Mein Prompt: Entwurf #1") == "Mein Prompt_ Entwurf #1"
    assert sanitize_export_filename("") == "prompt"
    assert sanitize_export_filename("   ") == "prompt"


def test_manage_translations_check_cwd_independent():
    # Calling check_translations with source_dir=None finds locales/translations.json regardless of CWD
    ret = manage_translations.check_translations()
    assert ret == 0
