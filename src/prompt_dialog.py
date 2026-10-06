# widgets/prompt_dialog.py
from PySide6 import QtWidgets, QtCore
from typing import Optional, List
from models import Prompt, Version, gen_id, now_iso
from storage import Storage
from storage_actions import report_storage_errors
from dataclasses import replace
from i18n import tr

class PromptDialog(QtWidgets.QDialog):
    def __init__(self, storage: Storage, prompt: Optional[Prompt] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Prompt bearbeiten") if prompt else tr("Prompt erstellen"))
        self.setModal(True)
        self.storage = storage
        self.prompt = prompt

        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setAccessibleName(tr("Titel"))
        self.title_edit.setAccessibleDescription(tr("Titel des Prompts (Pflichtfeld)"))
        self.title_edit.setPlaceholderText(tr("Titel des Prompts eingeben …"))

        self.purpose_edit = QtWidgets.QLineEdit()
        self.purpose_edit.setAccessibleName(tr("Zweck"))
        self.purpose_edit.setAccessibleDescription(tr("Zweck und Verwendungsziel des Prompts"))
        self.purpose_edit.setPlaceholderText(tr("Verwendungszweck beschreiben …"))

        self.tags_edit = QtWidgets.QLineEdit()
        self.tags_edit.setAccessibleName(tr("Tags"))
        self.tags_edit.setAccessibleDescription(tr("Kommagetrennte Liste von Schlagwörtern"))
        self.tags_edit.setPlaceholderText(tr("z. B. Coding, Refactoring, Python"))

        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setAccessibleName(tr("Prompt-Text"))
        self.text_edit.setAccessibleDescription(tr("Vollständiger Prompt-Text (Pflichtfeld)"))
        self.text_edit.setPlaceholderText(tr("Hier den Prompt-Text formulieren …"))

        self.result_edit = QtWidgets.QPlainTextEdit()
        self.result_edit.setAccessibleName(tr("Ergebnis"))
        self.result_edit.setAccessibleDescription(tr("Zuletzt erzieltes Testergebnis oder Modellausgabe"))
        self.result_edit.setPlaceholderText(tr("Optionale Modellausgabe oder Notizen …"))

        lbl_title = QtWidgets.QLabel(tr("Titel*"))
        lbl_title.setBuddy(self.title_edit)
        lbl_purpose = QtWidgets.QLabel(tr("Zweck"))
        lbl_purpose.setBuddy(self.purpose_edit)
        lbl_tags = QtWidgets.QLabel(tr("Tags (Komma)"))
        lbl_tags.setBuddy(self.tags_edit)
        lbl_text = QtWidgets.QLabel(tr("Prompt-Text*"))
        lbl_text.setBuddy(self.text_edit)
        lbl_result = QtWidgets.QLabel(tr("Ergebnis"))
        lbl_result.setBuddy(self.result_edit)

        form = QtWidgets.QFormLayout()
        form.addRow(lbl_title, self.title_edit)
        form.addRow(lbl_purpose, self.purpose_edit)
        form.addRow(lbl_tags, self.tags_edit)
        form.addRow(lbl_text, self.text_edit)
        form.addRow(lbl_result, self.result_edit)

        # Versionenliste (readonly)
        self.versions_list = QtWidgets.QListWidget()
        self.versions_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.versions_list.setAccessibleName(tr("Versionen-Liste"))
        self.versions_list.setAccessibleDescription(tr("Übersicht aller Versionen dieses Prompts"))
        group_versions = QtWidgets.QGroupBox(tr("Versionen"))
        group_versions.setAccessibleName(tr("Versionen-Gruppe"))
        vlay = QtWidgets.QVBoxLayout(group_versions)
        vlay.addWidget(self.versions_list)

        # Buttons
        btn_save = QtWidgets.QPushButton(tr("Speichern"))
        btn_save.setDefault(True)
        btn_save.setAccessibleName(tr("Speichern"))
        btn_save.setAccessibleDescription(tr("Speichert die Änderungen und schließt den Dialog"))
        btn_save.setToolTip(tr("Prompt speichern (Enter)"))

        btn_cancel = QtWidgets.QPushButton(tr("Abbrechen"))
        btn_cancel.setAccessibleName(tr("Abbrechen"))
        btn_cancel.setAccessibleDescription(tr("Verwirft Änderungen und schließt den Dialog"))
        btn_cancel.setToolTip(tr("Abbrechen (Esc)"))

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(group_versions)
        layout.addLayout(btns)

        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.on_save)

        if self.prompt:
            self._populate()

    def _populate(self):
        p = self.prompt
        self.title_edit.setText(p.title or "")
        self.purpose_edit.setText(p.purpose or "")
        tag_items = [
            str(t).strip() for t in (p.tags or []) if t is not None and str(t).strip()
        ]
        self.tags_edit.setText(", ".join(tag_items))
        self.text_edit.setPlainText(p.text or "")
        self.result_edit.setPlainText(p.last_result or "")
        self.versions_list.clear()
        versions = [v for v in (p.versions or []) if v is not None]
        for v in sorted(versions, key=lambda x: getattr(x, "version_number", 0) or 0):
            v_num = getattr(v, "version_number", None) or "?"
            item = QtWidgets.QListWidgetItem(f"v{v_num} — {v.title or ''}")
            item.setToolTip(v.text or "")
            self.versions_list.addItem(item)

    @report_storage_errors
    def on_save(self):
        title = self.title_edit.text().strip()
        text = self.text_edit.toPlainText().strip()
        if not title or not text:
            QtWidgets.QMessageBox.warning(self, tr("Fehler"), tr("Titel und Prompt-Text sind Pflichtfelder."))
            return
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        purpose = self.purpose_edit.text().strip()
        result = self.result_edit.toPlainText().strip()

        if self.prompt:
            edited = replace(self.prompt, title=title, purpose=purpose, tags=tags,
                             text=text, last_result=result, updated_at=now_iso())
            self.storage.upsert_prompt(edited)
            self.prompt = edited
        else:
            from models import Prompt as P
            p = P(
                id=gen_id(),
                title=title,
                purpose=purpose,
                text=text,
                tags=tags,
                last_result=result
            )
            self.storage.upsert_prompt(p)
            self.prompt = p
        self.accept()

class VersionDialog(QtWidgets.QDialog):
    def __init__(self, storage: Storage, prompt: Prompt, version: Optional[Version] = None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.prompt = prompt
        self.version = version  # None => Neuerstellung, sonst Bearbeitung

        is_edit = self.version is not None
        self.setWindowTitle(tr("Version bearbeiten") if is_edit else tr("Neue Version anlegen"))
        self.setModal(True)

        # Kontext/Status
        p_title = self.prompt.title or "" if self.prompt else ""
        v_title = (self.version.title or "") if is_edit and self.version else ""
        v_num = getattr(self.version, "version_number", None) or "?" if is_edit and self.version else ""
        context_lbl = QtWidgets.QLabel(
            tr("Prompt: {title}", title=p_title)
            + ("\n" + tr("Bearbeite: v{num} — {title}", num=v_num, title=v_title) if is_edit else "")
        )
        context_lbl.setStyleSheet("color:#666;")
        context_lbl.setAccessibleName(tr("Versions-Kontext"))
        context_lbl.setAccessibleDescription(tr("Zugeordneter Prompt: {title}", title=p_title))

        # Felder
        raw_tags = (self.version.tags if is_edit and self.version else (getattr(self.prompt, "tags", []) or []))
        tag_items = [
            str(t).strip() for t in (raw_tags or []) if t is not None and str(t).strip()
        ]
        self.title_edit = QtWidgets.QLineEdit((self.version.title or "") if is_edit and self.version else "")
        self.title_edit.setAccessibleName(tr("Versionstitel"))
        self.title_edit.setAccessibleDescription(tr("Titel dieser Prompt-Version (Pflichtfeld)"))
        self.title_edit.setPlaceholderText(tr("Titel der Version …"))

        self.tags_edit = QtWidgets.QLineEdit(", ".join(tag_items))
        self.tags_edit.setAccessibleName(tr("Tags"))
        self.tags_edit.setAccessibleDescription(tr("Kommagetrennte Liste von Schlagwörtern"))
        self.tags_edit.setPlaceholderText(tr("z. B. v2, überarbeitet, kurz"))

        self.text_edit = QtWidgets.QPlainTextEdit(
            (self.version.text or "") if is_edit and self.version else (getattr(self.prompt, "text", "") or "")
        )
        self.text_edit.setAccessibleName(tr("Prompt-Text"))
        self.text_edit.setAccessibleDescription(tr("Vollständiger Prompt-Text dieser Version (Pflichtfeld)"))
        self.text_edit.setPlaceholderText(tr("Prompt-Text für diese Version formulieren …"))

        self.result_edit = QtWidgets.QPlainTextEdit(
            (getattr(self.version, "result", "") or "") if is_edit and self.version else ""
        )
        self.result_edit.setAccessibleName(tr("Ergebnis"))
        self.result_edit.setAccessibleDescription(tr("Testergebnis oder Notizen dieser Version"))
        self.result_edit.setPlaceholderText(tr("Optionale Modellausgabe für diese Version …"))

        lbl_title = QtWidgets.QLabel(tr("Titel*"))
        lbl_title.setBuddy(self.title_edit)
        lbl_tags = QtWidgets.QLabel(tr("Tags (Komma)"))
        lbl_tags.setBuddy(self.tags_edit)
        lbl_text = QtWidgets.QLabel(tr("Prompt-Text*"))
        lbl_text.setBuddy(self.text_edit)
        lbl_result = QtWidgets.QLabel(tr("Ergebnis"))
        lbl_result.setBuddy(self.result_edit)

        form = QtWidgets.QFormLayout()
        form.addRow(lbl_title, self.title_edit)
        form.addRow(lbl_tags, self.tags_edit)
        form.addRow(lbl_text, self.text_edit)
        form.addRow(lbl_result, self.result_edit)

        # Buttons
        btn_cancel = QtWidgets.QPushButton(tr("Abbrechen"))
        btn_cancel.setAccessibleName(tr("Abbrechen"))
        btn_cancel.setAccessibleDescription(tr("Verwirft Eingaben und schließt den Dialog"))
        btn_cancel.setToolTip(tr("Abbrechen (Esc)"))

        if is_edit:
            btn_save_update = QtWidgets.QPushButton(tr("Speichern"))
            btn_save_update.setDefault(True)
            btn_save_update.setAccessibleName(tr("Speichern"))
            btn_save_update.setAccessibleDescription(tr("Speichert die Änderungen an dieser Version"))
            btn_save_update.setToolTip(tr("Version aktualisieren (Enter)"))

            btn_save_new = QtWidgets.QPushButton(tr("Als neue Version speichern"))
            btn_save_new.setAccessibleName(tr("Als neue Version speichern"))
            btn_save_new.setAccessibleDescription(tr("Erstellt eine neue Version mit fortlaufender Nummer"))
            btn_save_new.setToolTip(tr("Als neue Version anlegen"))
        else:
            btn_save_create = QtWidgets.QPushButton(tr("Version erstellen"))
            btn_save_create.setDefault(True)
            btn_save_create.setAccessibleName(tr("Version erstellen"))
            btn_save_create.setAccessibleDescription(tr("Erstellt eine neue Version dieses Prompts"))
            btn_save_create.setToolTip(tr("Version anlegen (Enter)"))

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        if is_edit:
            btns.addWidget(btn_save_new)
            btns.addWidget(btn_save_update)
        else:
            btns.addWidget(btn_save_create)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(context_lbl)
        layout.addLayout(form)
        layout.addLayout(btns)

        btn_cancel.clicked.connect(self.reject)
        if is_edit:
            btn_save_update.clicked.connect(self._on_save_update)
            btn_save_new.clicked.connect(self._on_save_create)
        else:
            btn_save_create.clicked.connect(self._on_save_create)

    def _validate(self) -> Optional[tuple[str, list[str], str, str]]:
        title = self.title_edit.text().strip()
        text = self.text_edit.toPlainText().strip()
        if not title or not text:
            QtWidgets.QMessageBox.warning(self, tr("Fehler"), tr("Titel und Prompt-Text sind Pflichtfelder."))
            return None
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        result = self.result_edit.toPlainText().strip()
        return title, tags, text, result

    @report_storage_errors
    def _on_save_update(self):
        data = self._validate()
        if not data:
            return
        title, tags, text, result = data
        # Erst nach erfolgreichem Speichern geteilte Modelle aktualisieren.
        v = replace(self.version, title=title, tags=tags, text=text,
                    result=result, updated_at=now_iso())

        pid = self.prompt.id if self.prompt else v.prompt_id
        if not self.storage.upsert_version(pid, v):
            QtWidgets.QMessageBox.warning(self, tr("Speichern fehlgeschlagen"), tr("Der zugehörige Prompt wurde nicht gefunden."))
            return
        self.version = v

        # Bugsweep 2026-09-18 BUG-VD01: self.prompt.versions synchronisieren, falls
        # self.version als separates Objekt geladen wurde (z.B. get_prompt vs get_version)
        if self.prompt:
            idx = next((i for i, ev in enumerate(self.prompt.versions) if ev.id == v.id), -1)
            if idx >= 0:
                self.prompt.versions[idx] = v
            else:
                self.prompt.versions.append(v)
            self.prompt.updated_at = now_iso()

        self.accept()

    @report_storage_errors
    def _on_save_create(self):
        data = self._validate()
        if not data:
            return
        title, tags, text, result = data

        vn = self.storage.next_version_number(self.prompt.id)
        new_v = Version(
            id=gen_id(),
            prompt_id=self.prompt.id,
            version_number=vn,
            title=title,
            text=text,
            tags=tags,
            result=result,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        if not self.storage.add_version(self.prompt.id, new_v):
            QtWidgets.QMessageBox.warning(self, tr("Speichern fehlgeschlagen"), tr("Der zugehörige Prompt wurde nicht gefunden."))
            return
        if self.prompt:
            self.prompt.versions.append(new_v)
            self.prompt.updated_at = now_iso()
        self.accept()
