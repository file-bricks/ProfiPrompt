from PySide6 import QtWidgets
from models import CopyMode
from settings_manager import SettingsManager

class CopySettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kopier-Einstellungen")
        self.settings = settings

        # ComboBox mit Label und zugehörigem Enum-Wert
        self.mode_combo = QtWidgets.QComboBox()
        for label, mode in [
            ("Nur Titel",       CopyMode.TITLE.value),
            ("Nur Prompt-Text", CopyMode.TEXT.value),
            ("Nur Ergebnis",    CopyMode.RESULT.value),
            ("Alles",           CopyMode.ALL.value),
        ]:
            self.mode_combo.addItem(label, mode)

        # Aktuellen Modus vorwählen
        current = self.settings.get_copy_mode().value
        idx = self.mode_combo.findData(current)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        # Checkbox für Metadaten
        self.chk_meta = QtWidgets.QCheckBox("Metadaten (Tags) hinzufügen")
        self.chk_meta.setChecked(self.settings.get_include_metadata())

        # Layout
        form = QtWidgets.QFormLayout()
        form.addRow("Kopiermodus:", self.mode_combo)
        form.addRow("",             self.chk_meta)

        btn_ok     = QtWidgets.QPushButton("OK")
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addLayout(btns)

    def accept(self) -> None:
        mode_str = self.mode_combo.currentData()
        mode     = CopyMode(mode_str)
        self.settings.set_copy_mode(mode)
        self.settings.set_include_metadata(self.chk_meta.isChecked())
        super().accept()
