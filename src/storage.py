# storage.py
import json
import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple
from models import Prompt, Version, Board, BoardItem, prompt_from_dict, prompt_to_dict, board_from_dict, gen_id, now_iso

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
        data = json.loads(self.prompts_file.read_text(encoding="utf-8"))
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

    def add_version(self, prompt_id: str, version: Version):
        prompts = self.load_prompts()
        for p in prompts:
            if p.id == prompt_id:
                p.versions.append(version)
                p.updated_at = now_iso()
                break
        self.save_prompts(prompts)

    def get_version(self, prompt_id: str, version_id: str) -> Optional[Version]:
        p = self.get_prompt(prompt_id)
        if not p:
            return None
        return next((v for v in p.versions if v.id == version_id), None)

    def next_version_number(self, prompt_id: str) -> int:
        p = self.get_prompt(prompt_id)
        if not p or not p.versions:
            return 1
        return max(v.version_number for v in p.versions) + 1

    # --- Boards ---
    def load_boards(self) -> List[Board]:
        data = json.loads(self.boards_file.read_text(encoding="utf-8"))
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

    def add_item_to_board(self, board_id: str, prompt_id: str, version_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
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
