from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QMimeData

from clipboard_manager import ClipboardManager
from app_version import __version__
from PySide6.QtGui import QIcon
from library_export import write_library_export
from models import Board, BoardItem, CopyMode, Prompt, Version, now_iso
from pdf_exporter import export_single_prompt, export_single_version
from profiprompt import MainWindow, apply_dark_theme
from storage import Storage


class SmokeSettings:
    """Kleines Settings-Double, damit der Smoke keine User-Settings anfasst."""

    def __init__(self) -> None:
        self._copy_mode = CopyMode.ALL
        self._include_metadata = True
        self.qs = _MemorySettingsStore()

    def get_copy_mode(self) -> CopyMode:
        return self._copy_mode

    def get_include_metadata(self) -> bool:
        return self._include_metadata

    SUPPORTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")

    def get_language(self) -> str:
        lang = self.qs.value("ui/language", "de", type=str)
        return lang if lang in self.SUPPORTED_LANGUAGES else "de"

    def set_language(self, lang: str) -> None:
        if lang in self.SUPPORTED_LANGUAGES:
            self.qs.setValue("ui/language", lang)

    def get_theme(self) -> str:
        theme = self.qs.value("ui/theme", "dark", type=str)
        return theme if theme in ("dark", "light") else "dark"

    def get_tile_color(self, kind: str) -> str:
        import theme as theme_mod
        default = (theme_mod.DEFAULT_TILE_MAIN if kind == "main"
                   else theme_mod.DEFAULT_TILE_VERSION)
        return self.qs.value(f"tiles/color_{kind}", default, type=str) or default


class _MemorySettingsStore:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def value(self, key: str, default: Any = None, type: type | None = None):
        value = self._values.get(key, default)
        if type is None or value is None:
            return value
        try:
            return type(value)
        except Exception:
            return default

    def setValue(self, key: str, value: Any) -> None:
        self._values[key] = value


@contextmanager
def _suppress_message_boxes():
    original_information = QMessageBox.information
    original_critical = QMessageBox.critical
    QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    try:
        yield
    finally:
        QMessageBox.information = original_information
        QMessageBox.critical = original_critical


@contextmanager
def _preserve_clipboard(expected_text: str):
    clipboard = QApplication.clipboard()
    previous = QMimeData()
    current = clipboard.mimeData()
    if current is not None:
        for fmt in current.formats():
            previous.setData(fmt, current.data(fmt))
        if current.hasImage():
            previous.setImageData(current.imageData())
        if current.hasColor():
            previous.setColorData(current.colorData())
    try:
        yield
    finally:
        # Keep unrelated clipboard changes made while the smoke is running.
        if clipboard.text() == expected_text:
            clipboard.setMimeData(previous)
            QApplication.processEvents()


def seed_smoke_storage(storage: Storage) -> tuple[Prompt, Version]:
    """Legt deterministische Beispieldaten an, damit der Smoke wiederholbar bleibt."""
    timestamp = now_iso()
    version = Version(
        id="v-smoke-1",
        prompt_id="p-smoke-1",
        version_number=1,
        title="Antwort unterwegs",
        text="Fasse die wichtigsten Punkte prägnant zusammen.",
        result="Kurzfassung mit echten Umlauten: äöü.",
        tags=["mobil", "lesen"],
        created_at=timestamp,
        updated_at=timestamp,
    )
    prompt = Prompt(
        id="p-smoke-1",
        title="Grußprompt",
        purpose="Überblick für Plattform-Smoke",
        text="Schreibe eine freundliche Begrüßung mit klarer Struktur.",
        tags=["deutsch", "überblick"],
        last_result="Hallo aus dem Smoke-Test.",
        created_at=timestamp,
        updated_at=timestamp,
        versions=[version],
    )
    board = Board(
        id="b-smoke-1",
        title="Unterwegs",
        description="Kleines Board für den Plattform-Smoke.",
        items=[
            BoardItem(
                id="bi-smoke-1",
                board_id="b-smoke-1",
                prompt_id=prompt.id,
                version_id=version.id,
                color="#2F5D9E",
                created_at=timestamp,
            )
        ],
        created_at=timestamp,
    )
    storage.save_prompts([prompt])
    storage.save_boards([board])
    return prompt, version


def run_platform_smoke(output_dir: str | Path, *, headless: bool = True) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    exports_dir = output_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    if headless and "QT_QPA_PLATFORM" not in os.environ and QApplication.instance() is None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    if not headless and QApplication.instance() is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    app = QApplication.instance() or QApplication([])
    app.setApplicationVersion(__version__)
    if not headless and app.platformName() == "offscreen":
        raise RuntimeError("Native Windows platform required for release screenshots.")
    apply_dark_theme(app)

    settings = SmokeSettings()
    storage = Storage(output_dir / "data")
    prompt, version = seed_smoke_storage(storage)

    window = MainWindow(storage, settings)
    try:
        if not headless and window.windowIcon().isNull():
            raise RuntimeError("Runtime icon missing from release bundle.")
        window.show()
        app.processEvents()

        prompt_txt_path = exports_dir / "prompt.txt"
        prompt_pdf_path = exports_dir / "prompt.pdf"
        version_pdf_path = exports_dir / "version.pdf"
        library_json_path = exports_dir / "profiprompt-library-v1.json"
        summary_path = exports_dir / "platform-smoke-summary.json"

        if any(path.exists() for path in (prompt_txt_path, prompt_pdf_path, version_pdf_path, library_json_path)):
            window.close()
            raise RuntimeError("Smoke artifacts already exist. Use a fresh output directory.")
        copy_text = ClipboardManager(settings).build_copy_text(prompt)

        with _suppress_message_boxes(), _preserve_clipboard(copy_text):
            window._write_txt_export(str(prompt_txt_path), copy_text, "TXT erfolgreich gespeichert.")
            if not export_single_prompt(prompt, settings, str(prompt_pdf_path)):
                raise RuntimeError("Prompt PDF export failed.")
            if not export_single_version(version, str(version_pdf_path), settings=settings):
                raise RuntimeError("Version PDF export failed.")
            payload = write_library_export(storage, library_json_path)
            ClipboardManager(settings).copy_to_clipboard(window.dashboard.tree, copy_text)
            app.processEvents()
            clipboard_text = QApplication.clipboard().text()

        txt_content = prompt_txt_path.read_text(encoding="utf-8")
        exported = json.loads(library_json_path.read_text(encoding="utf-8"))

        if clipboard_text != copy_text:
            raise RuntimeError("Clipboard-Smoke fehlgeschlagen: Text stimmt nicht mit dem Exporttext überein.")
        if "Grußprompt" not in txt_content or "Begrüßung" not in txt_content or "überblick" not in txt_content:
            raise RuntimeError("TXT-Smoke fehlgeschlagen: Exporttext enthält die erwarteten Umlaute nicht.")
        if exported.get("schema_version") != "profiprompt-library-v1":
            raise RuntimeError("JSON-Smoke fehlgeschlagen: schema_version fehlt oder ist falsch.")
        if payload["stats"]["prompt_count"] != 1 or payload["stats"]["board_count"] != 1:
            raise RuntimeError("JSON-Smoke fehlgeschlagen: Unerwartete Exportstatistik.")
        if not prompt_pdf_path.exists() or prompt_pdf_path.stat().st_size == 0:
            raise RuntimeError("PDF-Smoke fehlgeschlagen: Prompt-PDF wurde nicht erzeugt.")
        if any(not path.read_bytes().startswith(b"%PDF-") for path in (prompt_pdf_path, version_pdf_path)):
            raise RuntimeError("Smoke PDF artifacts are invalid.")
        if exported["app"]["version"] != __version__:
            raise RuntimeError("JSON export app version differs from runtime metadata.")
        if not version_pdf_path.exists() or version_pdf_path.stat().st_size == 0:
            raise RuntimeError("PDF-Smoke fehlgeschlagen: Versions-PDF wurde nicht erzeugt.")

        screenshots = []
        if not headless:
            from PySide6 import QtCore
            for lang in ("de", "en"):
                window.change_language(lang)
                app.processEvents()
                expected = "Titel" if lang == "de" else "Title"
                if window.dashboard.tree.headerItem().text(0) != expected:
                    raise RuntimeError("Live language switch did not update the prompt tree.")
                image = output_dir / ("main-" + lang + ".png")
                if not window.grab().save(str(image)):
                    raise RuntimeError("Screenshot save failed.")
                screenshots.append(str(image))
            window.change_language("de")
            # Exercise the shipped board-transfer path and persisted per-tile color.
            target = Board(id="b-smoke-2", title="Zielboard", items=[], created_at=now_iso())
            storage.upsert_board(target)
            ok, reason = storage.transfer_item("b-smoke-1", target.id, prompt.id, version.id, move=False)
            if not ok:
                raise RuntimeError(str(reason))
            transferred = next(b for b in storage.load_boards() if b.id == target.id)
            if len(transferred.items) != 1 or transferred.items[0].color != "#2F5D9E":
                raise RuntimeError("Board transfer or per-tile color did not persist.")
        summary = {
            "version": __version__,
            "frozen": bool(getattr(__import__("sys"), "frozen", False)),
            "native_platform": app.platformName(),
            "screenshots": screenshots,
            "headless": headless,
            "qt_platform": os.environ.get("QT_QPA_PLATFORM", ""),
            "artifacts": {
                "prompt_txt": str(prompt_txt_path),
                "prompt_pdf": str(prompt_pdf_path),
                "version_pdf": str(version_pdf_path),
                "library_json": str(library_json_path),
            },
            "clipboard_text": clipboard_text,
            "stats": payload["stats"],
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return summary
    finally:
        window.close()
        window.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
        app.processEvents()
        # Offscreen uses a private, virtual clipboard. Its retained QMimeData
        # crashes Qt 6.11 on Windows shutdown; release it before QApplication.
        if app.platformName() == "offscreen":
            QApplication.clipboard().clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduzierbarer Desktop-Plattform-Smoke für ProfiPrompt.",
    )
    parser.add_argument(
        "--output-dir",
        default="build/platform-smoke",
        help="Zielordner für temporäre Daten und erzeugte Artefakte.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="QT_QPA_PLATFORM nicht auf offscreen setzen.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_platform_smoke(
        args.output_dir,
        headless=not args.no_headless,
    )
    print("Plattform-Smoke erfolgreich.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
