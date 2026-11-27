"""Non-destructive JSON merge importer for the portable profiprompt-library-v1 format.

Validates prompts and boards together in memory before writing, persists prompts
before boards to keep board item references valid, and never silently overwrites
diverging local entries (conflicts are returned for explicit 3-way resolution).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple

import models as _models

ConflictChoice = Literal["keep_local", "keep_copy", "take_remote"]
MAX_LIBRARY_PAYLOAD_BYTES = 16 * 1024 * 1024


def _coerce_prompt(prompt: Any) -> _models.Prompt:
    """Coerce dict, live Prompt, or cross-module/reloaded Prompt dataclass safely."""
    if isinstance(prompt, _models.Prompt):
        return prompt
    if isinstance(prompt, dict):
        return _models.prompt_from_dict(prompt)
    if dataclasses.is_dataclass(prompt) and not isinstance(prompt, type):
        return _models.prompt_from_dict(dataclasses.asdict(prompt))
    return _models.prompt_from_dict(prompt)


def _coerce_board(board: Any) -> _models.Board:
    """Coerce dict, live Board, or cross-module/reloaded Board dataclass safely."""
    if isinstance(board, _models.Board):
        return board
    if isinstance(board, dict):
        return _models.board_from_dict(board)
    if dataclasses.is_dataclass(board) and not isinstance(board, type):
        return _models.board_from_dict(dataclasses.asdict(board))
    return _models.board_from_dict(board)


def canonical_prompt_hash(prompt: _models.Prompt | Dict[str, Any]) -> str:
    """Deterministic content hash for a Prompt including its nested Versions."""
    p = _coerce_prompt(prompt)
    comparable = {
        "id": p.id,
        "title": p.title,
        "purpose": p.purpose,
        "text": p.text,
        "tags": list(p.tags or []),
        "last_result": p.last_result,
        "versions": [
            {
                "id": v.id,
                "prompt_id": v.prompt_id,
                "version_number": v.version_number,
                "title": v.title,
                "text": v.text,
                "result": v.result,
                "tags": list(v.tags or []),
            }
            for v in sorted(p.versions or [], key=lambda x: (x.version_number, x.id))
        ],
    }
    encoded = json.dumps(comparable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_board_hash(board: _models.Board | Dict[str, Any]) -> str:
    """Deterministic content hash for a Board including its ordered BoardItems."""
    b = _coerce_board(board)
    comparable = {
        "id": b.id,
        "title": b.title,
        "description": b.description,
        "items": [
            {
                "id": it.id,
                "board_id": it.board_id,
                "prompt_id": it.prompt_id,
                "version_id": it.version_id,
            }
            for it in (b.items or [])
        ],
    }
    encoded = json.dumps(comparable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass
class ImportConflict:
    """Describes a diverging prompt or board discovered during merge/import."""

    kind: Literal["prompt", "board"]
    item_id: str
    title: str
    source: str
    local_payload: Dict[str, Any]
    remote_payload: Dict[str, Any]
    local_updated_at: str = ""
    remote_updated_at: str = ""
    remote_rev: Optional[int] = None


@dataclass
class LibraryImportResult:
    """Summary of a non-destructive library merge."""

    added_prompts: int = 0
    updated_prompts: int = 0
    added_boards: int = 0
    updated_boards: int = 0
    skipped_deleted: int = 0
    unchanged: int = 0
    conflicts: List[ImportConflict] = field(default_factory=list)
    imported_hashes: Dict[str, str] = field(default_factory=dict)


def parse_library_payload(raw: Dict[str, Any] | str | Path) -> Tuple[List[_models.Prompt], List[_models.Board], Dict[str, Any]]:
    """Parse and validate a profiprompt-library-v1 JSON payload in memory."""
    if isinstance(raw, Path):
        if raw.is_symlink():
            raise ValueError(f"Symlink-Importdatei abgelehnt: {raw}")
        if raw.stat().st_size > MAX_LIBRARY_PAYLOAD_BYTES:
            raise ValueError(f"Importdatei überschreitet Größenlimit ({MAX_LIBRARY_PAYLOAD_BYTES} Bytes): {raw}")
        data = json.loads(raw.read_text(encoding="utf-8-sig"))
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_LIBRARY_PAYLOAD_BYTES:
            raise ValueError(f"Import-JSON überschreitet Größenlimit ({MAX_LIBRARY_PAYLOAD_BYTES} Bytes).")
        data = json.loads(raw.lstrip("\ufeff"))
    elif isinstance(raw, dict):
        data = raw
    else:
        raise ValueError("Bibliotheks-Import erwartet dict, JSON-String oder Pfad.")

    if not isinstance(data, dict):
        raise ValueError("Bibliotheks-JSON muss ein Objekt sein.")

    raw_prompts = data.get("prompts", [])
    raw_boards = data.get("boards", [])
    if not isinstance(raw_prompts, list) or not isinstance(raw_boards, list):
        raise ValueError("Ungültige profiprompt-library-v1-Struktur: prompts und boards müssen Listen sein.")

    prompts: List[_models.Prompt] = []
    seen_prompt_ids: set[str] = set()
    for entry in raw_prompts:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        p = _models.prompt_from_dict(entry)
        if p.id in seen_prompt_ids:
            continue
        seen_prompt_ids.add(p.id)
        prompts.append(p)

    boards: List[_models.Board] = []
    seen_board_ids: set[str] = set()
    for entry in raw_boards:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        b = _models.board_from_dict(entry)
        if b.id in seen_board_ids:
            continue
        seen_board_ids.add(b.id)
        boards.append(b)

    manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}
    return prompts, boards, manifest


def _prune_board_items_for_existing_prompts(board: _models.Board, valid_prompt_ids: set[str]) -> _models.Board:
    """Ensure every BoardItem points to an existing prompt (prevent dangling refs)."""
    cleaned_items = [it for it in (board.items or []) if it.prompt_id in valid_prompt_ids]
    return _models.Board(
        id=board.id,
        title=board.title,
        description=board.description,
        items=cleaned_items,
        created_at=board.created_at,
    )


def merge_library_payload(
    storage,
    raw_payload: Dict[str, Any] | str | Path,
    *,
    source_label: str = "import",
    last_imported_hashes: Optional[Dict[str, str]] = None,
    deleted_ids: Optional[Sequence[str]] = None,
    conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None,
) -> LibraryImportResult:
    """Merge a profiprompt-library-v1 payload into ``storage`` without silent overwrites.

    - Unknown IDs are inserted (unless listed in ``deleted_ids``).
    - Identical content hashes are skipped as unchanged.
    - Existing entries whose local hash still equals ``last_imported_hashes[key]``
      (i.e. locally untouched since the last import from this source) fast-forward.
    - Diverging entries either ask ``conflict_resolver`` or remain untouched locally
      and are recorded in ``result.conflicts``.
    - Prompts are always validated and written BEFORE boards.
    """
    incoming_prompts, incoming_boards, _manifest = parse_library_payload(raw_payload)
    known_hashes = dict(last_imported_hashes or {})
    deleted_set = set(deleted_ids or ())

    local_prompts = list(storage.load_prompts())
    local_boards = list(storage.load_boards())
    prompt_by_id: Dict[str, _models.Prompt] = {p.id: p for p in local_prompts}
    board_by_id: Dict[str, _models.Board] = {b.id: b for b in local_boards}

    result = LibraryImportResult()
    prompts_changed = False
    boards_changed = False

    # 1. Merge prompts first
    for inc_p in incoming_prompts:
        key = f"prompt:{inc_p.id}"
        if key in deleted_set or inc_p.id in deleted_set:
            result.skipped_deleted += 1
            continue

        inc_hash = canonical_prompt_hash(inc_p)
        loc_p = prompt_by_id.get(inc_p.id)

        if loc_p is None:
            local_prompts.append(inc_p)
            prompt_by_id[inc_p.id] = inc_p
            result.added_prompts += 1
            result.imported_hashes[key] = inc_hash
            prompts_changed = True
            continue

        loc_hash = canonical_prompt_hash(loc_p)
        if loc_hash == inc_hash:
            result.unchanged += 1
            result.imported_hashes[key] = inc_hash
            continue

        if known_hashes.get(key) == loc_hash:
            # Locally unmodified since last import from this source -> fast-forward
            idx = next(i for i, p in enumerate(local_prompts) if p.id == inc_p.id)
            local_prompts[idx] = inc_p
            prompt_by_id[inc_p.id] = inc_p
            result.updated_prompts += 1
            result.imported_hashes[key] = inc_hash
            prompts_changed = True
            continue

        conflict = ImportConflict(
            kind="prompt",
            item_id=inc_p.id,
            title=loc_p.title or inc_p.title or inc_p.id,
            source=source_label,
            local_payload=_models.prompt_to_dict(loc_p),
            remote_payload=_models.prompt_to_dict(inc_p),
            local_updated_at=loc_p.updated_at,
            remote_updated_at=inc_p.updated_at,
        )
        if conflict_resolver is None:
            result.conflicts.append(conflict)
            continue

        choice = conflict_resolver(conflict)
        if choice == "take_remote":
            idx = next(i for i, p in enumerate(local_prompts) if p.id == inc_p.id)
            local_prompts[idx] = inc_p
            prompt_by_id[inc_p.id] = inc_p
            result.updated_prompts += 1
            result.imported_hashes[key] = inc_hash
            prompts_changed = True
        elif choice == "keep_copy":
            # Take remote as main prompt and preserve local text losslessly as a new Version
            merged_p = _models.prompt_from_dict(_models.prompt_to_dict(inc_p))
            next_vnum = max((v.version_number for v in merged_p.versions), default=0) + 1
            preserved = _models.Version(
                id=_models.gen_id(),
                prompt_id=merged_p.id,
                version_number=next_vnum,
                title=f"{loc_p.title or 'Lokal'} (lokale Kopie)",
                text=loc_p.text,
                result=loc_p.last_result,
                tags=list(loc_p.tags or []),
                created_at=loc_p.created_at,
                updated_at=_models.now_iso(),
            )
            # Also carry over any local versions missing in remote
            remote_v_ids = {v.id for v in merged_p.versions}
            for lv in loc_p.versions or []:
                if lv.id not in remote_v_ids:
                    merged_p.versions.append(lv)
            merged_p.versions.append(preserved)
            merged_p.updated_at = _models.now_iso()
            idx = next(i for i, p in enumerate(local_prompts) if p.id == inc_p.id)
            local_prompts[idx] = merged_p
            prompt_by_id[inc_p.id] = merged_p
            result.updated_prompts += 1
            result.imported_hashes[key] = canonical_prompt_hash(merged_p)
            prompts_changed = True
        else:
            # keep_local (default): do not overwrite
            result.unchanged += 1

    valid_prompt_ids = set(prompt_by_id.keys())

    # 2. Merge boards (referencing validated prompt set)
    for inc_b in incoming_boards:
        key = f"board:{inc_b.id}"
        if key in deleted_set or inc_b.id in deleted_set:
            result.skipped_deleted += 1
            continue

        cleaned_inc_b = _prune_board_items_for_existing_prompts(inc_b, valid_prompt_ids)
        inc_hash = canonical_board_hash(cleaned_inc_b)
        loc_b = board_by_id.get(cleaned_inc_b.id)

        if loc_b is None:
            local_boards.append(cleaned_inc_b)
            board_by_id[cleaned_inc_b.id] = cleaned_inc_b
            result.added_boards += 1
            result.imported_hashes[key] = inc_hash
            boards_changed = True
            continue

        loc_hash = canonical_board_hash(loc_b)
        if loc_hash == inc_hash:
            result.unchanged += 1
            result.imported_hashes[key] = inc_hash
            continue

        if known_hashes.get(key) == loc_hash:
            idx = next(i for i, b in enumerate(local_boards) if b.id == cleaned_inc_b.id)
            local_boards[idx] = cleaned_inc_b
            board_by_id[cleaned_inc_b.id] = cleaned_inc_b
            result.updated_boards += 1
            result.imported_hashes[key] = inc_hash
            boards_changed = True
            continue

        conflict = ImportConflict(
            kind="board",
            item_id=cleaned_inc_b.id,
            title=loc_b.title or cleaned_inc_b.title or cleaned_inc_b.id,
            source=source_label,
            local_payload=_models.board_to_dict(loc_b),
            remote_payload=_models.board_to_dict(cleaned_inc_b),
            local_updated_at=loc_b.created_at,
            remote_updated_at=cleaned_inc_b.created_at,
        )
        if conflict_resolver is None:
            result.conflicts.append(conflict)
            continue

        choice = conflict_resolver(conflict)
        if choice == "take_remote":
            idx = next(i for i, b in enumerate(local_boards) if b.id == cleaned_inc_b.id)
            local_boards[idx] = cleaned_inc_b
            board_by_id[cleaned_inc_b.id] = cleaned_inc_b
            result.updated_boards += 1
            result.imported_hashes[key] = inc_hash
            boards_changed = True
        elif choice == "keep_copy":
            # Take remote under original ID and keep local board as a copy with a fresh ID
            copy_id = _models.gen_id()
            local_copy = _models.Board(
                id=copy_id,
                title=f"{loc_b.title or 'Board'} (lokale Kopie)",
                description=loc_b.description,
                items=[
                    _models.BoardItem(
                        id=_models.gen_id(),
                        board_id=copy_id,
                        prompt_id=it.prompt_id,
                        version_id=it.version_id,
                        created_at=it.created_at,
                    )
                    for it in loc_b.items
                ],
                created_at=_models.now_iso(),
            )
            idx = next(i for i, b in enumerate(local_boards) if b.id == cleaned_inc_b.id)
            local_boards[idx] = cleaned_inc_b
            local_boards.append(local_copy)
            board_by_id[cleaned_inc_b.id] = cleaned_inc_b
            board_by_id[copy_id] = local_copy
            result.updated_boards += 1
            result.added_boards += 1
            result.imported_hashes[key] = inc_hash
            boards_changed = True
        else:
            result.unchanged += 1

    # 3. Persist prompts BEFORE boards (Konzept §7.2 Punkt 3)
    if prompts_changed:
        storage.save_prompts(local_prompts)
    if boards_changed:
        storage.save_boards(local_boards)

    return result
