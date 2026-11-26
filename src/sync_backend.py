"""Synchronization backends for ProfiPrompt Desktop (Off, Server, File-Slot).

Implements:
- ``NullBackend`` (mode ``"off"``, default, zero network/file I/O)
- ``ServerBackend`` (mode ``"server"``, Python stdlib ``urllib.request`` against
  ``prompt-sync-server`` with separate ``prompt`` and ``board`` kinds, ETag/304,
  409 Conflict three-way resolution, 410 Gone reset, offline queue, TLS guard,
  optional keyring + 0600 local token fallback)
- ``FileSlotBackend`` (mode ``"file"``, .SYNC-style single-writer host slots
  ``<sync_dir>/profiprompt/<HOST>/profiprompt@<HOST>.json``, mutual visibility
  with ``profiprompt-browser`` slots, A7 conflict-copy filtering, per-slot mode
  ``never`` / ``once`` / ``on_start``, local ``deleted_ids`` blocklist)
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import platform
import re
import stat
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from library_export import APP_VERSION, SCHEMA_VERSION, build_library_export
from library_import import (
    ConflictChoice,
    ImportConflict,
    canonical_board_hash,
    canonical_prompt_hash,
    merge_library_payload,
)
from models import (
    Board,
    BoardItem,
    Prompt,
    Version,
    board_from_dict,
    board_to_dict,
    gen_id,
    now_iso,
    prompt_from_dict,
    prompt_to_dict,
)

logger = logging.getLogger(__name__)

try:
    import keyring as _keyring_mod  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _keyring_mod = None

SYNC_MODES = ("off", "file", "server")
SLOT_IMPORT_MODES = ("never", "once", "on_start")
DEFAULT_SYNC_MODE = "off"
DEFAULT_NAMESPACE = "profiprompt"
DEFAULT_HTTP_TIMEOUT = 10.0

NAMESPACE_RE = re.compile(r"\A[a-z0-9_-]{1,32}\Z")
HOST_CLEAN_RE = re.compile(r"[^A-Za-z0-9._-]+")
TAILSCALE_IPV4_NET = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_IPV6_NET = ipaddress.ip_network("fd7a:115c:a1e0::/48")
REDIRECT_STATUS_CODES = frozenset({300, 301, 302, 303, 305, 306, 307, 308})
VISIBLE_SLOT_APPS = ("profiprompt", "profiprompt-browser")


class SyncError(Exception):
    """Base error for synchronization failures."""


class SyncTransportError(SyncError):
    """Raised when transport security rules or network calls fail."""


class SyncAuthError(SyncError):
    """Raised when the sync server rejects authentication or write permissions."""


def get_host_slot_name() -> str:
    """Read local hostname from OS, normalized to [A-Za-z0-9._-] uppercase (fail-closed)."""
    raw = (platform.node() or os.environ.get("COMPUTERNAME") or "").strip()
    cleaned = HOST_CLEAN_RE.sub("_", raw).strip("._-").upper()
    if not cleaned:
        raise SyncError("Hostname konnte nicht aus dem Betriebssystem ermittelt werden (fail-closed).")
    return cleaned


def validate_namespace(namespace: str) -> str:
    cleaned = (namespace or "").strip()
    if not cleaned:
        return DEFAULT_NAMESPACE
    if not NAMESPACE_RE.fullmatch(cleaned):
        raise ValueError(f"Ungültiger Namespace '{namespace}'. Erwartet [a-z0-9_-] (1..32 Zeichen).")
    return cleaned


def _unwrap_ipv4_mapped(addr: ipaddress.IPv4Address | ipaddress.IPv6Address):
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower().strip("[]")
    if normalized == "localhost":
        return True
    try:
        addr = _unwrap_ipv4_mapped(ipaddress.ip_address(normalized))
    except ValueError:
        return False
    return bool(addr.is_loopback)


def is_tailscale_host(host: str) -> bool:
    normalized = (host or "").strip().lower().strip("[]")
    try:
        addr = _unwrap_ipv4_mapped(ipaddress.ip_address(normalized))
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv4Address):
        return addr in TAILSCALE_IPV4_NET
    return addr in TAILSCALE_IPV6_NET


def validate_server_url(raw_url: str) -> str:
    """Enforce TLS outside loopback & private Tailscale addresses."""
    cleaned = (raw_url or "").strip().rstrip("/")
    if not cleaned:
        raise SyncTransportError("Server-URL darf nicht leer sein.")
    if any(ord(ch) <= 32 or ord(ch) >= 127 or ch == "\\" for ch in cleaned):
        raise SyncTransportError("Server-URL enthält ungültige Zeichen oder Leerzeichen.")
    parsed = urllib_parse.urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise SyncTransportError("Server-URL muss mit http:// oder https:// beginnen.")
    host = parsed.hostname or ""
    if not host:
        raise SyncTransportError("Server-URL enthält keinen Hostnamen.")
    if parsed.username or parsed.password:
        raise SyncTransportError("Zugangsdaten dürfen nicht in der URL stehen.")
    if parsed.params or parsed.query or parsed.fragment:
        raise SyncTransportError("Server-URL darf keine Query-Parameter oder Fragmente enthalten.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise SyncTransportError("Server-URL enthält einen ungültigen Port.") from exc
    if scheme == "http" and not (is_loopback_host(host) or is_tailscale_host(host)):
        raise SyncTransportError(
            "Unverschlüsseltes http:// ist nur für Loopback (127.0.0.1 / localhost) "
            "oder Tailscale (100.64.0.0/10) zulässig. Für andere Ziele bitte https:// nutzen."
        )
    return cleaned


def _atomic_write_json(target: Path, data: Dict[str, Any], *, restricted: bool = False) -> None:
    target = Path(target)
    if target.is_symlink() or (target.exists() and target.is_dir()):
        raise OSError(f"Ziel ist Symlink oder Verzeichnis: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    mode = 0o600 if restricted else 0o644
    fd = os.open(str(tmp), flags, mode)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)

    if restricted:
        try:
            os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    last_err: Optional[OSError] = None
    for attempt in range(5):
        try:
            os.replace(tmp, target)
            last_err = None
            break
        except PermissionError as exc:
            last_err = exc
            time.sleep(0.05 * (attempt + 1))
        except OSError as exc:
            last_err = exc
            break
    if last_err is not None:
        tmp.unlink(missing_ok=True)
        raise last_err


# ---------------------------------------------------------------------------
# Token storage (optional keyring + 0600 local fallback outside sync folders)
# ---------------------------------------------------------------------------


def default_token_file_path() -> Path:
    if os.name == "nt":
        base_raw = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(base_raw) if (base_raw and Path(base_raw).is_absolute()) else (Path.home() / "AppData" / "Local")
        return base / "PromptManager" / "sync_token.json"
    xdg_raw = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_raw) if (xdg_raw and Path(xdg_raw).is_absolute()) else (Path.home() / ".config")
    return base / "profiprompt" / "sync_token.json"


class TokenStorage:
    SERVICE_NAME = "ProfiPrompt"
    ACCOUNT_NAME = "sync_api_token"

    def __init__(self, fallback_path: Optional[Path] = None, *, keyring_backend: Any = None) -> None:
        self.fallback_path = Path(fallback_path) if fallback_path is not None else default_token_file_path()
        self._keyring_override = keyring_backend
        self._lock = threading.RLock()

    def _active_keyring(self) -> Any:
        if self._keyring_override is not None:
            return self._keyring_override
        if os.environ.get("PROFIPROMPT_DISABLE_KEYRING", "").strip() in ("1", "true", "yes"):
            return None
        return _keyring_mod

    def get_token(self) -> str:
        with self._lock:
            kr = self._active_keyring()
            if kr is not None:
                try:
                    secret = kr.get_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                    if isinstance(secret, str) and secret.strip():
                        return secret.strip()
                except Exception:
                    pass
            if self.fallback_path.is_symlink() or not self.fallback_path.is_file():
                return ""
            try:
                raw = json.loads(self.fallback_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return ""
            token = raw.get("token", "") if isinstance(raw, dict) else ""
            return token.strip() if isinstance(token, str) else ""

    def set_token(self, token: str) -> None:
        with self._lock:
            cleaned = (token or "").strip()
            if not cleaned:
                self.clear_token()
                return
            kr = self._active_keyring()
            if kr is not None:
                try:
                    kr.set_password(self.SERVICE_NAME, self.ACCOUNT_NAME, cleaned)
                    self.fallback_path.unlink(missing_ok=True)
                    return
                except Exception:
                    pass
            _atomic_write_json(self.fallback_path, {"version": 1, "token": cleaned}, restricted=True)

    def clear_token(self) -> None:
        with self._lock:
            kr = self._active_keyring()
            if kr is not None:
                try:
                    kr.delete_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
                except Exception:
                    pass
            self.fallback_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Sync state & protocol results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectionStatus:
    ok: bool
    latency_ms: float
    detail: str
    library_rev: Optional[int] = None
    item_count: Optional[int] = None


@dataclass
class PullResult:
    upserts: int = 0
    tombstones: int = 0
    conflicts: List[ImportConflict] = field(default_factory=list)
    cursor: int = 0
    not_modified: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class PushResult:
    applied_revs: Dict[str, int] = field(default_factory=dict)
    conflicts: List[ImportConflict] = field(default_factory=list)
    queued_offline: int = 0
    library_rev: Optional[int] = None


@dataclass(frozen=True)
class ForeignSlotInfo:
    slot_key: str  # e.g. "profiprompt@WORKSTATION-LG"
    app: str
    host: str
    path: Path
    updated_at: str
    item_count: int
    import_mode: str = "never"


class SyncStateStore:
    """Manages local ``sync_state.json`` and ``sync_queue.json`` in data_dir (never exported)."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.state_path = self.data_dir / "sync_state.json"
        self.queue_path = self.data_dir / "sync_queue.json"
        self._lock = threading.RLock()

    def load_state(self) -> Dict[str, Any]:
        with self._lock:
            default: Dict[str, Any] = {
                "library_rev": 0,
                "etag": "",
                "item_revs": {},          # "prompt:<id>" | "board:<id>" -> int
                "item_hashes": {},        # "prompt:<id>" | "board:<id>" -> sha256
                "deleted_ids": [],        # local blocklist for file mode
                "slot_modes": {},         # slot_key -> never|once|on_start
                "slot_cursors": {},       # slot_key -> last updated_at
                "slot_item_hashes": {},   # slot_key -> { "prompt:<id>": sha256 }
                "last_exported_hash": "",
                "last_sync_at": "",
            }
            if not self.state_path.is_file():
                return default
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                return default
            if isinstance(raw, dict):
                default.update(raw)
            return default

    def save_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            _atomic_write_json(self.state_path, state)

    def load_queue(self) -> Dict[str, Dict[str, Any]]:
        """Queue compacted by object key ('prompt:<id>' or 'board:<id>')."""
        with self._lock:
            if not self.queue_path.is_file():
                return {}
            try:
                raw = json.loads(self.queue_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                return {}
            return raw if isinstance(raw, dict) else {}

    def save_queue(self, queue: Dict[str, Dict[str, Any]]) -> None:
        with self._lock:
            _atomic_write_json(self.queue_path, queue)

    def record_local_delete(self, kind: str, item_id: str) -> None:
        state = self.load_state()
        key = f"{kind}:{item_id}"
        deleted = list(state.get("deleted_ids") or [])
        if key not in deleted:
            deleted.append(key)
            state["deleted_ids"] = deleted
            self.save_state(state)


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncTransportError(f"Server antwortete mit Redirect ({code}); aus Sicherheitsgründen abgelehnt.")


class SyncBackend(ABC):
    @abstractmethod
    def pull(self, *, conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None) -> PullResult:
        ...

    @abstractmethod
    def push(self, *, conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None) -> PushResult:
        ...

    @abstractmethod
    def test_connection(self) -> ConnectionStatus:
        ...


class NullBackend(SyncBackend):
    def pull(self, *, conflict_resolver=None) -> PullResult:
        return PullResult()

    def push(self, *, conflict_resolver=None) -> PushResult:
        return PushResult()

    def test_connection(self) -> ConnectionStatus:
        return ConnectionStatus(ok=True, latency_ms=0.0, detail="Synchronisierung ist deaktiviert.")


# ---------------------------------------------------------------------------
# ServerBackend (Stage 2a — prompt-sync-server namespace "profiprompt")
# ---------------------------------------------------------------------------


class ServerBackend(SyncBackend):
    """REST client for ``prompt-sync-server`` handling separate ``prompt`` and ``board`` kinds."""

    def __init__(
        self,
        storage,
        state_store: SyncStateStore,
        *,
        server_url: str,
        namespace: str = DEFAULT_NAMESPACE,
        token_storage: Optional[TokenStorage] = None,
        token_override: Optional[str] = None,
        client_id: Optional[str] = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self.storage = storage
        self.state_store = state_store
        self.server_url = validate_server_url(server_url)
        self.namespace = validate_namespace(namespace)
        self.token_storage = token_storage or TokenStorage()
        self._token_override = token_override
        self.client_id = client_id or (platform.node() or "profiprompt-desktop")
        self.timeout = timeout
        self._opener = urllib_request.build_opener(_NoRedirectHandler())

    def _get_token(self) -> str:
        if self._token_override is not None:
            return self._token_override.strip()
        return self.token_storage.get_token()

    def _http_json(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        require_auth: bool = True,
    ) -> Tuple[int, Dict[str, str], Any]:
        url = f"{self.server_url}{path}"
        req_headers = {"Accept": "application/json"}
        if require_auth:
            token = self._get_token()
            if not token:
                raise SyncAuthError("Kein API-Token hinterlegt.")
            req_headers["Authorization"] = f"Bearer {token}"
        if headers:
            req_headers.update(headers)

        raw_bytes: Optional[bytes] = None
        if body is not None:
            raw_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"
            req_headers["Content-Length"] = str(len(raw_bytes))

        req = urllib_request.Request(url, data=raw_bytes, headers=req_headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                status = int(resp.status)
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                raw = resp.read()
                parsed = json.loads(raw.decode("utf-8")) if raw else None
                return status, resp_headers, parsed
        except urllib_error.HTTPError as exc:
            status = int(exc.code)
            resp_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
            if status in REDIRECT_STATUS_CODES:
                raise SyncTransportError(f"Unerwarteter Redirect ({status}).") from exc
            raw = exc.read()
            parsed = None
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except Exception:
                    parsed = {"raw": raw.decode("utf-8", errors="replace")}
            if status in (401, 403):
                raise SyncAuthError(f"Server lehnte Authentifizierung ab (HTTP {status}).") from exc
            if status in (304, 409, 410):
                return status, resp_headers, parsed
            raise SyncTransportError(f"HTTP {status} von {path}: {parsed}") from exc
        except SyncError:
            raise
        except Exception as exc:
            raise SyncTransportError(f"Verbindung fehlgeschlagen: {exc}") from exc

    def test_connection(self) -> ConnectionStatus:
        t0 = time.perf_counter()
        try:
            status, _headers, data = self._http_json("GET", "/v1/libraries")
            ms = round((time.perf_counter() - t0) * 1000.0, 1)
            if status != 200 or not isinstance(data, dict):
                return ConnectionStatus(ok=False, latency_ms=ms, detail=f"Unerwartete Antwort (HTTP {status}).")
            ns_entry = next(
                (n for n in (data.get("namespaces") or []) if isinstance(n, dict) and n.get("name") == self.namespace),
                None,
            )
            if ns_entry:
                return ConnectionStatus(
                    ok=True,
                    latency_ms=ms,
                    detail=f"Verbunden ({self.namespace}, rev {ns_entry.get('library_rev', 0)}, {ns_entry.get('item_count', 0)} Objekte)",
                    library_rev=int(ns_entry.get("library_rev", 0)),
                    item_count=int(ns_entry.get("item_count", 0)),
                )
            return ConnectionStatus(
                ok=True,
                latency_ms=ms,
                detail=f"Verbunden (Namespace '{self.namespace}' ist noch leer).",
                library_rev=0,
                item_count=0,
            )
        except SyncError as exc:
            ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return ConnectionStatus(ok=False, latency_ms=ms, detail=str(exc))

    def _current_local_snapshot(self) -> Tuple[Dict[str, Prompt], Dict[str, Board], Dict[str, str]]:
        prompts = {p.id: p for p in self.storage.load_prompts()}
        boards = {b.id: b for b in self.storage.load_boards()}
        hashes: Dict[str, str] = {}
        for pid, p in prompts.items():
            hashes[f"prompt:{pid}"] = canonical_prompt_hash(p)
        for bid, b in boards.items():
            hashes[f"board:{bid}"] = canonical_board_hash(b)
        return prompts, boards, hashes

    def queue_local_diff(self) -> int:
        """Compare current local prompts/boards against last synced hashes and enqueue changes."""
        state = self.state_store.load_state()
        queue = self.state_store.load_queue()
        known_hashes: Dict[str, str] = dict(state.get("item_hashes") or {})
        item_revs: Dict[str, int] = dict(state.get("item_revs") or {})

        prompts, boards, current_hashes = self._current_local_snapshot()

        # Upserts (new or modified)
        for key, h in current_hashes.items():
            if known_hashes.get(key) == h:
                continue
            kind, item_id = key.split(":", 1)
            payload = prompt_to_dict(prompts[item_id]) if kind == "prompt" else board_to_dict(boards[item_id])
            base_rev = queue.get(key, {}).get("base_rev", int(item_revs.get(key, 0)))
            queue[key] = {"id": item_id, "kind": kind, "op": "upsert", "base_rev": int(base_rev), "payload": payload}

        # Deletes (previously synced keys now absent locally)
        for key in list(known_hashes.keys()):
            if key not in current_hashes and int(item_revs.get(key, 0)) > 0:
                kind, item_id = key.split(":", 1)
                base_rev = queue.get(key, {}).get("base_rev", int(item_revs.get(key, 0)))
                queue[key] = {"id": item_id, "kind": kind, "op": "delete", "base_rev": int(base_rev)}

        self.state_store.save_queue(queue)
        return len(queue)

    def pull(
        self,
        *,
        full: bool = False,
        conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None,
    ) -> PullResult:
        state = self.state_store.load_state()
        since_rev = 0 if full else int(state.get("library_rev", 0))
        path = f"/v1/libraries/{self.namespace}/changes"
        if not full and since_rev > 0:
            path = f"{path}?since_rev={since_rev}"
        headers = {}
        if not full and state.get("etag"):
            headers["If-None-Match"] = str(state["etag"])

        status, resp_headers, data = self._http_json("GET", path, headers=headers)
        if status == 304:
            return PullResult(cursor=since_rev, not_modified=True)
        if status == 410:
            # Tombstone retention exceeded -> perform safe full pull
            return self.pull(full=True, conflict_resolver=conflict_resolver)
        if status != 200 or not isinstance(data, dict):
            raise SyncTransportError(f"Unerwartete Pull-Antwort (HTTP {status}).")

        items = data.get("items") or []
        tombstones = data.get("tombstones") or []
        new_lib_rev = int(data.get("library_rev", since_rev))

        local_prompts = list(self.storage.load_prompts())
        local_boards = list(self.storage.load_boards())
        prompt_by_id = {p.id: p for p in local_prompts}
        board_by_id = {b.id: b for b in local_boards}

        item_revs: Dict[str, int] = dict(state.get("item_revs") or {})
        item_hashes: Dict[str, str] = dict(state.get("item_hashes") or {})
        result = PullResult(cursor=new_lib_rev)
        prompts_changed = False
        boards_changed = False

        # Apply prompts before boards
        ordered_items = sorted(items, key=lambda x: 0 if x.get("kind") == "prompt" else 1)
        for entry in ordered_items:
            kind = entry.get("kind")
            item_id = entry.get("id")
            rev = int(entry.get("rev", 0))
            payload = entry.get("payload")
            if kind not in ("prompt", "board") or not item_id or not isinstance(payload, dict):
                continue
            key = f"{kind}:{item_id}"
            payload = dict(payload)
            payload["id"] = item_id

            if kind == "prompt":
                rem_p = prompt_from_dict(payload)
                rem_hash = canonical_prompt_hash(rem_p)
                loc_p = prompt_by_id.get(item_id)
                if loc_p is None:
                    local_prompts.append(rem_p)
                    prompt_by_id[item_id] = rem_p
                    item_revs[key] = rev
                    item_hashes[key] = rem_hash
                    result.upserts += 1
                    prompts_changed = True
                else:
                    loc_hash = canonical_prompt_hash(loc_p)
                    if loc_hash == rem_hash or item_hashes.get(key) == loc_hash:
                        idx = next(i for i, p in enumerate(local_prompts) if p.id == item_id)
                        local_prompts[idx] = rem_p
                        prompt_by_id[item_id] = rem_p
                        item_revs[key] = rev
                        item_hashes[key] = rem_hash
                        if loc_hash != rem_hash:
                            result.upserts += 1
                            prompts_changed = True
                    else:
                        conflict = ImportConflict(
                            kind="prompt",
                            item_id=item_id,
                            title=loc_p.title or rem_p.title or item_id,
                            source=f"server:{self.namespace}",
                            local_payload=prompt_to_dict(loc_p),
                            remote_payload=prompt_to_dict(rem_p),
                            local_updated_at=loc_p.updated_at,
                            remote_updated_at=rem_p.updated_at,
                            remote_rev=rev,
                        )
                        if conflict_resolver is None:
                            result.conflicts.append(conflict)
                        else:
                            choice = conflict_resolver(conflict)
                            if choice == "take_remote":
                                idx = next(i for i, p in enumerate(local_prompts) if p.id == item_id)
                                local_prompts[idx] = rem_p
                                prompt_by_id[item_id] = rem_p
                                item_revs[key] = rev
                                item_hashes[key] = rem_hash
                                result.upserts += 1
                                prompts_changed = True
                            elif choice == "keep_copy":
                                merged_p = prompt_from_dict(prompt_to_dict(rem_p))
                                next_v = max((v.version_number for v in merged_p.versions), default=0) + 1
                                merged_p.versions.append(
                                    Version(
                                        id=gen_id(),
                                        prompt_id=merged_p.id,
                                        version_number=next_v,
                                        title=f"{loc_p.title or 'Lokal'} (lokale Kopie)",
                                        text=loc_p.text,
                                        result=loc_p.last_result,
                                        tags=list(loc_p.tags or []),
                                        created_at=loc_p.created_at,
                                        updated_at=now_iso(),
                                    )
                                )
                                idx = next(i for i, p in enumerate(local_prompts) if p.id == item_id)
                                local_prompts[idx] = merged_p
                                prompt_by_id[item_id] = merged_p
                                item_revs[key] = rev
                                item_hashes[key] = rem_hash
                                result.upserts += 1
                                prompts_changed = True
                            else:
                                # keep_local -> update base_rev so next push overwrites cleanly
                                item_revs[key] = rev
            else:
                rem_b = board_from_dict(payload)
                rem_hash = canonical_board_hash(rem_b)
                loc_b = board_by_id.get(item_id)
                if loc_b is None:
                    local_boards.append(rem_b)
                    board_by_id[item_id] = rem_b
                    item_revs[key] = rev
                    item_hashes[key] = rem_hash
                    result.upserts += 1
                    boards_changed = True
                else:
                    loc_hash = canonical_board_hash(loc_b)
                    if loc_hash == rem_hash or item_hashes.get(key) == loc_hash:
                        idx = next(i for i, b in enumerate(local_boards) if b.id == item_id)
                        local_boards[idx] = rem_b
                        board_by_id[item_id] = rem_b
                        item_revs[key] = rev
                        item_hashes[key] = rem_hash
                        if loc_hash != rem_hash:
                            result.upserts += 1
                            boards_changed = True
                    else:
                        conflict = ImportConflict(
                            kind="board",
                            item_id=item_id,
                            title=loc_b.title or rem_b.title or item_id,
                            source=f"server:{self.namespace}",
                            local_payload=board_to_dict(loc_b),
                            remote_payload=board_to_dict(rem_b),
                            local_updated_at=loc_b.created_at,
                            remote_updated_at=rem_b.created_at,
                            remote_rev=rev,
                        )
                        if conflict_resolver is None:
                            result.conflicts.append(conflict)
                        else:
                            choice = conflict_resolver(conflict)
                            if choice == "take_remote":
                                idx = next(i for i, b in enumerate(local_boards) if b.id == item_id)
                                local_boards[idx] = rem_b
                                board_by_id[item_id] = rem_b
                                item_revs[key] = rev
                                item_hashes[key] = rem_hash
                                result.upserts += 1
                                boards_changed = True
                            elif choice == "keep_copy":
                                copy_id = gen_id()
                                local_copy = Board(
                                    id=copy_id,
                                    title=f"{loc_b.title or 'Board'} (lokale Kopie)",
                                    description=loc_b.description,
                                    items=[
                                        BoardItem(
                                            id=gen_id(),
                                            board_id=copy_id,
                                            prompt_id=it.prompt_id,
                                            version_id=it.version_id,
                                            created_at=it.created_at,
                                        )
                                        for it in loc_b.items
                                    ],
                                    created_at=now_iso(),
                                )
                                idx = next(i for i, b in enumerate(local_boards) if b.id == item_id)
                                local_boards[idx] = rem_b
                                local_boards.append(local_copy)
                                board_by_id[item_id] = rem_b
                                board_by_id[copy_id] = local_copy
                                item_revs[key] = rev
                                item_hashes[key] = rem_hash
                                result.upserts += 1
                                boards_changed = True
                            else:
                                item_revs[key] = rev

        # Apply tombstones (respecting local edits -> conflict instead of silent delete)
        for tomb in tombstones:
            kind = tomb.get("kind")
            item_id = tomb.get("id")
            rev = int(tomb.get("rev", 0))
            if kind not in ("prompt", "board") or not item_id:
                continue
            key = f"{kind}:{item_id}"
            if kind == "prompt" and item_id in prompt_by_id:
                loc_p = prompt_by_id[item_id]
                loc_hash = canonical_prompt_hash(loc_p)
                if item_hashes.get(key) in (None, loc_hash):
                    local_prompts = [p for p in local_prompts if p.id != item_id]
                    prompt_by_id.pop(item_id, None)
                    item_revs.pop(key, None)
                    item_hashes.pop(key, None)
                    result.tombstones += 1
                    prompts_changed = True
                else:
                    result.conflicts.append(
                        ImportConflict(
                            kind="prompt",
                            item_id=item_id,
                            title=loc_p.title or item_id,
                            source=f"server:{self.namespace} (gelöscht)",
                            local_payload=prompt_to_dict(loc_p),
                            remote_payload={"id": item_id, "deleted": True},
                            local_updated_at=loc_p.updated_at,
                            remote_updated_at=str(tomb.get("deleted_at") or ""),
                            remote_rev=rev,
                        )
                    )
            elif kind == "board" and item_id in board_by_id:
                loc_b = board_by_id[item_id]
                loc_hash = canonical_board_hash(loc_b)
                if item_hashes.get(key) in (None, loc_hash):
                    local_boards = [b for b in local_boards if b.id != item_id]
                    board_by_id.pop(item_id, None)
                    item_revs.pop(key, None)
                    item_hashes.pop(key, None)
                    result.tombstones += 1
                    boards_changed = True
                else:
                    result.conflicts.append(
                        ImportConflict(
                            kind="board",
                            item_id=item_id,
                            title=loc_b.title or item_id,
                            source=f"server:{self.namespace} (gelöscht)",
                            local_payload=board_to_dict(loc_b),
                            remote_payload={"id": item_id, "deleted": True},
                            local_updated_at=loc_b.created_at,
                            remote_updated_at=str(tomb.get("deleted_at") or ""),
                            remote_rev=rev,
                        )
                    )

        # Persist prompts BEFORE boards
        if prompts_changed:
            self.storage.save_prompts(local_prompts)
        if boards_changed:
            self.storage.save_boards(local_boards)

        state["library_rev"] = new_lib_rev
        state["etag"] = resp_headers.get("etag", f'"rev-{new_lib_rev}"')
        state["item_revs"] = item_revs
        state["item_hashes"] = item_hashes
        state["last_sync_at"] = now_iso()
        self.state_store.save_state(state)
        return result

    def push(
        self,
        *,
        conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None,
    ) -> PushResult:
        self.queue_local_diff()
        queue = self.state_store.load_queue()
        if not queue:
            return PushResult()

        # Order prompts before boards in push payload
        mutations = sorted(queue.values(), key=lambda m: (0 if m.get("kind") == "prompt" else 1, m.get("id", "")))
        idem_key = f"pp-{uuid.uuid4().hex}"
        try:
            status, _headers, data = self._http_json(
                "POST",
                f"/v1/libraries/{self.namespace}/push",
                body={"client_id": self.client_id, "mutations": mutations},
                headers={"Idempotency-Key": idem_key},
            )
        except SyncTransportError:
            # Offline-first: keep queue intact for later flush
            return PushResult(queued_offline=len(queue))

        if status not in (200, 409) or not isinstance(data, dict):
            raise SyncTransportError(f"Unerwartete Push-Antwort (HTTP {status}).")

        state = self.state_store.load_state()
        item_revs: Dict[str, int] = dict(state.get("item_revs") or {})
        item_hashes: Dict[str, str] = dict(state.get("item_hashes") or {})
        result = PushResult(library_rev=int(data.get("library_rev", state.get("library_rev", 0))))

        for applied in data.get("applied") or []:
            key = f"{applied['kind']}:{applied['id']}"
            rev = int(applied["rev"])
            result.applied_revs[key] = rev
            mut = queue.pop(key, None)
            if applied.get("op") == "delete":
                item_revs.pop(key, None)
                item_hashes.pop(key, None)
            else:
                item_revs[key] = rev
                if mut and isinstance(mut.get("payload"), dict):
                    item_hashes[key] = (
                        canonical_prompt_hash(mut["payload"])
                        if applied["kind"] == "prompt"
                        else canonical_board_hash(mut["payload"])
                    )

        for conf in data.get("conflicts") or []:
            kind = conf.get("kind", "prompt")
            item_id = conf.get("id", "")
            key = f"{kind}:{item_id}"
            server_item = conf.get("server_item") or {}
            mut = queue.get(key) or {}
            local_payload = mut.get("payload") or {"id": item_id}
            remote_payload = server_item.get("payload") or {"id": item_id}
            ic = ImportConflict(
                kind="prompt" if kind == "prompt" else "board",
                item_id=item_id,
                title=str(local_payload.get("title") or remote_payload.get("title") or item_id),
                source=f"server:{self.namespace}",
                local_payload=local_payload,
                remote_payload=remote_payload,
                remote_rev=int(conf.get("server_rev", 0)),
            )
            result.conflicts.append(ic)
            # Update base_rev in queue if user resolves via keep_local later
            if key in queue and conf.get("server_rev") is not None:
                queue[key]["base_rev"] = int(conf["server_rev"])

        if result.library_rev is not None:
            state["library_rev"] = max(int(state.get("library_rev", 0)), result.library_rev)
            state["etag"] = f'"rev-{state["library_rev"]}"'
        state["item_revs"] = item_revs
        state["item_hashes"] = item_hashes
        state["last_sync_at"] = now_iso()
        self.state_store.save_state(state)
        self.state_store.save_queue(queue)
        return result


# ---------------------------------------------------------------------------
# FileSlotBackend (Stage 3 — .SYNC host slots, mutual ProfiPrompt + Browser visibility)
# ---------------------------------------------------------------------------


def is_conflict_copy_filename(filename: str, app: str, host: str) -> bool:
    """Detect OneDrive/cloud conflict copies like ``profiprompt@ASUS-GEI-WORKSTATION.json`` (A7)."""
    expected = f"{app}@{host}.json"
    if filename == expected:
        return False
    if filename.startswith(".") or filename.endswith((".tmp", ".crswap")):
        return True
    if filename.startswith(f"{app}@{host}-") and filename.endswith(".json"):
        return True
    return False


class FileSlotBackend(SyncBackend):
    """Single-writer .SYNC-style host slot backend with mutual ProfiPrompt/Browser visibility."""

    def __init__(
        self,
        storage,
        state_store: SyncStateStore,
        *,
        sync_dir: Path,
        app_name: str = "profiprompt",
        host_name: Optional[str] = None,
    ) -> None:
        self.storage = storage
        self.state_store = state_store
        self.sync_dir = Path(sync_dir)
        self.app_name = app_name
        self.host_name = (host_name or get_host_slot_name()).strip().upper()
        if not self.host_name:
            raise SyncError("Host-Slot-Name darf nicht leer sein.")

    @property
    def own_slot_key(self) -> str:
        return f"{self.app_name}@{self.host_name}"

    @property
    def own_slot_path(self) -> Path:
        return self.sync_dir / self.app_name / self.host_name / f"{self.app_name}@{self.host_name}.json"

    def test_connection(self) -> ConnectionStatus:
        t0 = time.perf_counter()
        if not self.sync_dir.exists() or not self.sync_dir.is_dir():
            return ConnectionStatus(
                ok=False,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 1),
                detail=f"Sync-Ordner existiert nicht: {self.sync_dir}",
            )
        slots, warnings = self.discover_foreign_slots()
        ms = round((time.perf_counter() - t0) * 1000.0, 1)
        warn_suffix = f" ({len(warnings)} A7-Konfliktdatei(en))" if warnings else ""
        return ConnectionStatus(
            ok=True,
            latency_ms=ms,
            detail=f"Ordner erreichbar, eigener Slot {self.own_slot_key}, {len(slots)} fremde(r) Slot(s){warn_suffix}.",
            item_count=len(slots),
        )

    def discover_foreign_slots(self) -> Tuple[List[ForeignSlotInfo], List[str]]:
        """Discover foreign ProfiPrompt & ProfiPrompt-Browser slots; flag A7 conflict copies."""
        state = self.state_store.load_state()
        slot_modes: Dict[str, str] = state.get("slot_modes") or {}
        found: List[ForeignSlotInfo] = []
        warnings: List[str] = []

        for app in VISIBLE_SLOT_APPS:
            app_root = self.sync_dir / app
            if not app_root.is_dir():
                continue
            for host_dir in sorted(app_root.iterdir()):
                if not host_dir.is_dir():
                    continue
                host = host_dir.name
                canonical_name = f"{app}@{host}.json"
                for child in sorted(host_dir.iterdir()):
                    if not child.is_file():
                        continue
                    if is_conflict_copy_filename(child.name, app, host):
                        warnings.append(f"Konfliktkopie/Temp ignoriert: {child.name}")
                        continue
                slot_file = host_dir / canonical_name
                if not slot_file.is_file():
                    continue
                slot_key = f"{app}@{host}"
                if slot_key.upper() == self.own_slot_key.upper():
                    continue
                try:
                    raw = json.loads(slot_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    warnings.append(f"Slot nicht lesbar: {slot_file.name}")
                    continue
                manifest = raw.get("manifest") if isinstance(raw.get("manifest"), dict) else {}
                updated_at = str(
                    manifest.get("updated_at")
                    or (raw.get("app") or {}).get("exported_at")
                    or datetime.fromtimestamp(slot_file.stat().st_mtime, tz=timezone.utc).isoformat()
                )
                item_count = int(manifest.get("item_count", len(raw.get("prompts") or [])))
                found.append(
                    ForeignSlotInfo(
                        slot_key=slot_key,
                        app=app,
                        host=host,
                        path=slot_file,
                        updated_at=updated_at,
                        item_count=item_count,
                        import_mode=slot_modes.get(slot_key, "never"),
                    )
                )
        return found, warnings

    def set_slot_import_mode(self, slot_key: str, mode: str) -> None:
        if mode not in SLOT_IMPORT_MODES:
            raise ValueError(f"Ungültiger Slot-Importmodus: {mode}")
        state = self.state_store.load_state()
        slot_modes = dict(state.get("slot_modes") or {})
        slot_modes[slot_key] = mode
        state["slot_modes"] = slot_modes
        self.state_store.save_state(state)

    def push(self, *, conflict_resolver=None, force: bool = False) -> PushResult:
        """Export own library atomically to own host slot (never writes into foreign slots)."""
        payload = build_library_export(self.storage)
        updated_at = now_iso()
        payload["manifest"] = {
            "app": self.app_name,
            "version": APP_VERSION,
            "host": self.host_name,
            "updated_at": updated_at,
            "item_count": len(payload.get("prompts") or []),
            "board_count": len(payload.get("boards") or []),
            "schema_version": SCHEMA_VERSION,
        }
        content_hash = hashlib.sha256(
            json.dumps(
                {"prompts": payload["prompts"], "boards": payload["boards"]},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()

        state = self.state_store.load_state()
        if not force and state.get("last_exported_hash") == content_hash and self.own_slot_path.is_file():
            return PushResult()

        _atomic_write_json(self.own_slot_path, payload)
        state["last_exported_hash"] = content_hash
        state["last_sync_at"] = updated_at
        self.state_store.save_state(state)
        return PushResult(applied_revs={self.own_slot_key: 1})

    def pull(
        self,
        *,
        conflict_resolver: Optional[Callable[[ImportConflict], ConflictChoice]] = None,
    ) -> PullResult:
        """Import foreign slots configured as ``once`` or ``on_start``."""
        slots, warnings = self.discover_foreign_slots()
        state = self.state_store.load_state()
        slot_modes = dict(state.get("slot_modes") or {})
        slot_cursors = dict(state.get("slot_cursors") or {})
        slot_hashes = dict(state.get("slot_item_hashes") or {})
        deleted_ids = list(state.get("deleted_ids") or [])

        result = PullResult(warnings=warnings)

        for slot in slots:
            mode = slot_modes.get(slot.slot_key, "never")
            if mode == "never":
                continue
            if mode == "on_start" and slot_cursors.get(slot.slot_key, "") >= slot.updated_at:
                continue

            merge_res = merge_library_payload(
                self.storage,
                slot.path,
                source_label=slot.slot_key,
                last_imported_hashes=slot_hashes.get(slot.slot_key) or {},
                deleted_ids=deleted_ids,
                conflict_resolver=conflict_resolver,
            )
            result.upserts += (
                merge_res.added_prompts
                + merge_res.updated_prompts
                + merge_res.added_boards
                + merge_res.updated_boards
            )
            result.conflicts.extend(merge_res.conflicts)

            merged_hash_map = dict(slot_hashes.get(slot.slot_key) or {})
            merged_hash_map.update(merge_res.imported_hashes)
            slot_hashes[slot.slot_key] = merged_hash_map
            slot_cursors[slot.slot_key] = slot.updated_at

            if mode == "once":
                slot_modes[slot.slot_key] = "never"

        state["slot_modes"] = slot_modes
        state["slot_cursors"] = slot_cursors
        state["slot_item_hashes"] = slot_hashes
        state["last_sync_at"] = now_iso()
        self.state_store.save_state(state)
        return result
