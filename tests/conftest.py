# -*- coding: utf-8 -*-
"""Gemeinsame Test-Fixtures fuer ProfiPrompt.

Isolation (Welle-1-Querschnittsbefund): Tests duerfen NICHT in die echten
QSettings des Users (%APPDATA%\\PromptManager) schreiben. Deshalb wird der
IniFormat/UserScope-Pfad session-weit in ein Temp-Verzeichnis umgebogen.
Zusaetzlich laeuft Qt headless (offscreen).
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolate_qsettings(tmp_path_factory):
    """Leitet die App-QSettings in ein Temp-Verzeichnis um (kein %APPDATA%-Write)."""
    d = tmp_path_factory.mktemp("qsettings")
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, str(d)
    )
    yield


@pytest.fixture(scope="session")
def qapp():
    """Eine einzige QApplication-Instanz fuer alle GUI-nahen Tests."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return app
