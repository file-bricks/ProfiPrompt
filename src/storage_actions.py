"""Keep Qt actions open and report unsuccessful library operations."""
from functools import wraps
from PySide6 import QtWidgets
from i18n import tr


def report_storage_errors(action):
    @wraps(action)
    def run(self, *args, **kwargs):
        try:
            return action(self, *args, **kwargs)
        except OSError as error:
            QtWidgets.QMessageBox.critical(
                self, tr("Bibliothek nicht verfügbar"),
                tr("Die Bibliothek konnte nicht gelesen oder gespeichert werden.\n"
                   "Prüfen Sie die Datei und ihre Zugriffsrechte und versuchen Sie es erneut.")
                + f"\n\n{error}",
            )
            return None
    return run
