"""Accessible PySide6 Synchronization Settings & 3-Way Conflict Resolution Dialogs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore, QtWidgets

from library_import import ConflictChoice, ImportConflict
from sync_backend import (
    DEFAULT_NAMESPACE,
    FileSlotBackend,
    NullBackend,
    SLOT_IMPORT_MODES,
    ServerBackend,
    SyncBackend,
    SyncStateStore,
    TokenStorage,
    get_host_slot_name,
)


class ConflictResolutionDialog(QtWidgets.QDialog):
    """Three-way conflict resolution dialog (Keep Local / Save Copy / Take Remote)."""

    def __init__(self, conflicts: List[ImportConflict], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Synchronisierungs-Konflikte lösen")
        self.resize(760, 460)
        self.conflicts = list(conflicts)
        self._combos: List[QtWidgets.QComboBox] = []

        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            f"{len(self.conflicts)} abweichende(r) Eintrag/Einträge gefunden. "
            "Standard ist 'Lokal behalten' — eigene Daten werden niemals still überschrieben."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QtWidgets.QTableWidget(len(self.conflicts), 4, self)
        self.table.setHorizontalHeaderLabels(["Typ", "Titel", "Quelle", "Aktion"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        for row, conf in enumerate(self.conflicts):
            kind_label = "Prompt" if conf.kind == "prompt" else "Board"
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(kind_label))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(conf.title or conf.item_id))
            rev_info = f"{conf.source} (rev {conf.remote_rev})" if conf.remote_rev is not None else conf.source
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(rev_info))

            combo = QtWidgets.QComboBox(self)
            combo.addItem("Lokal behalten (Standard)", "keep_local")
            combo.addItem("Als neue Version / Kopie anlegen", "keep_copy")
            combo.addItem("Fremd-/Serverstand übernehmen", "take_remote")
            self._combos.append(combo)
            self.table.setCellWidget(row, 3, combo)

        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def resolutions(self) -> Dict[str, ConflictChoice]:
        out: Dict[str, ConflictChoice] = {}
        for conf, combo in zip(self.conflicts, self._combos):
            key = f"{conf.kind}:{conf.item_id}"
            out[key] = combo.currentData() or "keep_local"
        return out


class SyncSettingsDialog(QtWidgets.QDialog):
    """Unified Sync settings dialog supporting Off, File-Slot, and Server modes."""

    def __init__(
        self,
        storage,
        settings,
        *,
        state_store: Optional[SyncStateStore] = None,
        token_storage: Optional[TokenStorage] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.state_store = state_store or SyncStateStore(settings.get_data_path())
        self.token_storage = token_storage or TokenStorage()
        self.setWindowTitle("Synchronisierung")
        self.resize(680, 520)

        root = QtWidgets.QVBoxLayout(self)

        # Mode selector
        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(QtWidgets.QLabel("Sync-Modus:"))
        self.mode_combo = QtWidgets.QComboBox(self)
        self.mode_combo.addItem("Aus (nur lokal)", "off")
        self.mode_combo.addItem("Dateibasiert (Cloud-Ordner / Host-Slots)", "file")
        self.mode_combo.addItem("Server (kanonischer Sync-Server)", "server")
        mode_row.addWidget(self.mode_combo, 1)
        root.addLayout(mode_row)

        self.status_label = QtWidgets.QLabel("Status: Bereit")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # Stacked mode panels
        self.stack = QtWidgets.QStackedWidget(self)
        root.addWidget(self.stack, 1)

        # Page 0: Off
        off_page = QtWidgets.QWidget(self)
        off_layout = QtWidgets.QVBoxLayout(off_page)
        off_info = QtWidgets.QLabel(
            "Synchronisierung ist deaktiviert. Alle Prompts und Boards bleiben rein lokal im Datenordner."
        )
        off_info.setWordWrap(True)
        off_layout.addWidget(off_info)
        off_layout.addStretch(1)
        self.stack.addWidget(off_page)

        # Page 1: File-Slot mode
        file_page = QtWidgets.QWidget(self)
        file_layout = QtWidgets.QVBoxLayout(file_page)

        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(QtWidgets.QLabel("Sync-Ordner:"))
        self.sync_dir_edit = QtWidgets.QLineEdit(self)
        self.sync_dir_edit.setPlaceholderText("z. B. OneDrive / Nextcloud / Dropbox Sync-Ordner")
        self.btn_browse_dir = QtWidgets.QPushButton("Ordner wählen …", self)
        self.btn_browse_dir.clicked.connect(self._browse_sync_dir)
        dir_row.addWidget(self.sync_dir_edit, 1)
        dir_row.addWidget(self.btn_browse_dir)
        file_layout.addLayout(dir_row)

        try:
            host_label = get_host_slot_name()
        except Exception:
            host_label = "(unbekannt)"
        self.own_slot_label = QtWidgets.QLabel(f"Eigener Schreib-Slot: profiprompt@{host_label}.json (Single-Writer)")
        file_layout.addWidget(self.own_slot_label)

        self.slots_table = QtWidgets.QTableWidget(0, 4, self)
        self.slots_table.setHorizontalHeaderLabels(["Fremd-Slot", "App", "Stand", "Import-Modus"])
        self.slots_table.horizontalHeader().setStretchLastSection(True)
        self.slots_table.verticalHeader().setVisible(False)
        file_layout.addWidget(self.slots_table, 1)

        slot_btn_row = QtWidgets.QHBoxLayout()
        self.btn_refresh_slots = QtWidgets.QPushButton("Fremd-Slots neu einlesen", self)
        self.btn_refresh_slots.clicked.connect(self.refresh_foreign_slots)
        slot_btn_row.addWidget(self.btn_refresh_slots)
        slot_btn_row.addStretch(1)
        file_layout.addLayout(slot_btn_row)
        self.stack.addWidget(file_page)

        # Page 2: Server mode
        srv_page = QtWidgets.QWidget(self)
        srv_form = QtWidgets.QFormLayout(srv_page)

        self.server_url_edit = QtWidgets.QLineEdit(self)
        self.server_url_edit.setPlaceholderText("http://100.x.y.z:8765 oder https://sync.example.org")
        srv_form.addRow("Server-URL:", self.server_url_edit)

        self.namespace_edit = QtWidgets.QLineEdit(self)
        self.namespace_edit.setPlaceholderText(DEFAULT_NAMESPACE)
        srv_form.addRow("Namespace:", self.namespace_edit)

        self.token_edit = QtWidgets.QLineEdit(self)
        self.token_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Bearer API-Token (lokal geschützt gespeichert)")
        srv_form.addRow("API-Token:", self.token_edit)

        self.interval_spin = QtWidgets.QSpinBox(self)
        self.interval_spin.setRange(30, 3600)
        self.interval_spin.setSuffix(" s")
        srv_form.addRow("Abruf-Intervall:", self.interval_spin)

        self.stack.addWidget(srv_page)

        # Action row: Test Connection + Sync Now
        action_row = QtWidgets.QHBoxLayout()
        self.btn_test = QtWidgets.QPushButton("Verbindung testen", self)
        self.btn_test.clicked.connect(self.on_test_connection)
        self.btn_sync_now = QtWidgets.QPushButton("Jetzt synchronisieren", self)
        self.btn_sync_now.clicked.connect(self.on_sync_now)
        action_row.addWidget(self.btn_test)
        action_row.addWidget(self.btn_sync_now)
        action_row.addStretch(1)
        root.addLayout(action_row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._slot_combos: Dict[str, QtWidgets.QComboBox] = {}
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._load_initial()

    def _load_initial(self) -> None:
        mode = self.settings.get_sync_mode()
        idx = self.mode_combo.findData(mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.sync_dir_edit.setText(self.settings.get_sync_folder())
        self.server_url_edit.setText(self.settings.get_sync_server_url())
        self.namespace_edit.setText(self.settings.get_sync_namespace())
        self.interval_spin.setValue(self.settings.get_sync_interval_sec())
        self.token_edit.setText(self.token_storage.get_token())
        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        if mode == "file":
            self.stack.setCurrentIndex(1)
            self.refresh_foreign_slots()
        elif mode == "server":
            self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(0)

    def _browse_sync_dir(self) -> None:
        chosen = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Sync-Ordner auswählen", self.sync_dir_edit.text() or str(Path.home())
        )
        if chosen:
            self.sync_dir_edit.setText(chosen)
            self.refresh_foreign_slots()

    def build_backend_from_fields(self) -> SyncBackend:
        mode = self.mode_combo.currentData()
        if mode == "file":
            folder = self.sync_dir_edit.text().strip()
            if not folder:
                raise ValueError("Bitte zuerst einen Sync-Ordner wählen.")
            return FileSlotBackend(self.storage, self.state_store, sync_dir=Path(folder))
        if mode == "server":
            return ServerBackend(
                self.storage,
                self.state_store,
                server_url=self.server_url_edit.text().strip(),
                namespace=self.namespace_edit.text().strip() or DEFAULT_NAMESPACE,
                token_storage=self.token_storage,
                token_override=self.token_edit.text().strip(),
            )
        return NullBackend()

    def refresh_foreign_slots(self) -> None:
        self.slots_table.setRowCount(0)
        self._slot_combos.clear()
        folder = self.sync_dir_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            return
        backend = FileSlotBackend(self.storage, self.state_store, sync_dir=Path(folder))
        slots, warnings = backend.discover_foreign_slots()
        self.slots_table.setRowCount(len(slots))
        for row, slot in enumerate(slots):
            self.slots_table.setItem(row, 0, QtWidgets.QTableWidgetItem(slot.slot_key))
            self.slots_table.setItem(row, 1, QtWidgets.QTableWidgetItem(slot.app))
            self.slots_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{slot.updated_at[:19]} ({slot.item_count})"))
            combo = QtWidgets.QComboBox(self)
            combo.addItem("Nie", "never")
            combo.addItem("Einmalig", "once")
            combo.addItem("Beim Start", "on_start")
            c_idx = combo.findData(slot.import_mode)
            combo.setCurrentIndex(c_idx if c_idx >= 0 else 0)
            self.slots_table.setCellWidget(row, 3, combo)
            self._slot_combos[slot.slot_key] = combo
        self.slots_table.resizeColumnsToContents()
        if warnings:
            self.status_label.setText(f"Hinweis (A7): {'; '.join(warnings)}")

    def _persist_slot_modes(self) -> None:
        if not self._slot_combos:
            return
        state = self.state_store.load_state()
        modes = dict(state.get("slot_modes") or {})
        for slot_key, combo in self._slot_combos.items():
            val = combo.currentData()
            if val in SLOT_IMPORT_MODES:
                modes[slot_key] = val
        state["slot_modes"] = modes
        self.state_store.save_state(state)

    def on_test_connection(self) -> None:
        try:
            backend = self.build_backend_from_fields()
            res = backend.test_connection()
            prefix = "OK" if res.ok else "Fehler"
            self.status_label.setText(f"Status ({prefix}, {res.latency_ms:.0f} ms): {res.detail}")
        except Exception as exc:
            self.status_label.setText(f"Status (Fehler): {exc}")

    def on_sync_now(self) -> None:
        self._persist_slot_modes()
        try:
            backend = self.build_backend_from_fields()
            pull_res = backend.pull()
            conflicts = list(pull_res.conflicts)
            if conflicts:
                dlg = ConflictResolutionDialog(conflicts, self)
                if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    choices = dlg.resolutions()
                    pull_res = backend.pull(
                        conflict_resolver=lambda c: choices.get(f"{c.kind}:{c.item_id}", "keep_local")
                    )
            push_res = backend.push()
            self.status_label.setText(
                f"Synchronisiert: Pull +{pull_res.upserts}/-{pull_res.tombstones}, "
                f"Push {len(push_res.applied_revs)}, Offline-Queue {push_res.queued_offline}, "
                f"Konflikte {len(pull_res.conflicts) + len(push_res.conflicts)}."
            )
        except Exception as exc:
            self.status_label.setText(f"Sync fehlgeschlagen: {exc}")

    def save_and_accept(self) -> None:
        self._persist_slot_modes()
        self.settings.set_sync_mode(self.mode_combo.currentData() or "off")
        self.settings.set_sync_folder(self.sync_dir_edit.text().strip())
        self.settings.set_sync_server_url(self.server_url_edit.text().strip())
        self.settings.set_sync_namespace(self.namespace_edit.text().strip() or DEFAULT_NAMESPACE)
        self.settings.set_sync_interval_sec(int(self.interval_spin.value()))
        token = self.token_edit.text().strip()
        if token:
            self.token_storage.set_token(token)
        self.accept()
