"""Tests for ProfiPrompt JSON merge import, ServerBackend (real prompt-sync-server),
FileSlotBackend (.SYNC host slots + A7 filter), and SyncSettingsDialog (offscreen)."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from library_export import build_library_export
from library_import import (
    canonical_board_hash,
    canonical_prompt_hash,
    merge_library_payload,
)
from models import Board, BoardItem, Prompt, Version
from storage import Storage
from sync_backend import (
    FileSlotBackend,
    NullBackend,
    ServerBackend,
    SyncAuthError,
    SyncStateStore,
    SyncTransportError,
    TokenStorage,
    is_conflict_copy_filename,
    validate_server_url,
)


def _sample_prompt(pid: str = "p1", title: str = "Review", text: str = "Check diff.") -> Prompt:
    return Prompt(
        id=pid,
        title=title,
        purpose="QA",
        text=text,
        tags=["review"],
        versions=[
            Version(id=f"{pid}_v1", prompt_id=pid, version_number=1, title="v1", text="Short v1"),
        ],
    )


def _sample_board(bid: str = "b1", pid: str = "p1", title: str = "Daily") -> Board:
    return Board(
        id=bid,
        title=title,
        description="Core board",
        items=[BoardItem(id=f"{bid}_i1", board_id=bid, prompt_id=pid, version_id=None)],
    )


# ---------------------------------------------------------------------------
# 1. library_import tests
# ---------------------------------------------------------------------------


def test_merge_import_adds_prompts_before_boards_and_prunes_dangling_refs(tmp_path: Path):
    storage = Storage(tmp_path / "data")
    payload = {
        "schema_version": "profiprompt-library-v1",
        "prompts": [
            {
                "id": "p1",
                "title": "Prompt 1",
                "purpose": "Test",
                "text": "Hello",
                "tags": ["a"],
                "versions": [],
            }
        ],
        "boards": [
            {
                "id": "b1",
                "title": "Board 1",
                "description": "",
                "items": [
                    {"id": "i1", "board_id": "b1", "prompt_id": "p1", "version_id": None},
                    {"id": "i2", "board_id": "b1", "prompt_id": "missing_p", "version_id": None},
                ],
            }
        ],
    }

    res = merge_library_payload(storage, payload, source_label="test.json")
    assert res.added_prompts == 1
    assert res.added_boards == 1
    assert res.conflicts == []
    boards = storage.load_boards()
    assert len(boards) == 1
    assert [it.prompt_id for it in boards[0].items] == ["p1"]


def test_merge_import_detects_conflict_and_supports_all_three_resolutions(tmp_path: Path):
    storage = Storage(tmp_path / "data")
    storage.upsert_prompt(_sample_prompt("p1", "Lokal", "Lokaler Text"))
    remote_payload = {
        "schema_version": "profiprompt-library-v1",
        "prompts": [
            {
                "id": "p1",
                "title": "Remote",
                "purpose": "QA",
                "text": "Fremder Text",
                "tags": ["review"],
                "versions": [],
            }
        ],
        "boards": [],
    }

    # No resolver -> conflict returned, local untouched
    r_unresolved = merge_library_payload(storage, remote_payload, source_label="foreign")
    assert len(r_unresolved.conflicts) == 1
    assert storage.get_prompt("p1").text == "Lokaler Text"

    # keep_local -> local preserved
    r_keep = merge_library_payload(
        storage, remote_payload, source_label="foreign", conflict_resolver=lambda _: "keep_local"
    )
    assert r_keep.updated_prompts == 0
    assert storage.get_prompt("p1").text == "Lokaler Text"

    # keep_copy -> remote becomes main text, local preserved losslessly as new Version
    r_copy = merge_library_payload(
        storage, remote_payload, source_label="foreign", conflict_resolver=lambda _: "keep_copy"
    )
    assert r_copy.updated_prompts == 1
    p_after = storage.get_prompt("p1")
    assert p_after.text == "Fremder Text"
    assert any(v.text == "Lokaler Text" for v in p_after.versions)

    # take_remote -> replaces with remote cleanly
    remote_payload2 = {
        "schema_version": "profiprompt-library-v1",
        "prompts": [
            {
                "id": "p1",
                "title": "Remote Final",
                "purpose": "QA",
                "text": "Endstand",
                "tags": [],
                "versions": [],
            }
        ],
        "boards": [],
    }
    r_take = merge_library_payload(
        storage, remote_payload2, source_label="foreign", conflict_resolver=lambda _: "take_remote"
    )
    assert r_take.updated_prompts == 1
    assert storage.get_prompt("p1").text == "Endstand"


# ---------------------------------------------------------------------------
# 2. URL security & TokenStorage tests
# ---------------------------------------------------------------------------


def test_validate_server_url_blocks_public_http_and_allows_loopback_and_tailscale():
    import ipaddress

    tailnet_host = str(ipaddress.IPv4Address(0x6440002A))
    assert validate_server_url("http://127.0.0.1:8765/") == "http://127.0.0.1:8765"
    assert validate_server_url(f"http://{tailnet_host}:8765") == f"http://{tailnet_host}:8765"
    assert validate_server_url("https://sync.example.org:8443") == "https://sync.example.org:8443"

    with pytest.raises(SyncTransportError):
        validate_server_url("http://sync.example.org:8765")
    with pytest.raises(SyncTransportError):
        validate_server_url("http://198.51.100.50:8765")
    with pytest.raises(SyncTransportError):
        validate_server_url("https://user:pass@sync.example.org")


def test_token_storage_0600_fallback_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROFIPROMPT_DISABLE_KEYRING", "1")
    ts = TokenStorage(fallback_path=tmp_path / "token.json")
    assert ts.get_token() == ""
    ts.set_token("secret-token-xyz")
    assert ts.get_token() == "secret-token-xyz"
    ts.clear_token()
    assert ts.get_token() == ""


# ---------------------------------------------------------------------------
# 3. FileSlotBackend tests (.SYNC pattern, mutual visibility, A7 conflict filter)
# ---------------------------------------------------------------------------


def test_file_slot_backend_single_writer_mutual_visibility_and_a7_filter(tmp_path: Path):
    sync_dir = tmp_path / "cloud_sync"
    sync_dir.mkdir()

    # Host A (ASUS-GEI) exports its own slot
    st_a = Storage(tmp_path / "data_a")
    st_a.upsert_prompt(_sample_prompt("p1", "Von A", "Text A"))
    st_a.upsert_board(_sample_board("b1", "p1", "Board A"))
    backend_a = FileSlotBackend(st_a, SyncStateStore(tmp_path / "data_a"), sync_dir=sync_dir, host_name="ASUS-GEI")

    push_a = backend_a.push()
    assert "profiprompt@ASUS-GEI" in push_a.applied_revs
    expected_slot = sync_dir / "profiprompt" / "ASUS-GEI" / "profiprompt@ASUS-GEI.json"
    assert expected_slot.is_file()
    written = json.loads(expected_slot.read_text(encoding="utf-8"))
    assert written["manifest"]["app"] == "profiprompt"
    assert written["manifest"]["host"] == "ASUS-GEI"

    # Drop an A7 conflict copy + a ProfiPrompt-Browser slot
    conflict_copy = expected_slot.parent / "profiprompt@ASUS-GEI-WORKSTATION-LG.json"
    conflict_copy.write_text("{}", encoding="utf-8")
    assert is_conflict_copy_filename(conflict_copy.name, "profiprompt", "ASUS-GEI")

    browser_slot_dir = sync_dir / "profiprompt-browser" / "EDGE-HOME"
    browser_slot_dir.mkdir(parents=True)
    browser_slot = browser_slot_dir / "profiprompt-browser@EDGE-HOME.json"
    browser_slot.write_text(
        json.dumps(
            {
                "schema_version": "profiprompt-library-v1",
                "manifest": {
                    "app": "profiprompt-browser",
                    "host": "EDGE-HOME",
                    "updated_at": "2026-11-26T12:00:00Z",
                    "item_count": 1,
                },
                "prompts": [
                    {
                        "id": "p_browser",
                        "title": "Aus Browser",
                        "purpose": "Clip",
                        "text": "Browser-Prompt",
                        "tags": ["web"],
                        "versions": [],
                    }
                ],
                "boards": [],
            }
        ),
        encoding="utf-8",
    )

    # Host B discovers BOTH profiprompt@ASUS-GEI and profiprompt-browser@EDGE-HOME, warns on A7 conflict copy
    st_b = Storage(tmp_path / "data_b")
    state_b = SyncStateStore(tmp_path / "data_b")
    backend_b = FileSlotBackend(st_b, state_b, sync_dir=sync_dir, host_name="WORKSTATION-LG")
    slots, warnings = backend_b.discover_foreign_slots()
    slot_keys = {s.slot_key for s in slots}
    assert "profiprompt@ASUS-GEI" in slot_keys
    assert "profiprompt-browser@EDGE-HOME" in slot_keys
    assert any("profiprompt@ASUS-GEI-WORKSTATION-LG.json" in w for w in warnings)

    # Default mode is 'never' -> pull imports 0
    assert backend_b.pull().upserts == 0

    # Set ASUS-GEI to 'once' and Browser to 'on_start' -> both imported, 'once' resets to 'never'
    backend_b.set_slot_import_mode("profiprompt@ASUS-GEI", "once")
    backend_b.set_slot_import_mode("profiprompt-browser@EDGE-HOME", "on_start")
    res_b = backend_b.pull()
    assert res_b.upserts == 3  # p1, b1, p_browser
    assert st_b.get_prompt("p1").text == "Text A"
    assert st_b.get_prompt("p_browser").text == "Browser-Prompt"
    assert state_b.load_state()["slot_modes"]["profiprompt@ASUS-GEI"] == "never"

    # Local deletion blocklist prevents re-import on subsequent pull
    st_b.delete_prompt("p_browser")
    state_b.record_local_delete("prompt", "p_browser")
    state_b_raw = state_b.load_state()
    state_b_raw["slot_cursors"]["profiprompt-browser@EDGE-HOME"] = ""
    state_b.save_state(state_b_raw)
    backend_b.pull()
    assert st_b.get_prompt("p_browser") is None


# ---------------------------------------------------------------------------
# 4. ServerBackend end-to-end tests against REAL local prompt-sync-server
# ---------------------------------------------------------------------------


def _start_contract_sync_server(expected_token: str = "test-rw-token"):
    """Self-contained local HTTP contract server (works identically in CI without sibling repos)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    state = {"library_rev": 0, "min_retained_rev": 0, "objects": {}, "tombstones": {}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send_json(self, code: int, payload, extra_headers=None):
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
            self.send_response(code)
            if payload is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if raw:
                self.wfile.write(raw)

        def _check_auth(self) -> bool:
            if self.headers.get("Authorization") != f"Bearer {expected_token}":
                self._send_json(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self):
            if not self._check_auth():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/v1/libraries":
                self._send_json(
                    200,
                    {
                        "namespaces": [
                            {
                                "name": "profiprompt",
                                "schema_version": "profiprompt-library-v1",
                                "library_rev": state["library_rev"],
                                "min_retained_rev": state["min_retained_rev"],
                                "item_count": len(state["objects"]),
                            }
                        ]
                    },
                )
                return
            if parsed.path == "/v1/libraries/profiprompt/changes":
                etag = f'"rev-{state["library_rev"]}"'
                if self.headers.get("If-None-Match") == etag:
                    self._send_json(304, None, {"ETag": etag})
                    return
                qs = parse_qs(parsed.query)
                since = int(qs.get("since_rev", ["0"])[0]) if "since_rev" in qs else 0
                if since > 0 and since < state["min_retained_rev"]:
                    self._send_json(
                        410,
                        {
                            "reset_required": True,
                            "namespace": "profiprompt",
                            "library_rev": state["library_rev"],
                            "min_retained_rev": state["min_retained_rev"],
                        },
                    )
                    return
                items = [o for o in state["objects"].values() if o["lib_rev"] > since]
                tombs = [t for t in state["tombstones"].values() if t["lib_rev"] > since]
                self._send_json(
                    200,
                    {
                        "namespace": "profiprompt",
                        "library_rev": state["library_rev"],
                        "min_retained_rev": state["min_retained_rev"],
                        "items": items,
                        "tombstones": tombs,
                    },
                    {"ETag": etag},
                )
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self):
            if not self._check_auth():
                return
            if self.path != "/v1/libraries/profiprompt/push":
                self._send_json(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            applied = []
            conflicts = []
            for m in body.get("mutations") or []:
                key = f"{m['kind']}:{m['id']}"
                existing = state["objects"].get(key)
                server_rev = existing["rev"] if existing else 0
                if int(m.get("base_rev", 0)) != server_rev:
                    conflicts.append(
                        {
                            "id": m["id"],
                            "kind": m["kind"],
                            "client_base_rev": int(m.get("base_rev", 0)),
                            "server_rev": server_rev,
                            "server_item": existing,
                        }
                    )
                    continue
                state["library_rev"] += 1
                new_rev = server_rev + 1
                if m.get("op") == "delete":
                    state["objects"].pop(key, None)
                    state["tombstones"][key] = {
                        "id": m["id"],
                        "kind": m["kind"],
                        "rev": new_rev,
                        "lib_rev": state["library_rev"],
                        "deleted_at": "2026-11-26T12:00:00Z",
                    }
                else:
                    state["tombstones"].pop(key, None)
                    state["objects"][key] = {
                        "id": m["id"],
                        "kind": m["kind"],
                        "rev": new_rev,
                        "lib_rev": state["library_rev"],
                        "updated_at": "2026-11-26T12:00:00Z",
                        "payload": m["payload"],
                    }
                applied.append({"id": m["id"], "kind": m["kind"], "op": m.get("op", "upsert"), "rev": new_rev})
            code = 409 if conflicts else 200
            self._send_json(
                code,
                {
                    "namespace": "profiprompt",
                    "library_rev": state["library_rev"],
                    "applied": applied,
                    "conflicts": conflicts,
                },
            )

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}", expected_token, state


def test_server_backend_full_roundtrip_push_pull_409_410_and_offline_queue(tmp_path: Path):
    srv, base_url, token, srv_state = _start_contract_sync_server()
    try:
        # Client 1 pushes prompt + board
        st1 = Storage(tmp_path / "c1")
        st1.upsert_prompt(_sample_prompt("p1", "Server Prompt", "V1 text"))
        st1.upsert_board(_sample_board("b1", "p1", "Server Board"))
        c1 = ServerBackend(
            st1,
            SyncStateStore(tmp_path / "c1"),
            server_url=base_url,
            namespace="profiprompt",
            token_override=token,
            client_id="client-1",
        )

        conn = c1.test_connection()
        assert conn.ok is True

        p1 = c1.push()
        assert "prompt:p1" in p1.applied_revs
        assert "board:b1" in p1.applied_revs
        assert p1.conflicts == []

        # Client 2 pulls prompt + board cleanly
        st2 = Storage(tmp_path / "c2")
        c2 = ServerBackend(
            st2,
            SyncStateStore(tmp_path / "c2"),
            server_url=base_url,
            namespace="profiprompt",
            token_override=token,
            client_id="client-2",
        )
        pull2 = c2.pull()
        assert pull2.upserts == 2
        assert st2.get_prompt("p1").text == "V1 text"
        assert len(st2.load_boards()) == 1

        # Second pull gets 304 Not Modified
        pull2_again = c2.pull()
        assert pull2_again.not_modified is True

        # Concurrent edit -> 409 Conflict!
        st1.upsert_prompt(_sample_prompt("p1", "Server Prompt", "Client 1 edit"))
        assert c1.push().conflicts == []

        st2.upsert_prompt(_sample_prompt("p1", "Server Prompt", "Client 2 conflicting edit"))
        push2 = c2.push()
        assert len(push2.conflicts) == 1
        assert push2.conflicts[0].item_id == "p1"
        assert push2.conflicts[0].remote_rev == 2

        # 410 Gone recovery -> triggers automatic full pull
        srv_state["min_retained_rev"] = 999
        c2_state = c2.state_store.load_state()
        c2_state["etag"] = ""
        c2_state["library_rev"] = 1
        c2.state_store.save_state(c2_state)
        pull_after_410 = c2.pull(conflict_resolver=lambda _: "take_remote")
        assert pull_after_410.upserts >= 1
        assert st2.get_prompt("p1").text == "Client 1 edit"

        # Wrong token -> SyncAuthError
        bad_client = ServerBackend(
            st2,
            SyncStateStore(tmp_path / "c2"),
            server_url=base_url,
            namespace="profiprompt",
            token_override="wrong-token",
        )
        assert bad_client.test_connection().ok is False
        with pytest.raises(SyncAuthError):
            bad_client.pull()
    finally:
        srv.shutdown()
        srv.server_close()

    # After server shutdown, push queues offline instead of crashing
    st1.upsert_prompt(_sample_prompt("p_offline", "Offline", "Queued"))
    off_res = c1.push()
    assert off_res.queued_offline >= 1


def test_sync_settings_dialog_smoke_offscreen(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("PROFIPROMPT_DISABLE_KEYRING", "1")
    from PySide6.QtWidgets import QApplication
    from settings_manager import SettingsManager
    from sync_settings_dialog import SyncSettingsDialog

    app = QApplication.instance() or QApplication([])
    st = Storage(tmp_path / "ui_data")
    sm = SettingsManager()
    dlg = SyncSettingsDialog(
        st,
        sm,
        state_store=SyncStateStore(tmp_path / "ui_data"),
        token_storage=TokenStorage(fallback_path=tmp_path / "tok.json"),
    )
    assert dlg.mode_combo.count() == 3
    dlg.mode_combo.setCurrentIndex(0)
    assert isinstance(dlg.build_backend_from_fields(), NullBackend)
    dlg.close()
