"""Versioned JSON export for the portable ProfiPrompt library format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import Board, Prompt, board_to_dict, prompt_to_dict

SCHEMA_VERSION = "profiprompt-library-v1"
APP_NAME = "ProfiPrompt"
APP_VERSION = "1.0.1"


def build_library_export(storage, exported_at: str | None = None) -> dict[str, Any]:
    """Build a portable export payload from the current Storage state."""
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
    payload = build_library_export(storage)
    target = Path(path)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _build_stats(prompts: list[Prompt], boards: list[Board]) -> dict[str, int]:
    return {
        "prompt_count": len(prompts),
        "version_count": sum(len(prompt.versions) for prompt in prompts),
        "board_count": len(boards),
        "board_item_count": sum(len(board.items) for board in boards),
    }


def _collect_tags(prompts: list[Prompt]) -> list[str]:
    tags: set[str] = set()
    for prompt in prompts:
        tags.update(tag for tag in prompt.tags if tag)
        for version in prompt.versions:
            tags.update(tag for tag in version.tags if tag)
    return sorted(tags, key=str.casefold)
