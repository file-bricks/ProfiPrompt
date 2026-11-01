# models.py

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum
import re


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
    color: Optional[str] = None        # individuelle Kachelfarbe '#RRGGBB'; None => Standardfarbe


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


def _normalize_tags(raw: Any) -> List[str]:
    """Normalisiert Tags robust zu einer Liste getrimmter, nicht-leerer Strings.

    Unterstützt kommagetrennte Strings ('coding, python') sowie Listen/Iterables
    mit beliebigen Typen, filtert None-Werte und Leerstrings aus.
    """
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, (list, tuple, set)):
        return [str(t).strip() for t in raw if t is not None and str(t).strip()]
    return []


def version_from_dict(v: Dict[str, Any], default_prompt_id: str = "") -> Version:
    """Reconstruct a Version from a dict (feldweise, schema-drift-robust).

    Bugsweep 2026-11-01: Defensive .get()-Defaults mit gen_id() für fehlende/leere IDs
    und default_prompt_id-Vererbung verhindern KeyError bei unvollständigen Version-Dicts.
    """
    return Version(
        id=v.get("id") or gen_id(),
        prompt_id=v.get("prompt_id") or default_prompt_id,
        version_number=v.get("version_number") or 0,
        title=v.get("title") or "",
        text=v.get("text") or "",
        result=v.get("result") or "",
        tags=_normalize_tags(v.get("tags")),
        created_at=v.get("created_at") or now_iso(),
        updated_at=v.get("updated_at") or now_iso(),
    )


def prompt_from_dict(d: Dict[str, Any]) -> Prompt:
    """Reconstruct a Prompt (and its Versions) from a dict (feldweise, schema-drift-robust).

    Bugsweep 28 BUG-PS01 / Bugsweep 2026-11-01: title=d["title"] warf KeyError bei alten/fremden
    JSON-Exporten ohne 'title'-Feld und riss den gesamten load_prompts mit. Fehlendes 'id' wirft
    weiterhin KeyError (Zombie-Schutz), aber explizites id=None oder Leerstring wird defensiv
    durch gen_id() ersetzt. default_prompt_id-Vererbung an verschachtelte Versionen und robuste
    Tag-Normalisierung (_normalize_tags).
    """
    if "id" not in d:
        raise KeyError("id")
    prompt_id = d["id"] or gen_id()
    versions_data = d.get("versions") or []
    versions = [version_from_dict(v, default_prompt_id=prompt_id) for v in versions_data if isinstance(v, dict)]
    return Prompt(
        id=prompt_id,
        title=d.get("title") or "",
        purpose=d.get("purpose") or "",
        text=d.get("text") or "",
        tags=_normalize_tags(d.get("tags")),
        last_result=d.get("last_result") or "",
        created_at=d.get("created_at") or now_iso(),
        updated_at=d.get("updated_at") or now_iso(),
        versions=versions
    )


_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_item_color(value: Any) -> Optional[str]:
    """Gibt eine gueltige '#RRGGBB'-Farbe (Grossbuchstaben) oder None zurueck.

    Board-JSONs koennen von Hand oder fremden Tools stammen; nur strikt valide
    Hex-Farben gelangen ins Kachel-Stylesheet (keine QSS-Injektion, kein Crash).
    """
    if isinstance(value, str) and _HEX_COLOR_RE.match(value.strip()):
        return value.strip().upper()
    return None


def boarditem_from_dict(d: Dict[str, Any]) -> BoardItem:
    """Reconstruct a BoardItem from a dict (feldweise, schema-drift-robust)."""
    # Bugsweep 19/28 BUG-BM01: .get()-Defaults für id, board_id, prompt_id verhindern KeyError bei schema-drift
    return BoardItem(
        id=d.get("id") or gen_id(),
        board_id=d.get("board_id") or "",
        prompt_id=d.get("prompt_id") or "",
        version_id=d.get("version_id"),
        created_at=d.get("created_at") or now_iso(),
        color=normalize_item_color(d.get("color")),
    )


def board_from_dict(d: Dict[str, Any]) -> Board:
    """Reconstruct a Board (and its BoardItems) from a dict (feldweise, schema-drift-robust).

    Bugsweep 28 BUG-BM02: title=d["title"] und id=d["id"] warfen KeyError bei alten/fremden
    Board-JSONs ohne 'title'/'id' und rissen den gesamten load_boards() mit.
    Bugsweep 2026-10-03 BUG-BM05: items=None in JSON führte zu TypeError in List-Comprehension;
    jetzt über .get('items') or [] defensiv abgefangen und None-Felder mit sauberen Defaults belegt.
    """
    items_data = d.get("items") or []
    items = [boarditem_from_dict(i) for i in items_data if isinstance(i, dict)]
    return Board(
        id=d.get("id") or gen_id(),
        title=d.get("title") or "",
        description=d.get("description") or "",
        items=items,
        created_at=d.get("created_at") or now_iso()
    )

