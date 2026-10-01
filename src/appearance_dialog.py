"""Darstellungs-Einstellungen (Welle-1 U2 Theme + U3 Kachelfarben).

Ein schlanker Dialog:
  * Theme-Auswahl Hell/Dunkel (persistiert via QSettings ui/theme).
  * getrennte Basis-Farbwahl fuer Haupt-Prompt- und Versions-Kacheln
    (QColorDialog, persistiert via QSettings tiles/color_*).
  * "Zuruecksetzen" stellt die Standard-Kachelfarben wieder her.

Persistiert wird erst bei OK (accept); der Aufrufer wendet die Aenderung danach
live an.
"""
from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore

from settings_manager import SettingsManager
import theme as theme_mod


class AppearanceDialog(QtWidgets.QDialog):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Darstellung")
        self.setModal(True)
        self.setMinimumWidth(360)

        # --- Theme (U2) ---
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.setAccessibleName("Theme-Auswahl")
        self.theme_combo.setAccessibleDescription("Auswahl zwischen dunklem und hellem Farbschema")
        self.theme_combo.addItem("Dunkel", "dark")
        self.theme_combo.addItem("Hell", "light")
        cur_theme = self.settings.get_theme()
        idx = self.theme_combo.findData(cur_theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

        # --- Kachelfarben (U3) ---
        self._main_color = self.settings.get_tile_color("main")
        self._version_color = self.settings.get_tile_color("version")

        self.btn_main = QtWidgets.QPushButton()
        self.btn_main.setAccessibleName("Farbe Hauptprompt-Kacheln")
        self.btn_main.clicked.connect(lambda: self._pick_color("main"))
        self.btn_version = QtWidgets.QPushButton()
        self.btn_version.setAccessibleName("Farbe Versionsprompt-Kacheln")
        self.btn_version.clicked.connect(lambda: self._pick_color("version"))
        self._refresh_swatch("main")
        self._refresh_swatch("version")

        self.btn_reset = QtWidgets.QPushButton("Zurücksetzen")
        self.btn_reset.setAccessibleName("Kachelfarben zurücksetzen")
        self.btn_reset.setAccessibleDescription("Setzt die Kachelfarben auf die Standardwerte zurück")
        self.btn_reset.setToolTip("Standardfarben wiederherstellen")
        self.btn_reset.clicked.connect(self._reset_colors)

        lbl_theme = QtWidgets.QLabel("Theme:")
        lbl_theme.setBuddy(self.theme_combo)
        lbl_main = QtWidgets.QLabel("Farbe Hauptprompt-Kacheln:")
        lbl_main.setBuddy(self.btn_main)
        lbl_version = QtWidgets.QLabel("Farbe Versionsprompt-Kacheln:")
        lbl_version.setBuddy(self.btn_version)

        # --- Layout ---
        form = QtWidgets.QFormLayout()
        form.addRow(lbl_theme, self.theme_combo)
        form.addRow(lbl_main, self.btn_main)
        form.addRow(lbl_version, self.btn_version)
        form.addRow("", self.btn_reset)

        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.setAccessibleName("OK")
        btn_ok.setAccessibleDescription("Darstellungs-Einstellungen speichern und anwenden")
        btn_ok.setToolTip("Einstellungen speichern (Enter)")

        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        btn_cancel.setAccessibleName("Abbrechen")
        btn_cancel.setAccessibleDescription("Änderungen verwerfen und Dialog schließen")
        btn_cancel.setToolTip("Abbrechen (Esc)")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        root = QtWidgets.QVBoxLayout(self)
        root.addLayout(form)
        root.addSpacing(8)
        root.addLayout(btns)

    # --- Kachelfarben-Helfer ---
    def _current_color(self, kind: str) -> str:
        return self._main_color if kind == "main" else self._version_color

    def _set_current_color(self, kind: str, hexcolor: str):
        if kind == "main":
            self._main_color = hexcolor
        else:
            self._version_color = hexcolor

    def _refresh_swatch(self, kind: str):
        btn = self.btn_main if kind == "main" else self.btn_version
        hexcolor = self._current_color(kind)
        text_col = theme_mod.contrast_text(hexcolor)
        btn.setText(hexcolor)
        label_kind = "Hauptprompts" if kind == "main" else "Versionsprompts"
        btn.setToolTip(f"Kachelfarbe für {label_kind} ändern (Aktuell: {hexcolor})")
        btn.setAccessibleDescription(f"Aktuelle Hex-Farbe für {label_kind}: {hexcolor}")
        btn.setStyleSheet(
            f"background-color: {hexcolor}; color: {text_col}; "
            f"border: 1px solid #888; border-radius: 4px; padding: 6px 12px;"
        )

    def _pick_color(self, kind: str):
        initial = QtGui.QColor(self._current_color(kind))
        chosen = QtWidgets.QColorDialog.getColor(
            initial, self, "Kachelfarbe wählen"
        )
        if chosen.isValid():
            self._set_current_color(kind, chosen.name().upper())
            self._refresh_swatch(kind)

    def _reset_colors(self):
        self._main_color = theme_mod.DEFAULT_TILE_MAIN
        self._version_color = theme_mod.DEFAULT_TILE_VERSION
        self._refresh_swatch("main")
        self._refresh_swatch("version")

    # --- Persistenz ---
    def accept(self) -> None:
        self.settings.set_theme(self.theme_combo.currentData())
        self.settings.set_tile_color("main", self._main_color)
        self.settings.set_tile_color("version", self._version_color)
        super().accept()
