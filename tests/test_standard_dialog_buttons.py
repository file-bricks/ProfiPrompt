from PySide6 import QtCore, QtWidgets

import pytest

import i18n
from dialog_button_localizer import DialogButtonLocalizer, install_standard_button_localizer


LOCALES = ("en", "de", "es", "zh", "ja", "ru", "fr", "hi", "ar", "bn", "pt")
MESSAGE_BUTTONS = (
    QtWidgets.QMessageBox.StandardButton.Ok,
    QtWidgets.QMessageBox.StandardButton.Cancel,
    QtWidgets.QMessageBox.StandardButton.Yes,
    QtWidgets.QMessageBox.StandardButton.No,
)
BUTTONS = (
    QtWidgets.QDialogButtonBox.StandardButton.Ok,
    QtWidgets.QDialogButtonBox.StandardButton.Cancel,
    QtWidgets.QDialogButtonBox.StandardButton.Yes,
    QtWidgets.QDialogButtonBox.StandardButton.No,
)
KEYS = ("OK", "Abbrechen", "Ja", "Nein")


def _assert_labels(button_box, expected, standards=BUTTONS):
    for standard, text in zip(standards, expected, strict=True):
        button = button_box.button(standard)
        assert button is not None
        assert button_box.standardButton(button) == standard
        assert button.text() == text


def test_qt_standard_button_labels_follow_every_complete_app_locale(qapp, monkeypatch):
    localizer = install_standard_button_localizer(qapp)
    assert localizer.parent() is qapp
    assert getattr(qapp, "_profiprompt_dialog_button_localizer") is localizer
    assert install_standard_button_localizer(qapp) is localizer

    with monkeypatch.context() as scoped:
        scoped.setattr(
            localizer,
            "_belongs_to_file_dialog",
            lambda widget: pytest.fail("Unrelated widgets must skip the ancestry walk"),
        )
        unrelated_widget = QtWidgets.QWidget()
        show_event = QtCore.QEvent(QtCore.QEvent.Type.Show)
        assert localizer.eventFilter(unrelated_widget, show_event) is False

    translator = i18n.get_translator()
    original = translator.get_language()
    try:
        for locale in LOCALES:
            assert translator.set_language(locale)
            expected = [i18n.tr(key) for key in KEYS]

            message = QtWidgets.QMessageBox()
            message.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel
                | QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
            )
            message.show()
            qapp.processEvents()
            for standard, text in zip(MESSAGE_BUTTONS, expected, strict=True):
                button = message.button(standard)
                assert button is not None
                assert message.standardButton(button) == standard
                assert button.text() == text
            message.close()

            prompt = QtWidgets.QInputDialog()
            prompt.show()
            qapp.processEvents()
            input_buttons = prompt.findChild(QtWidgets.QDialogButtonBox)
            assert input_buttons is not None
            _assert_labels(input_buttons, expected[:2], BUTTONS[:2])
            prompt.close()

            dialog = QtWidgets.QDialog()
            layout = QtWidgets.QVBoxLayout(dialog)
            standard_buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
                | QtWidgets.QDialogButtonBox.StandardButton.Cancel
                | QtWidgets.QDialogButtonBox.StandardButton.Yes
                | QtWidgets.QDialogButtonBox.StandardButton.No,
                dialog,
            )
            layout.addWidget(standard_buttons)
            dialog.show()
            qapp.processEvents()
            _assert_labels(standard_buttons, expected)
            dialog.close()
    finally:
        translator.set_language(original)
        qapp.processEvents()


def test_qfiledialog_and_its_children_are_excluded_from_app_translation(qapp):
    install_standard_button_localizer(qapp)
    dialog = QtWidgets.QFileDialog()
    assert DialogButtonLocalizer._belongs_to_file_dialog(dialog)
    child = QtWidgets.QDialogButtonBox(dialog)
    assert DialogButtonLocalizer._belongs_to_file_dialog(child)
    dialog.close()
