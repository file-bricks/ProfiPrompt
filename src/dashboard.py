# dashboard.py

from __future__ import annotations
import json
from typing import List, Optional

from PySide6 import QtWidgets, QtCore, QtGui
from models import Prompt, Version, now_iso
from storage import Storage
from settings_manager import SettingsManager
from event_bus import bus
from prompt_dialog import PromptDialog, VersionDialog
from clipboard_manager import ClipboardManager
from pdf_exporter import (
    export_single_prompt,
    export_single_version,
    export_single_prompt_with_versions,
)

import os as _os
_ICON_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "icons")



class PromptTree(QtWidgets.QTreeWidget):
    MIME_TYPE = "application/x-prompt-item"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(
            ["Titel", "Zweck", "Tags", "Erstellt", "Aktualisiert", "", ""]
        )
        # Letzte beiden Spalten für Icons freihalten
        self.setColumnCount(7)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        
        
    def mimeTypes(self) -> List[str]:
        return [self.MIME_TYPE]

    def mimeData(self, items: List[QtWidgets.QTreeWidgetItem]) -> QtCore.QMimeData:
        tup = items[0].data(0, QtCore.Qt.UserRole)
        blob = json.dumps(tup)
        md = QtCore.QMimeData()
        md.setData(self.MIME_TYPE, blob.encode("utf-8"))
        return md

    def supportedDragActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.CopyAction

class DashboardWidget(QtWidgets.QWidget):
    def __init__(
        self,
        storage: Storage,
        settings: SettingsManager,
        parent=None,
    ):
        super().__init__(parent)

        self.storage = storage
        self.settings = settings
        self.clip = ClipboardManager(settings)

        # --- Filter Controls ---
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Suche in Titel/Text/Tags …")

        self.tag_combo = QtWidgets.QComboBox()
        self.tag_combo.addItem("Alle Tags", "")

        self.date_from = QtWidgets.QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.date_to = QtWidgets.QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        sentinel = QtCore.QDate(1900, 1, 1)
        for d in (self.date_from, self.date_to):
            d.setSpecialValueText("—")
            d.setMinimumDate(sentinel)
            d.setMaximumDate(QtCore.QDate(2100, 1, 1))
            d.setDate(sentinel)
        self._date_sentinel = sentinel

        self.btn_clear = QtWidgets.QPushButton("Filter zurücksetzen")

        # Connect filter signals to reload()
        self.search_edit.textChanged.connect(self.reload)
        self.tag_combo.currentIndexChanged.connect(self.reload)
        self.date_from.dateChanged.connect(self.reload)
        self.date_to.dateChanged.connect(self.reload)
        self.btn_clear.clicked.connect(self._clear_filters)
        
        # --- Prompt Tree ---
        self.tree = PromptTree(self)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        # --- Layout ---
        filter_layout = QtWidgets.QGridLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Suche:"), 0, 0)
        filter_layout.addWidget(self.search_edit, 0, 1)
        filter_layout.addWidget(QtWidgets.QLabel("Tag:"), 0, 2)
        filter_layout.addWidget(self.tag_combo, 0, 3)
        filter_layout.addWidget(QtWidgets.QLabel("Von:"), 0, 4)
        filter_layout.addWidget(self.date_from, 0, 5)
        filter_layout.addWidget(QtWidgets.QLabel("Bis:"), 0, 6)
        filter_layout.addWidget(self.date_to, 0, 7)
        filter_layout.addWidget(self.btn_clear, 0, 8)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.tree)

        # Listen for external prompt changes
        bus.promptsChanged.connect(self.reload)

        # Initial load
        self.reload()

    def _clear_filters(self):
        self.search_edit.clear()
        self.tag_combo.setCurrentIndex(0)
        self.date_from.setDate(self._date_sentinel)
        self.date_to.setDate(self._date_sentinel)
        self.reload()


    def reload(self):
        """Neu laden aller Prompts + Versionen und Icons setzen."""
        self.tree.clear()
        prompts = self.storage.load_prompts()

        # Update tag combo (preserve current selection)
        current_tag = self.tag_combo.currentData()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("Alle Tags", "")
        for tag in self._collect_tags(prompts):
            self.tag_combo.addItem(tag, tag)
        idx = self.tag_combo.findData(current_tag)
        self.tag_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.tag_combo.blockSignals(False)

        # Apply text filter
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            prompts = [
                p for p in prompts
                if search_text in (p.title or "").lower()
                or search_text in (p.text or "").lower()
                or any(search_text in t.lower() for t in (p.tags or []))
            ]

        # Apply tag filter
        selected_tag = self.tag_combo.currentData()
        if selected_tag:
            prompts = [
                p for p in prompts
                if selected_tag in (p.tags or [])
                or any(selected_tag in (v.tags or []) for v in p.versions)
            ]

        # Apply date filter
        date_from = self._date_or_none(self.date_from)
        date_to = self._date_or_none(self.date_to)
        if date_from or date_to:
            filtered = []
            for p in prompts:
                p_date = QtCore.QDate.fromString(
                    (p.updated_at or "").split("T")[0], "yyyy-MM-dd"
                )
                if date_from and p_date < date_from:
                    continue
                if date_to and p_date > date_to:
                    continue
                filtered.append(p)
            prompts = filtered

        def safe_date(s: Optional[str]) -> str:
            return s.split("T")[0] if s else ""

        PAPERCLIP_ICON = _os.path.join(_ICON_DIR, "paperclip.ico")
        CLIPBOARD_ICON = _os.path.join(_ICON_DIR, "clipboard.ico")

        for p in sorted(prompts, key=lambda x: x.updated_at or "", reverse=True):
            # Top‐Level‐Item für Prompt
            parent = QtWidgets.QTreeWidgetItem(self.tree)
            parent.setText(0, p.title or "")
            parent.setText(1, p.purpose or "")
            parent.setText(2, ", ".join(p.tags or []))
            parent.setText(3, safe_date(p.created_at))
            parent.setText(4, safe_date(p.updated_at))
            parent.setData(0, QtCore.Qt.UserRole, ("prompt", p.id))

            # Büroklammer‐Icon in Spalte 5, wenn Versionen existieren
            if p.versions:
                parent.setIcon(5, QtGui.QIcon(PAPERCLIP_ICON))

            # Clipboard‐Button in Spalte 6
            btn_copy = QtWidgets.QToolButton()
            btn_copy.setIcon(QtGui.QIcon(CLIPBOARD_ICON))
            btn_copy.setAutoRaise(True)
            btn_copy.clicked.connect(lambda _, pid=p.id: self._copy_prompt(pid))
            self.tree.setItemWidget(parent, 6, btn_copy)

            # Child‐Items für jede Version
            for v in sorted(p.versions, key=lambda x: x.version_number):
                child = QtWidgets.QTreeWidgetItem(parent)
                child.setText(0, f"v{v.version_number} — {v.title or ''}")
                child.setText(1, "")
                child.setText(2, ", ".join(v.tags or []))
                child.setText(3, safe_date(v.created_at))
                child.setText(4, safe_date(v.updated_at))
                child.setData(0, QtCore.Qt.UserRole, ("version", p.id, v.id))

                # Clipboard‐Button für die Version in Spalte 6
                btn_ver_copy = QtWidgets.QToolButton()
                btn_ver_copy.setIcon(QtGui.QIcon(CLIPBOARD_ICON))
                btn_ver_copy.setAutoRaise(True)
                btn_ver_copy.clicked.connect(
                    lambda _, pid=p.id, vid=v.id: self._copy_version(pid, vid)
                )
                self.tree.setItemWidget(child, 6, btn_ver_copy)

        # alle Zweige ausklappen und Spalten automatisch anpassen
        self.tree.expandAll()
        for col in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(col)

    def open_context_menu(self, pos: QtCore.QPoint):
        """
        Zeigt Kontextmenü:
         - Klick auf einen Eintrag: Aktionen für Prompt/Version
         - Klick auf leeren Bereich: 'Neuen Prompt hinzufügen'
        """
        item = self.tree.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        if not item:
            # Leerer Bereich
            menu.addAction("Neuen Prompt hinzufügen", self.create_prompt)
            menu.exec(self.tree.viewport().mapToGlobal(pos))
            return

        # Eintrag angeklickt: Prompt-/Version‐Menü
        kind, pid, *rest = item.data(0, QtCore.Qt.UserRole)
        vid = rest[0] if rest else None
        p = self.storage.get_prompt(pid)
        v = self.storage.get_version(pid, vid) if kind == "version" and vid else None

        # Copy Aktionen
        if kind == "prompt":
            act_copy       = menu.addAction("Prompt kopieren")
            act_copy_full  = menu.addAction("Prompt inkl. Versionen kopieren")
        else:
            act_copy       = menu.addAction("Version kopieren")
        menu.addSeparator()

        # Neue Version / Prompt
        if kind == "prompt":
            act_new_ver = menu.addAction("Neue Version anlegen")
        act_new_p = menu.addAction("Neuer Prompt")
        menu.addSeparator()

        # Editieren
        act_edit = menu.addAction("Bearbeiten")
        menu.addSeparator()

        # Export
        if kind == "prompt":
            menu.addAction("Prompt exportieren (TXT)")
            menu.addAction("Prompt exportieren (PDF)")
            menu.addAction("Prompt+Versionen exportieren (TXT)")
            menu.addAction("Prompt+Versionen exportieren (PDF)")
        else:
            menu.addAction("Version exportieren (TXT)")
            menu.addAction("Version exportieren (PDF)")
        menu.addSeparator()

        # Löschen
        act_delete = menu.addAction("Löschen")

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        # -- Handle Aktionen --
        if chosen == act_copy:
            txt = self.clip.build_copy_text(p, v)
            self.clip.copy_to_clipboard(self.tree, txt)
        elif kind == "prompt" and chosen == act_copy_full:
            parts = [self.clip.build_copy_text(p)]
            for vv in sorted(p.versions, key=lambda x: x.version_number):
                parts.append(self.clip.build_copy_text(p, vv))
            self.clip.copy_to_clipboard(self.tree, "\n\n".join(parts))
        elif kind == "prompt" and chosen == act_new_ver:
            dlg = VersionDialog(self.storage, p, None, self)
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                bus.promptsChanged.emit()
        elif chosen == act_new_p:
            self.create_prompt()
        elif chosen == act_edit:
            if kind == "prompt":
                dlg = PromptDialog(self.storage, p, self)
            else:
                dlg = VersionDialog(self.storage, p, v, self)
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                bus.promptsChanged.emit()
        elif chosen.text().startswith("Prompt exportieren") and "TXT" in chosen.text():
            self._export_prompt_txt(p)
        elif chosen.text().startswith("Prompt exportieren") and "PDF" in chosen.text():
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "PDF speichern", f"{p.title}.pdf", "PDF-Datei (*.pdf)")
            if path:
                export_single_prompt(p, self.settings, path, self)
        elif chosen.text().startswith("Prompt+Versionen exportieren") and "TXT" in chosen.text():
            self._export_bundle_txt(p)
        elif chosen.text().startswith("Prompt+Versionen exportieren") and "PDF" in chosen.text():
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "PDF speichern", f"{p.title}_all.pdf", "PDF-Datei (*.pdf)")
            if path:
                export_single_prompt_with_versions(p, self.settings, path, self)
        elif kind == "version" and chosen.text().startswith("Version exportieren") and "TXT" in chosen.text():
            self._export_version_txt(v)
        elif kind == "version" and chosen.text().startswith("Version exportieren") and "PDF" in chosen.text():
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "PDF speichern", f"{v.title}.pdf", "PDF-Datei (*.pdf)")
            if path:
                export_single_version(v, path, self)
        elif chosen == act_delete:
            if kind == "prompt":
                if QtWidgets.QMessageBox.question(
                    self, "Löschen", f"Prompt „{p.title}“ wirklich löschen?"
                ) == QtWidgets.QMessageBox.Yes:
                    self.storage.delete_prompt(p.id)
                    bus.promptsChanged.emit()
            else:
                if QtWidgets.QMessageBox.question(
                    self, "Löschen",
                    f"Version „v{v.version_number} – {v.title}“ wirklich löschen?"
                ) == QtWidgets.QMessageBox.Yes:
                    p.versions = [x for x in p.versions if x.id != v.id]
                    p.updated_at = now_iso()
                    self.storage.upsert_prompt(p)
                    bus.promptsChanged.emit()

    # -- Copy‐Shortcuts für Tree‐Icons -------------------------------

    def _copy_prompt(self, prompt_id: str):
        p = self.storage.get_prompt(prompt_id)
        txt = self.clip.build_copy_text(p)
        self.clip.copy_to_clipboard(self.tree, txt)

    def _copy_version(self, prompt_id: str, version_id: str):
        p = self.storage.get_prompt(prompt_id)
        v = self.storage.get_version(prompt_id, version_id)
        txt = self.clip.build_copy_text(p, v)
        self.clip.copy_to_clipboard(self.tree, txt)

    # -- Export‐Helper & create_prompt, _export_prompt_txt, _export_version_txt, _export_bundle_txt,
    #    create_prompt remain unchanged, ebenso get_current_prompt/get_current_version --

  
       # --- Helpers for MainWindow ---
    def get_current_prompt(self) -> Optional[Prompt]:
        it = self.tree.currentItem()
        if not it:
            return None
        data = it.data(0, QtCore.Qt.UserRole)
        if data and data[0] == "prompt":
            return self.storage.get_prompt(data[1])
        return None

    def get_current_version(self):
        it = self.tree.currentItem()
        if not it:
            return None
        data = it.data(0, QtCore.Qt.UserRole)
        if data and data[0] == "version":
            _, pid, vid = data
            return self.storage.get_version(pid, vid)
        return None


    def _collect_tags(self, prompts: List[Prompt]) -> List[str]:
        tags = set()
        for p in prompts:
            tags.update(t for t in (p.tags or []) if t)
            for v in p.versions:
                tags.update(t for t in (v.tags or []) if t)
        return sorted(tags)


    def _date_or_none(self, d_edit: QtWidgets.QDateEdit) -> Optional[QtCore.QDate]:
        d = d_edit.date()
        return None if d == self._date_sentinel else d

    # --- Double‐click edits ---
    def _on_item_double_clicked(
        self,
        item: QtWidgets.QTreeWidgetItem,
        column: int
    ):
        data = item.data(0, QtCore.Qt.UserRole)
        if not data:
            return

        kind, pid, *rest = data
        p = self.storage.get_prompt(pid)
        if not p:
            return

        if kind == "prompt":
            dlg = PromptDialog(self.storage, p, self)
        else:
            vid = rest[0]
            v = self.storage.get_version(pid, vid)
            dlg = VersionDialog(self.storage, p, v, self)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            bus.promptsChanged.emit()
            
    # --- Export‐Helpers ---
    def _export_prompt_txt(self, p: Prompt):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "TXT speichern", f"{p.title}.txt", "Textdatei (*.txt)"
        )
        if not path:
            return
        text = self.clip.build_copy_text(p)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QtWidgets.QMessageBox.information(self, "Export", "Prompt erfolgreich exportiert.")

    def _export_version_txt(self, v):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "TXT speichern", f"{v.title}.txt", "Textdatei (*.txt)"
        )
        if not path:
            return
        p = self.storage.get_prompt(v.prompt_id)
        text = self.clip.build_copy_text(p, v)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QtWidgets.QMessageBox.information(self, "Export", "Version erfolgreich exportiert.")

    def _export_bundle_txt(self, p: Prompt):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "TXT speichern", f"{p.title}_all.txt", "Textdatei (*.txt)"
        )
        if not path:
            return
        parts = [self.clip.build_copy_text(p)]
        for ver in sorted(p.versions, key=lambda x: x.version_number or 0):
            parts.append(self.clip.build_copy_text(p, ver))
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(parts))
        QtWidgets.QMessageBox.information(self, "Export", "Bundle erfolgreich exportiert.")


    # --- Create Prompt helper ---
    def create_prompt(self):
        dlg = PromptDialog(self.storage, None, self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            bus.promptsChanged.emit()
            


