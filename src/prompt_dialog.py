# widgets/prompt_dialog.py
from PySide6 import QtWidgets, QtCore
from typing import Optional, List
from models import Prompt, Version, gen_id, now_iso
from storage import Storage

class PromptDialog(QtWidgets.QDialog):
    def __init__(self, storage: Storage, prompt: Optional[Prompt] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt bearbeiten" if prompt else "Prompt erstellen")
        self.storage = storage
        self.prompt = prompt

        self.title_edit = QtWidgets.QLineEdit()
        self.purpose_edit = QtWidgets.QLineEdit()
        self.tags_edit = QtWidgets.QLineEdit()
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.result_edit = QtWidgets.QPlainTextEdit()

        form = QtWidgets.QFormLayout()
        form.addRow("Titel*", self.title_edit)
        form.addRow("Zweck", self.purpose_edit)
        form.addRow("Tags (Komma)", self.tags_edit)
        form.addRow("Prompt-Text*", self.text_edit)
        form.addRow("Ergebnis", self.result_edit)

        # Versionenliste (readonly)
        self.versions_list = QtWidgets.QListWidget()
        self.versions_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        group_versions = QtWidgets.QGroupBox("Versionen")
        vlay = QtWidgets.QVBoxLayout(group_versions)
        vlay.addWidget(self.versions_list)

        # Buttons
        btn_save = QtWidgets.QPushButton("Speichern")
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
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
        self.title_edit.setText(p.title)
        self.purpose_edit.setText(p.purpose)
        self.tags_edit.setText(", ".join(p.tags))
        self.text_edit.setPlainText(p.text)
        self.result_edit.setPlainText(p.last_result)
        self.versions_list.clear()
        for v in sorted(p.versions, key=lambda x: x.version_number):
            item = QtWidgets.QListWidgetItem(f"v{v.version_number} — {v.title}")
            item.setToolTip(v.text)
            self.versions_list.addItem(item)

    def on_save(self):
        title = self.title_edit.text().strip()
        text = self.text_edit.toPlainText().strip()
        if not title or not text:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Titel und Prompt-Text sind Pflichtfelder.")
            return
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        purpose = self.purpose_edit.text().strip()
        result = self.result_edit.toPlainText().strip()

        if self.prompt:
            self.prompt.title = title
            self.prompt.purpose = purpose
            self.prompt.tags = tags
            self.prompt.text = text
            self.prompt.last_result = result
            self.prompt.updated_at = now_iso()
            self.storage.upsert_prompt(self.prompt)
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
        self.setWindowTitle("Version bearbeiten" if is_edit else "Neue Version anlegen")

        # Kontext/Status
        context_lbl = QtWidgets.QLabel(
            f"Prompt: {self.prompt.title}"
            + (f"\nBearbeite: v{self.version.version_number} — {self.version.title}" if is_edit else "")
        )
        context_lbl.setStyleSheet("color:#666;")

        # Felder
        self.title_edit = QtWidgets.QLineEdit(self.version.title if is_edit else "")
        self.tags_edit = QtWidgets.QLineEdit(", ".join(self.version.tags if is_edit else (self.prompt.tags or [])))
        self.text_edit = QtWidgets.QPlainTextEdit(self.version.text if is_edit else (self.prompt.text or ""))
        self.result_edit = QtWidgets.QPlainTextEdit(self.version.result if is_edit else "")

        form = QtWidgets.QFormLayout()
        form.addRow("Titel*", self.title_edit)
        form.addRow("Tags (Komma)", self.tags_edit)
        form.addRow("Prompt-Text*", self.text_edit)
        form.addRow("Ergebnis", self.result_edit)

        # Buttons
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        if is_edit:
            btn_save_update = QtWidgets.QPushButton("Speichern")
            btn_save_new = QtWidgets.QPushButton("Als neue Version speichern")
        else:
            btn_save_create = QtWidgets.QPushButton("Version erstellen")

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
            QtWidgets.QMessageBox.warning(self, "Fehler", "Titel und Prompt-Text sind Pflichtfelder.")
            return None
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        result = self.result_edit.toPlainText().strip()
        return title, tags, text, result

    def _on_save_update(self):
        data = self._validate()
        if not data:
            return
        title, tags, text, result = data
        # In-place bearbeiten
        v = self.version
        v.title = title
        v.tags = tags
        v.text = text
        v.result = result
        v.updated_at = now_iso()

        self.prompt.updated_at = now_iso()
        self.storage.upsert_prompt(self.prompt)  # gesamte Prompt-Struktur inkl. Versionen speichern
        self.accept()

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
        self.storage.add_version(self.prompt.id, new_v)
        self.accept()
