"""Localize Qt standard button labels using the active ProfiPrompt UI locale."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from i18n import tr


_MESSAGEBOX_BUTTON_KEYS = {
    QtWidgets.QMessageBox.StandardButton.Ok: "OK",
    QtWidgets.QMessageBox.StandardButton.Cancel: "Abbrechen",
    QtWidgets.QMessageBox.StandardButton.Yes: "Ja",
    QtWidgets.QMessageBox.StandardButton.No: "Nein",
}
_DIALOG_BUTTONBOX_BUTTON_KEYS = {
    QtWidgets.QDialogButtonBox.StandardButton.Ok: "OK",
    QtWidgets.QDialogButtonBox.StandardButton.Cancel: "Abbrechen",
    QtWidgets.QDialogButtonBox.StandardButton.Yes: "Ja",
    QtWidgets.QDialogButtonBox.StandardButton.No: "Nein",
}
_INSTALLED: dict[int, "DialogButtonLocalizer"] = {}


class DialogButtonLocalizer(QtCore.QObject):
    """Translate only buttons carrying a recognized Qt StandardButton enum."""

    def eventFilter(self, watched, event):
        if event.type() != QtCore.QEvent.Type.Show:
            return False
        if self._belongs_to_file_dialog(watched):
            return False

        if isinstance(watched, QtWidgets.QMessageBox):
            self._translate_standard_buttons(watched)
        if isinstance(watched, QtWidgets.QDialog):
            for button_box in watched.findChildren(QtWidgets.QDialogButtonBox):
                self._translate_standard_buttons(button_box)
        elif isinstance(watched, QtWidgets.QDialogButtonBox):
            self._translate_standard_buttons(watched)
        return False

    @staticmethod
    def _belongs_to_file_dialog(widget) -> bool:
        current = widget
        while isinstance(current, QtWidgets.QWidget):
            if isinstance(current, QtWidgets.QFileDialog):
                return True
            current = current.parentWidget()
        return False

    @staticmethod
    def _translate_standard_buttons(button_box) -> None:
        labels = (
            _MESSAGEBOX_BUTTON_KEYS
            if isinstance(button_box, QtWidgets.QMessageBox)
            else _DIALOG_BUTTONBOX_BUTTON_KEYS
        )
        for button in button_box.buttons():
            standard = button_box.standardButton(button)
            key = labels.get(standard)
            if key is not None:
                button.setText(tr(key))


def install_standard_button_localizer(app=None) -> DialogButtonLocalizer:
    """Install one app-wide filter; standard enums retain their original behavior."""
    app = app or QtWidgets.QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication must exist before installing dialog localization")
    existing = _INSTALLED.get(id(app))
    if existing is not None:
        return existing
    localizer = DialogButtonLocalizer(app)
    app.installEventFilter(localizer)
    _INSTALLED[id(app)] = localizer
    return localizer
