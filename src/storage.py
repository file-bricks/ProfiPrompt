# storage.py
import json
import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple
from models import Prompt, Version, Board, BoardItem, prompt_from_dict, prompt_to_dict, board_from_dict, board_to_dict, gen_id, now_iso

class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.data_dir / "prompts.json"
        self.boards_file = self.data_dir / "boards.json"
        self._lock = threading.Lock()
        self._ensure_files()

    def _ensure_files(self):
        if not self.prompts_file.exists():
            self.prompts_file.write_text(json.dumps({"prompts": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.boards_file.exists():
            self.boards_file.write_text(json.dumps({"boards": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Prompts ---
    def load_prompts(self) -> List[Prompt]:
        # Bugsweep 28 BUG-PS02: OSError (inkl. FileNotFoundError/PermissionError) war
        # ungefangen — z.B. wenn prompts.json zwischen _ensure_files und dem Lesen
        # gelöscht wird (fehlgeschlagener .tmp-Rename, OneDrive-Lock). UnicodeDecodeError
        # ist bereits via ValueError abgedeckt; OSError fehlte komplett.
        try:
            data = json.loads(self.prompts_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            data = {}
        return [prompt_from_dict(p) for p in data.get("prompts", [])]
    
    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        for p in self.load_prompts():
            if p.id == prompt_id:
                return p
        return None


    def _atomic_write(self, target: Path, data: dict):
        """Schreibt Daten atomar: erst in .tmp, dann rename. Thread-safe durch Lock."""
        tmp = target.with_suffix(".tmp")
        text = json.dumps(data, ensure_ascii=False, indent=2)
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)

    def save_prompts(self, prompts: List[Prompt]):
        data = {"prompts": [prompt_to_dict(p) for p in prompts]}
        with self._lock:
            self._atomic_write(self.prompts_file, data)

    def upsert_prompt(self, prompt: Prompt):
        prompts = self.load_prompts()
        idx = next((i for i, p in enumerate(prompts) if p.id == prompt.id), -1)
        if idx >= 0:
            prompts[idx] = prompt
        else:
            prompts.append(prompt)
        self.save_prompts(prompts)

    def delete_prompt(self, prompt_id: str):
        prompts = [p for p in self.load_prompts() if p.id != prompt_id]
        self.save_prompts(prompts)
        # Bugsweep 2026-09-18 BUG-VD03: Verwaiste Board-Referenzen entfernen
        boards = self.load_boards()
        changed = False
        for b in boards:
            orig_len = len(b.items)
            b.items = [it for it in b.items if it.prompt_id != prompt_id]
            if len(b.items) != orig_len:
                changed = True
        if changed:
            self.save_boards(boards)

    def add_version(self, prompt_id: str, version: Version):
        prompts = self.load_prompts()
        for p in prompts:
            if p.id == prompt_id:
                p.versions.append(version)
                p.updated_at = now_iso()
                break
        self.save_prompts(prompts)

    def upsert_version(self, prompt_id: str, version: Version) -> bool:
        """Aktualisiert eine existierende Version oder fügt sie hinzu (BUG-VD02)."""
        prompts = self.load_prompts()
        for p in prompts:
            if p.id == prompt_id:
                idx = next((i for i, v in enumerate(p.versions) if v.id == version.id), -1)
                if idx >= 0:
                    p.versions[idx] = version
                else:
                    p.versions.append(version)
                p.updated_at = now_iso()
                self.save_prompts(prompts)
                return True
        return False

    def delete_version(self, prompt_id: str, version_id: str) -> bool:
        """Löscht eine Version und bereinigt zugehörige BoardItems (BUG-VD03)."""
        prompts = self.load_prompts()
        found = False
        for p in prompts:
            if p.id == prompt_id:
                p.versions = [v for v in p.versions if v.id != version_id]
                p.updated_at = now_iso()
                found = True
                break
        if not found:
            return False
        self.save_prompts(prompts)
        boards = self.load_boards()
        changed = False
        for b in boards:
            orig_len = len(b.items)
            b.items = [it for it in b.items if not (it.prompt_id == prompt_id and it.version_id == version_id)]
            if len(b.items) != orig_len:
                changed = True
        if changed:
            self.save_boards(boards)
        return True

    def get_version(self, prompt_id: str, version_id: str) -> Optional[Version]:
        p = self.get_prompt(prompt_id)
        if not p:
            return None
        return next((v for v in p.versions if v.id == version_id), None)

    def next_version_number(self, prompt_id: str) -> int:
        p = self.get_prompt(prompt_id)
        if not p or not p.versions:
            return 1
        nums = [
            v.version_number
            for v in p.versions
            if v is not None and getattr(v, "version_number", None) is not None
        ]
        return (max(nums) + 1) if nums else 1

    # --- Boards ---
    def load_boards(self) -> List[Board]:
        # Bugsweep 28 BUG-PS02: identisch zu load_prompts — OSError ungefangen.
        try:
            data = json.loads(self.boards_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            data = {}
        return [board_from_dict(b) for b in data.get("boards", [])]

    def save_boards(self, boards: List[Board]):
        data = {"boards": [board_to_dict(b) for b in boards]}
        with self._lock:
            self._atomic_write(self.boards_file, data)

    def upsert_board(self, board: Board):
        boards = self.load_boards()
        idx = next((i for i, b in enumerate(boards) if b.id == board.id), -1)
        if idx >= 0:
            boards[idx] = board
        else:
            boards.append(board)
        self.save_boards(boards)

    def delete_board(self, board_id: str):
        boards = [b for b in self.load_boards() if b.id != board_id]
        self.save_boards(boards)

    def add_item_to_board(self, board_id: str, prompt_id: str, version_id: Optional[str] = None, validate_prompt: bool = False) -> Tuple[bool, Optional[str]]:
        if not prompt_id or not str(prompt_id).strip():
            return False, None
        if validate_prompt:
            p = self.get_prompt(prompt_id)
            if not p:
                return False, None
            if version_id and not any(v.id == version_id for v in p.versions):
                return False, None

        boards = self.load_boards()
        for b in boards:
            if b.id == board_id:
                # Verhindere Duplikate
                for it in b.items:
                    if it.prompt_id == prompt_id and it.version_id == version_id:
                        return False, None
                item = BoardItem(id=gen_id(), board_id=board_id, prompt_id=prompt_id, version_id=version_id)
                b.items.append(item)
                self.save_boards(boards)
                return True, item.id
        return False, None
