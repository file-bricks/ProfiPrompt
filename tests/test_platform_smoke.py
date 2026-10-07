# -*- coding: utf-8 -*-
"""Regressionstest fuer den reproduzierbaren Plattform-Smoke."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_run_platform_smoke_creates_expected_artifacts(tmp_path):
    from platform_smoke import run_platform_smoke

    summary = run_platform_smoke(tmp_path / "platform-smoke", headless=True)

    assert summary["stats"]["prompt_count"] == 1
    assert summary["stats"]["board_count"] == 1

    for artifact in summary["artifacts"].values():
        path = Path(artifact)
        assert path.exists()
        assert path.stat().st_size > 0

    exported = json.loads(
        Path(summary["artifacts"]["library_json"]).read_text(encoding="utf-8")
    )
    assert exported["schema_version"] == "profiprompt-library-v1"
    assert exported["prompts"][0]["title"] == "Grußprompt"
    txt_export = Path(summary["artifacts"]["prompt_txt"]).read_text(encoding="utf-8")
    assert "Begrüßung" in txt_export
    assert "überblick" in txt_export

def test_failed_pdf_export_cannot_pass_smoke(tmp_path, monkeypatch):
    import pytest
    import platform_smoke
    monkeypatch.setattr(platform_smoke, "export_single_prompt", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="PDF export failed"):
        platform_smoke.run_platform_smoke(tmp_path / "failed-smoke", headless=True)


def test_smoke_preserves_typed_clipboard_data_and_concurrent_copy(qapp, monkeypatch):
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtGui import QImage, QColor
    from PySide6.QtWidgets import QApplication
    from platform_smoke import _preserve_clipboard

    class Clipboard:
        def __init__(self, mime):
            self.mime = mime

        def mimeData(self):
            return self.mime

        def setMimeData(self, mime):
            self.mime = mime

        def text(self):
            return self.mime.text()

        def setText(self, text):
            self.mime = QMimeData()
            self.mime.setText(text)

    original = QMimeData()
    original.setText("Vorher")
    original.setHtml("<b>Vorher</b>")
    original.setData("application/x-smoke-test", b"binary\x00payload")
    original.setUrls([QUrl("file:///C:/example.txt")])
    image = QImage(4, 4, QImage.Format_ARGB32)
    image.fill(QColor("red"))
    original.setImageData(image)
    original.setColorData(QColor("blue"))
    clipboard = Clipboard(original)
    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: clipboard))
    with _preserve_clipboard("Smoke"):
        clipboard.setText("Smoke")
    restored = clipboard.mimeData()
    assert restored.text() == "Vorher"
    assert restored.html() == "<b>Vorher</b>"
    assert bytes(restored.data("application/x-smoke-test")) == b"binary\x00payload"
    assert restored.urls() == original.urls()
    assert isinstance(restored.imageData(), QImage)
    assert restored.imageData() == image
    assert restored.colorData() == QColor("blue")
    with _preserve_clipboard("Smoke"):
        clipboard.setText("Neue Kopie")
    assert clipboard.text() == "Neue Kopie"
