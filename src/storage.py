# storage.py
import json
import threading
from functools import wraps
from pathlib import Path
from typing import List, Optional, Tuple
from atomic_io import atomic_write_json
from models import Prompt, Version, Board, BoardItem, prompt_from_dict, prompt_to_dict, board_from_dict, board_to_dict, gen_id, now_iso, normalize_item_color

class StorageReadError(OSError):
    """A library could not be read completely; a mutation must not replace it."""

    def __init__(self, path: Path):
        super().__init__(f"Bibliotheksdatei konnte nicht vollständig gelesen werden: {path}")


def _locked(method):
    @wraps(method)
    def run(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return run


def _validate_records(data, key, nested_key):
    if not isinstance(data, dict) or key not in data or not isinstance(data[key], list):
        raise ValueError(f"Ungültige Bibliotheksstruktur: {key}")
    for record in data[key]:
        if not isinstance(record, dict):
            raise ValueError(f"Ungültiger Eintrag: {key}")
        nested = record.get(nested_key, [])
        # Existing models support null placeholders as empty entries. Reject
        # informative malformed entries rather than silently dropping them.
        if nested is None and nested_key in ("versions", "items"):
            nested = []
        if not isinstance(nested, list) or any(item is not None and not isinstance(item, dict) for item in nested):
            raise ValueError(f"Ungültige Bibliotheksstruktur: {nested_key}")


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.data_dir / "prompts.json"
        self.boards_file = self.data_dir / "boards.json"
        self._lock = threading.RLock()
        self._ensure_files()

    def _ensure_files(self):
        if not self.prompts_file.exists():
            self._atomic_write(self.prompts_file, {"prompts": []})
        if not self.boards_file.exists():
            self._atomic_write(self.boards_file, {"boards": []})

    # --- Prompts ---
    def load_prompts(self, *, strict: bool = False) -> List[Prompt]:
        # Bugsweep 28 BUG-PS02: OSError (inkl. FileNotFoundError/PermissionError) war
        # ungefangen — z.B. wenn prompts.json zwischen _ensure_files und dem Lesen
        # gelöscht wird (fehlgeschlagener .tmp-Rename, OneDrive-Lock). UnicodeDecodeError
        # ist bereits via ValueError abgedeckt; OSError fehlte komplett.
        try:
            data = json.loads(self.prompts_file.read_text(encoding="utf-8"))
            if strict:
                _validate_records(data, "prompts", "versions")
            return [prompt_from_dict(p) for p in data.get("prompts", [])]
        except (json.JSONDecodeError, ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            if strict:
                raise StorageReadError(self.prompts_file) from exc
            return []
    
    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        for p in self.load_prompts():
            if p.id == prompt_id:
                return p
        return None


    def _atomic_write(self, target: Path, data: dict):
        """Schreibt Daten atomar: erst in eindeutiges .tmp, dann fsync & replace. Thread-safe durch Lock."""
        atomic_write_json(target, data, indent=2)

    def save_prompts(self, prompts: List[Prompt]):
        with self._lock:
            self.load_prompts(strict=True)
            self._write_prompts(prompts)

    def _write_prompts(self, prompts: List[Prompt]):
        """Private write: caller holds the lock and has read all required inputs."""
        self._atomic_write(self.prompts_file, {"prompts": [prompt_to_dict(p) for p in prompts]})

    @_locked
    def upsert_prompt(self, prompt: Prompt):
        prompts = self.load_prompts(strict=True)
        idx = next((i for i, p in enumerate(prompts) if p.id == prompt.id), -1)
        if idx >= 0:
            prompts[idx] = prompt
        else:
            prompts.append(prompt)
        self._write_prompts(prompts)

    @_locked
    def delete_prompt(self, prompt_id: str):
        prompts = [p for p in self.load_prompts(strict=True) if p.id != prompt_id]
        boards = self.load_boards(strict=True)
        self._write_prompts(prompts)
        # Bugsweep 2026-09-18 BUG-VD03: Verwaiste Board-Referenzen entfernen
        changed = False
        for b in boards:
            orig_len = len(b.items)
            b.items = [it for it in b.items if it and it.prompt_id != prompt_id]
            if len(b.items) != orig_len:
                changed = True
        if changed:
            self._write_boards(boards)

    @_locked
    def add_version(self, prompt_id: str, version: Version) -> bool:
        prompts = self.load_prompts(strict=True)
        for p in prompts:
            if p and getattr(p, "id", None) == prompt_id:
                if getattr(p, "versions", None) is None:
                    p.versions = []
                p.versions.append(version)
                p.updated_at = now_iso()
                self._write_prompts(prompts)
                return True
        return False

    @_locked
    def upsert_version(self, prompt_id: str, version: Version) -> bool:
        """Aktualisiert eine existierende Version oder fügt sie hinzu (BUG-VD02)."""
        prompts = self.load_prompts(strict=True)
        for p in prompts:
            if p and getattr(p, "id", None) == prompt_id:
                if getattr(p, "versions", None) is None:
                    p.versions = []
                idx = next((i for i, v in enumerate(p.versions) if v and getattr(v, "id", None) == version.id), -1)
                if idx >= 0:
                    p.versions[idx] = version
                else:
                    p.versions.append(version)
                p.updated_at = now_iso()
                self._write_prompts(prompts)
                return True
        return False

    @_locked
    def delete_version(self, prompt_id: str, version_id: str) -> bool:
        """Löscht eine Version und bereinigt zugehörige BoardItems (BUG-VD03)."""
        prompts = self.load_prompts(strict=True)
        found = False
        for p in prompts:
            if p and getattr(p, "id", None) == prompt_id:
                p.versions = [v for v in (getattr(p, "versions", []) or []) if v and getattr(v, "id", None) != version_id]
                p.updated_at = now_iso()
                found = True
                break
        if not found:
            return False
        boards = self.load_boards(strict=True)
        self._write_prompts(prompts)
        changed = False
        for b in boards:
            orig_len = len(b.items)
            b.items = [it for it in (getattr(b, "items", []) or []) if not (it and getattr(it, "prompt_id", None) == prompt_id and getattr(it, "version_id", None) == version_id)]
            if len(b.items) != orig_len:
                changed = True
        if changed:
            self._write_boards(boards)
        return True

    def get_version(self, prompt_id: str, version_id: str) -> Optional[Version]:
        p = self.get_prompt(prompt_id)
        if not p:
            return None
        return next((v for v in (getattr(p, "versions", []) or []) if v is not None and getattr(v, "id", None) == version_id), None)

    def next_version_number(self, prompt_id: str) -> int:
        p = next((p for p in (self.load_prompts(strict=True) or []) if p and getattr(p, "id", None) == prompt_id), None)
        if not p or not getattr(p, "versions", None):
            return 1
        nums = [
            v.version_number
            for v in (p.versions or [])
            if v is not None and getattr(v, "version_number", None) is not None
        ]
        return (max(nums) + 1) if nums else 1

    # --- Boards ---
    def load_boards(self, *, strict: bool = False) -> List[Board]:
        # Bugsweep 28 BUG-PS02: identisch zu load_prompts — OSError ungefangen.
        try:
            data = json.loads(self.boards_file.read_text(encoding="utf-8"))
            if strict:
                _validate_records(data, "boards", "items")
            return [board_from_dict(b) for b in data.get("boards", [])]
        except (json.JSONDecodeError, ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            if strict:
                raise StorageReadError(self.boards_file) from exc
            return []

    @_locked
    def load_library(self) -> Tuple[List[Prompt], List[Board]]:
        """Read both library files without hiding errors, e.g. before exporting."""
        return self.load_prompts(strict=True), self.load_boards(strict=True)

    def save_boards(self, boards: List[Board]):
        with self._lock:
            self.load_boards(strict=True)
            self._write_boards(boards)

    def _write_boards(self, boards: List[Board]):
        """Private write: caller holds the lock and has read all required inputs."""
        self._atomic_write(self.boards_file, {"boards": [board_to_dict(b) for b in boards]})

    @_locked
    def upsert_board(self, board: Board):
        boards = self.load_boards(strict=True)
        idx = next((i for i, b in enumerate(boards) if b.id == board.id), -1)
        if idx >= 0:
            boards[idx] = board
        else:
            boards.append(board)
        self._write_boards(boards)

    @_locked
    def delete_board(self, board_id: str):
        boards = [b for b in self.load_boards(strict=True) if b.id != board_id]
        self._write_boards(boards)

    @_locked
    def add_item_to_board(self, board_id: str, prompt_id: str, version_id: Optional[str] = None, validate_prompt: bool = False,
                          color: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        if not prompt_id or not str(prompt_id).strip():
            return False, None
        if validate_prompt:
            p = next((p for p in (self.load_prompts(strict=True) or []) if p and getattr(p, "id", None) == prompt_id), None)
            if not p:
                return False, None
            if version_id and not any(v and getattr(v, "id", None) == version_id for v in (getattr(p, "versions", []) or [])):
                return False, None

        boards = self.load_boards(strict=True)
        for b in boards:
            if b and getattr(b, "id", None) == board_id:
                if getattr(b, "items", None) is None:
                    b.items = []
                # Verhindere Duplikate
                for it in b.items:
                    if it and getattr(it, "prompt_id", None) == prompt_id and getattr(it, "version_id", None) == version_id:
                        return False, None
                item = BoardItem(id=gen_id(), board_id=board_id, prompt_id=prompt_id, version_id=version_id,
                                 color=normalize_item_color(color))
                b.items.append(item)
                self._write_boards(boards)
                return True, item.id
        return False, None

    @_locked
    def remove_item_from_board(self, board_id: str, prompt_id: str, version_id: Optional[str] = None) -> bool:
        boards = self.load_boards(strict=True)
        for board in boards:
            if board.id == board_id:
                for index, item in enumerate(board.items):
                    if item and item.prompt_id == prompt_id and item.version_id == version_id:
                        board.items.pop(index)
                        self._write_boards(boards)
                        return True
        return False

    # --- Kachel zwischen Boards senden / duplizieren, Kachelfarbe ---
    @staticmethod
    def _find_item(board: Board, prompt_id: str, version_id: Optional[str]) -> int:
        return next((i for i, it in enumerate(getattr(board, "items", None) or [])
                     if it and it.prompt_id == prompt_id and it.version_id == version_id), -1)

    @_locked
    def transfer_item(self, source_board_id: str, target_board_id: str, prompt_id: str,
                      version_id: Optional[str] = None, *, move: bool = False) -> Tuple[bool, str]:
        """Kopiert (move=False) oder verschiebt (move=True) eine Kachel auf ein anderes Board.

        Die individuelle Kachelfarbe wird mitgenommen. Beide Boards werden in EINEM
        atomaren Schreibvorgang aktualisiert, damit ein Verschieben nie zu einer
        verlorenen oder doppelten Kachel fuehrt.

        Rueckgabe: (Erfolg, Grund) mit Grund in
        'ok' | 'same_board' | 'source_missing' | 'target_missing' | 'duplicate'.
        """
        if source_board_id == target_board_id:
            return False, "same_board"
        boards = self.load_boards(strict=True)
        src = next((b for b in boards if b and b.id == source_board_id), None)
        dst = next((b for b in boards if b and b.id == target_board_id), None)
        if src is None:
            return False, "source_missing"
        if dst is None:
            return False, "target_missing"
        idx = self._find_item(src, prompt_id, version_id)
        if idx < 0:
            return False, "source_missing"
        if dst.items is None:
            dst.items = []
        if self._find_item(dst, prompt_id, version_id) >= 0:
            return False, "duplicate"
        original = src.items[idx]
        dst.items.append(BoardItem(id=gen_id(), board_id=dst.id, prompt_id=prompt_id,
                                   version_id=version_id, color=original.color))
        if move:
            src.items.pop(idx)
        self._write_boards(boards)
        return True, "ok"

    def copy_item_to_board(self, source_board_id: str, target_board_id: str, prompt_id: str,
                           version_id: Optional[str] = None) -> Tuple[bool, str]:
        return self.transfer_item(source_board_id, target_board_id, prompt_id, version_id, move=False)

    def move_item_to_board(self, source_board_id: str, target_board_id: str, prompt_id: str,
                           version_id: Optional[str] = None) -> Tuple[bool, str]:
        return self.transfer_item(source_board_id, target_board_id, prompt_id, version_id, move=True)

    @_locked
    def set_item_color(self, board_id: str, prompt_id: str, version_id: Optional[str] = None,
                       color: Optional[str] = None) -> bool:
        """Setzt (oder entfernt mit color=None) die individuelle Farbe einer Kachel."""
        new_color = normalize_item_color(color)
        if color is not None and new_color is None:
            return False
        boards = self.load_boards(strict=True)
        for board in boards:
            if board and board.id == board_id:
                idx = self._find_item(board, prompt_id, version_id)
                if idx < 0:
                    return False
                board.items[idx].color = new_color
                self._write_boards(boards)
                return True
        return False

    @_locked
    def rename_board(self, board_id: str, title: str) -> bool:
        title = (title or "").strip()
        if not title:
            return False
        boards = self.load_boards(strict=True)
        for board in boards:
            if board and board.id == board_id:
                board.title = title
                self._write_boards(boards)
                return True
        return False
