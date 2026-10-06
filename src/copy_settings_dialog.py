from PySide6 import QtWidgets
from models import CopyMode
from settings_manager import SettingsManager
from i18n import tr

class CopySettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Kopier-Einstellungen"))
        self.setModal(True)
        self.settings = settings

        # ComboBox mit Label und zugehörigem Enum-Wert
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.setAccessibleName(tr("Kopiermodus"))
        self.mode_combo.setAccessibleDescription(tr("Auswahl, welche Inhalte beim Kopieren in die Zwischenablage übernommen werden"))
        for label, mode in [
            ("Nur Titel",       CopyMode.TITLE.value),
            ("Nur Prompt-Text", CopyMode.TEXT.value),
            ("Nur Ergebnis",    CopyMode.RESULT.value),
            ("Alles",           CopyMode.ALL.value),
        ]:
            self.mode_combo.addItem(tr(label), mode)

        # Aktuellen Modus vorwählen
        current = self.settings.get_copy_mode().value
        idx = self.mode_combo.findData(current)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        # Checkbox für Metadaten
        self.chk_meta = QtWidgets.QCheckBox(tr("Metadaten (Tags) hinzufügen"))
        self.chk_meta.setAccessibleName(tr("Metadaten hinzufügen"))
        self.chk_meta.setAccessibleDescription(tr("Schlagwörter und Metadaten an den kopierten Text anfügen"))
        self.chk_meta.setChecked(self.settings.get_include_metadata())

        lbl_mode = QtWidgets.QLabel(tr("Kopiermodus:"))
        lbl_mode.setBuddy(self.mode_combo)

        # Layout
        form = QtWidgets.QFormLayout()
        form.addRow(lbl_mode, self.mode_combo)
        form.addRow("",       self.chk_meta)

        btn_ok     = QtWidgets.QPushButton(tr("OK"))
        btn_ok.setDefault(True)
        btn_ok.setAccessibleName(tr("OK"))
        btn_ok.setAccessibleDescription(tr("Kopier-Einstellungen speichern und Dialog schließen"))
        btn_ok.setToolTip(tr("Einstellungen speichern (Enter)"))

        btn_cancel = QtWidgets.QPushButton(tr("Abbrechen"))
        btn_cancel.setAccessibleName(tr("Abbrechen"))
        btn_cancel.setAccessibleDescription(tr("Änderungen verwerfen und Dialog schließen"))
        btn_cancel.setToolTip(tr("Abbrechen (Esc)"))

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
