"""Versioned JSON export for the portable ProfiPrompt library format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atomic_io import atomic_write_json
from app_version import __version__
from models import Board, Prompt, board_to_dict, prompt_to_dict

SCHEMA_VERSION = "profiprompt-library-v1"
APP_NAME = "ProfiPrompt"
APP_VERSION = __version__
DEFAULT_LIBRARY_EXPORT_NAME = "profiprompt-library-v1.json"


def resolve_library_export_path(path: str | Path) -> Path:
    """Resolve an export path into a validated target file path.

    Handles directory paths and trailing slashes by appending the canonical
    export filename 'profiprompt-library-v1.json'. Appends '.json' if extension
    is missing.
    """
    raw_str = str(path).strip()
    if not raw_str:
        return Path(DEFAULT_LIBRARY_EXPORT_NAME)

    p = Path(raw_str)
    if p.is_dir() or raw_str.endswith(("/", "\\")):
        return p / DEFAULT_LIBRARY_EXPORT_NAME

    if not p.suffix:
        return p.with_suffix(".json")
    return p


def build_library_export(storage, exported_at: str | None = None) -> dict[str, Any]:
    """Build a portable export payload from the current Storage state."""
    # Production Storage must not replace a backup with an empty/partial export
    # after a failed read. Small in-memory providers retain the existing protocol.
    if callable(getattr(storage, "load_library", None)):
        prompts, boards = storage.load_library()
    else:
        prompts = storage.load_prompts()
        boards = storage.load_boards()
    exported_at = exported_at or datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": SCHEMA_VERSION,
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "exported_at": exported_at,
        },
        "stats": _build_stats(prompts, boards),
        "tags": _collect_tags(prompts),
        "prompts": [prompt_to_dict(prompt) for prompt in prompts],
        "boards": [board_to_dict(board) for board in boards],
    }


def write_library_export(storage, path: str | Path) -> dict[str, Any]:
    """Write the portable library export as UTF-8 JSON and return the payload."""
    target_path = resolve_library_export_path(path)
    payload = build_library_export(storage)
    protected = []
    if hasattr(storage, "prompts_file"):
        protected.append(storage.prompts_file)
    if hasattr(storage, "boards_file"):
        protected.append(storage.boards_file)
    atomic_write_json(target_path, payload, indent=2, protected_paths=protected)
    return payload


def _build_stats(prompts: list[Prompt], boards: list[Board]) -> dict[str, int]:
    return {
        "prompt_count": len(prompts),
        "version_count": sum(len(prompt.versions) for prompt in prompts if prompt and prompt.versions),
        "board_count": len(boards),
        "board_item_count": sum(len(board.items) for board in boards if board and board.items),
    }


def _collect_tags(prompts: list[Prompt]) -> list[str]:
    tags: set[str] = set()
    for prompt in prompts:
        if prompt and prompt.tags:
            tags.update(str(tag).strip() for tag in prompt.tags if tag is not None and str(tag).strip())
        if prompt and prompt.versions:
            for version in prompt.versions:
                if version and version.tags:
                    tags.update(str(tag).strip() for tag in version.tags if tag is not None and str(tag).strip())
    return sorted(tags, key=str.casefold)
