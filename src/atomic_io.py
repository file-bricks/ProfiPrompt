"""Atomic and fail-safe file I/O operations for ProfiPrompt.

Provides collision-free temporary file writes, fsync durability guarantees,
Windows read-only attribute handling, cleanup guards, and protection against
accidental overwrites of internal library state files.
"""

from __future__ import annotations

import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any, Iterable


def resolve_path(path: str | Path) -> Path:
    """Resolve a path to its normalized absolute representation."""
    p = Path(path).expanduser()
    try:
        return p.resolve()
    except (OSError, RuntimeError):
        return p.absolute()


def is_protected_path(target: str | Path, protected_paths: Iterable[str | Path] | None) -> bool:
    """Check whether target matches or aliases any protected path."""
    if not protected_paths:
        return False
    target_resolved = resolve_path(target)
    for protected in protected_paths:
        if protected is None:
            continue
        try:
            prot_resolved = resolve_path(protected)
            if target_resolved == prot_resolved:
                return True
            if target_resolved.exists() and prot_resolved.exists():
                try:
                    if os.path.samefile(target_resolved, prot_resolved):
                        return True
                except (OSError, ValueError):
                    pass
        except (OSError, RuntimeError, ValueError):
            continue
    return False


def atomic_write_text(
    target: str | Path,
    text: str,
    encoding: str = "utf-8",
    protected_paths: Iterable[str | Path] | None = None,
) -> Path:
    """Atomically write text content to target file.

    Guarantees:
    - Pre-flight rejection of protected files (e.g. internal storage databases).
    - Writes to a unique per-process/UUID temp file in the target directory.
    - Explicit flush and fsync for crash durability.
    - Windows read-only permission reset prior to atomic replace.
    - Automatic cleanup of temporary file on error.
    - Preserves existing target file untouched if writing or replace fails.
    """
    target_path = Path(target)
    if is_protected_path(target_path, protected_paths):
        raise PermissionError(
            f"Zielpfad '{target_path}' darf keine geschützte Bibliotheksdatei überschreiben."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(
        f".{target_path.name}.tmp.{os.getpid()}_{uuid.uuid4().hex[:8]}"
    )

    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass

        if target_path.exists():
            try:
                os.chmod(target_path, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass

        os.replace(tmp_path, target_path)
        return target_path
    finally:
        if tmp_path.exists():
            try:
                os.chmod(tmp_path, stat.S_IWRITE | stat.S_IREAD)
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def atomic_write_json(
    target: str | Path,
    data: Any,
    indent: int = 2,
    protected_paths: Iterable[str | Path] | None = None,
) -> Path:
    """Atomically serialize and write JSON data to target file."""
    text = json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    return atomic_write_text(target, text, encoding="utf-8", protected_paths=protected_paths)


def atomic_publish_file(
    source_tmp: str | Path,
    target: str | Path,
    protected_paths: Iterable[str | Path] | None = None,
    min_bytes: int = 1,
) -> Path:
    """Publish an already generated temporary file to target atomically.

    Verifies non-emptiness (min_bytes) and cleans up source_tmp on failure.
    """
    tmp_path = Path(source_tmp)
    target_path = Path(target)

    if is_protected_path(target_path, protected_paths):
        raise PermissionError(
            f"Zielpfad '{target_path}' darf keine geschützte Bibliotheksdatei überschreiben."
        )

    if not tmp_path.exists():
        raise FileNotFoundError(f"Temporäre Quelldatei nicht gefunden: {tmp_path}")

    actual_size = tmp_path.stat().st_size
    if actual_size < min_bytes:
        raise ValueError(
            f"Temporäre Datei ist unvollständig ({actual_size} Bytes < {min_bytes} Bytes): {tmp_path}"
        )

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            try:
                os.chmod(target_path, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
        os.replace(tmp_path, target_path)
        return target_path
    finally:
        if tmp_path.exists():
            try:
                os.chmod(tmp_path, stat.S_IWRITE | stat.S_IREAD)
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
