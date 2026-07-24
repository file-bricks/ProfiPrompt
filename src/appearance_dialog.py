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
        self.setMinimumWidth(360)

        # --- Theme (U2) ---
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItem("Dunkel", "dark")
        self.theme_combo.addItem("Hell", "light")
        cur_theme = self.settings.get_theme()
        idx = self.theme_combo.findData(cur_theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

        # --- Kachelfarben (U3) ---
        self._main_color = self.settings.get_tile_color("main")
        self._version_color = self.settings.get_tile_color("version")

        self.btn_main = QtWidgets.QPushButton()
        self.btn_main.clicked.connect(lambda: self._pick_color("main"))
        self.btn_version = QtWidgets.QPushButton()
        self.btn_version.clicked.connect(lambda: self._pick_color("version"))
        self._refresh_swatch("main")
        self._refresh_swatch("version")

        self.btn_reset = QtWidgets.QPushButton("Zurücksetzen")
        self.btn_reset.clicked.connect(self._reset_colors)

        # --- Layout ---
        form = QtWidgets.QFormLayout()
        form.addRow("Theme:", self.theme_combo)
        form.addRow("Farbe Hauptprompt-Kacheln:", self.btn_main)
        form.addRow("Farbe Versionsprompt-Kacheln:", self.btn_version)
        form.addRow("", self.btn_reset)

        btn_ok = QtWidgets.QPushButton("OK")
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
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
