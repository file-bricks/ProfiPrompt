# models.py

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class CopyMode(str, Enum):
    TITLE  = "title"
    TEXT   = "text"
    RESULT = "result"
    ALL    = "all"


def now_iso() -> str:
    """Returns current UTC time in ISO8601 format."""
    return datetime.now(tz=__import__('datetime').timezone.utc).isoformat()


def gen_id() -> str:
    """Generates a new unique identifier."""
    return uuid.uuid4().hex


@dataclass
class Version:
    id: str
    prompt_id: str
    version_number: int
    title: str
    text: str
    result: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass
class Prompt:
    id: str
    title: str
    purpose: str
    text: str
    tags: List[str] = field(default_factory=list)
    last_result: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    versions: List[Version] = field(default_factory=list)


@dataclass
class BoardItem:
    id: str
    board_id: str
    prompt_id: str
    version_id: Optional[str] = None   # None => Haupt-Prompt
    created_at: str = field(default_factory=now_iso)


@dataclass
class Board:
    id: str
    title: str
    description: str = ""
    items: List[BoardItem] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


# -------------------------------------------------------------------
# Serialization helpers

def version_to_dict(v: Version) -> Dict[str, Any]:
    """Convert a Version to its dict representation."""
    return asdict(v)


def prompt_to_dict(p: Prompt) -> Dict[str, Any]:
    """Convert a Prompt (including nested versions) to its dict representation."""
    return asdict(p)


def boarditem_to_dict(item: BoardItem) -> Dict[str, Any]:
    """Convert a BoardItem to its dict representation."""
    return asdict(item)


def board_to_dict(b: Board) -> Dict[str, Any]:
    """Convert a Board (including nested items) to its dict representation."""
    return asdict(b)


def prompt_from_dict(d: Dict[str, Any]) -> Prompt:
    """Reconstruct a Prompt (and its Versions) from a dict."""
    versions_data = d.get("versions", [])
    versions = [Version(**v) for v in versions_data]
    return Prompt(
        id=d["id"],
        title=d["title"],
        purpose=d.get("purpose", ""),
        text=d.get("text", ""),
        tags=d.get("tags", []),
        last_result=d.get("last_result", ""),
        created_at=d.get("created_at", now_iso()),
        updated_at=d.get("updated_at", now_iso()),
        versions=versions
    )


def boarditem_from_dict(d: Dict[str, Any]) -> BoardItem:
    """Reconstruct a BoardItem from a dict."""
    return BoardItem(**d)


def board_from_dict(d: Dict[str, Any]) -> Board:
    """Reconstruct a Board (and its BoardItems) from a dict."""
    items_data = d.get("items", [])
    items = [BoardItem(**i) for i in items_data]
    return Board(
        id=d["id"],
        title=d["title"],
        description=d.get("description", ""),
        items=items,
        created_at=d.get("created_at", now_iso())
    )
