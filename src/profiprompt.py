import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDockWidget,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QAction, QActionGroup, QPalette, QColor
from PySide6.QtCore import Qt

from settings_manager import SettingsManager
from storage import Storage
from event_bus import bus
from dashboard import DashboardWidget
from board_manager import BoardManager
from copy_settings_dialog import CopySettingsDialog
from clipboard_manager import ClipboardManager
from library_export import write_library_export
from pdf_exporter import (
    export_all_prompts,
    export_single_prompt,
    export_single_version,
)

# --- Uebersetzung / i18n (Welle-1 U1: sichtbarer DE/EN-Sprachschalter) -------
import os
from pathlib import Path


def _app_base_dir() -> Path:
    """Basisverzeichnis fuer gebuendelte Daten (locales/translator).

    Frozen (PyInstaller): sys._MEIPASS; sonst der Repo-Root (Parent von src/).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return Path(__file__).resolve().parent.parent


_BASE_DIR = _app_base_dir()
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

try:
    from translator import TranslationSystem
except Exception:  # pragma: no cover - Uebersetzung ist optional
    TranslationSystem = None


def make_translator(lang: str):
    """Erzeugt ein TranslationSystem mit robuster locales-Aufloesung (oder None)."""
    if TranslationSystem is None:
        return None
    try:
        return TranslationSystem(lang, app_dir=_BASE_DIR)
    except Exception:
        return None


from theme import apply_theme
from appearance_dialog import AppearanceDialog


def apply_dark_theme(app):
    """Kompat-Wrapper: setzt das Dark-Theme (Theme-Logik jetzt in theme.py)."""
    return apply_theme(app, "dark")

class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, settings: SettingsManager):
        super().__init__()
        self.storage = storage
        self.settings = settings
        self.app = QApplication.instance()
        self.translator = make_translator(self.settings.get_language())

        self.setWindowTitle("Prompt Manager")
        self.resize(1300, 850)

        # Zentraler Bereich: Dashboard
        self.dashboard = DashboardWidget(self.storage, self.settings)
        self.setCentralWidget(self.dashboard)

        # Dock: Boards
        self.boardDock = QDockWidget("Boards", self)
        self.boardDock.setObjectName("BoardsDock")
        self.boardDock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.boardManager = BoardManager(self.storage, self.settings)
        self.boardDock.setWidget(self.boardManager)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.boardDock)

        # Menü & Aktionen
        self._build_menu()

        # Event-Bus Connects
        # Bugsweep 19 BUG-06: dashboard.reload / boardManager.reload werden bereits
        # widget-seitig verbunden (DashboardWidget bzw. BoardManager __init__). Die
        # frueheren zusaetzlichen Connects hier fuehrten zu DOPPELTEM reload (doppelter
        # Disk-Zugriff + Tree/Grid-Rebuild) bei jedem promptsChanged/boardsChanged.
        bus.copyRequested.connect(self.handle_copy_request)
        bus.dragRequested.connect(self.handle_drag_request)

    def _t(self, key: str) -> str:
        """Uebersetzt key in die aktuelle Sprache (Fallback: key selbst)."""
        return self.translator.t(key) if self.translator is not None else key

    def _build_menu(self):
        menubar = self.menuBar()
        _t = self._t

        # Datei
        m_file = menubar.addMenu(_t("Datei"))
        m_file.addAction(self._action(_t("Alle Prompts (TXT)"), self.export_all_txt))
        m_file.addAction(self._action(_t("Alle Prompts (PDF)"), self.export_all_pdf))
        m_file.addAction(self._action(_t("Bibliothek (JSON)"), self.export_library_json))
        m_file.addSeparator()
        m_file.addAction(self._action(_t("Aktueller Prompt (TXT)"), self.export_current_prompt_txt))
        m_file.addAction(self._action(_t("Aktueller Prompt (PDF)"), self.export_current_prompt_pdf))
        m_file.addSeparator()
        m_file.addAction(self._action(_t("Aktuelle Version (TXT)"), self.export_current_version_txt))
        m_file.addAction(self._action(_t("Aktuelle Version (PDF)"), self.export_current_version_pdf))
        m_file.addSeparator()
        m_file.addAction(self._action(_t("Beenden"), QApplication.instance().quit))

        # Bearbeiten
        m_edit = menubar.addMenu(_t("Bearbeiten"))
        m_edit.addAction(self._action(_t("Neuen Prompt erstellen"), self.dashboard.create_prompt))
        m_edit.addAction(self._action(_t("Kopier-Einstellungen …"), self.open_copy_settings))
        m_edit.addAction(self._action(_t("Darstellung …"), self.open_appearance_settings))

        # Ansicht
        m_view = menubar.addMenu(_t("Ansicht"))
        toggle_boards = QAction(_t("Boards anzeigen/ausblenden"), self, checkable=True)
        toggle_boards.setChecked(self.boardDock.isVisible())
        toggle_boards.toggled.connect(self.boardDock.setVisible)
        m_view.addAction(toggle_boards)

        # Hilfe
        m_help = menubar.addMenu(_t("Hilfe"))
        m_help.addAction(self._action(_t("Anleitung"), self._show_help))
        m_help.addAction(self._action(_t("Über Prompt Manager"), self._show_about))

        # Sprache / Language (Welle-1 U1: sichtbarer DE/EN-Schalter)
        m_lang = menubar.addMenu("Sprache / Language")
        cur = self.translator.get_language() if self.translator is not None else "de"
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        act_de = QAction("Deutsch", self, checkable=True)
        act_de.setChecked(cur == "de")
        act_de.triggered.connect(lambda: self.change_language("de"))
        act_en = QAction("English", self, checkable=True)
        act_en.setChecked(cur == "en")
        act_en.triggered.connect(lambda: self.change_language("en"))
        lang_group.addAction(act_de)
        lang_group.addAction(act_en)
        m_lang.addAction(act_de)
        m_lang.addAction(act_en)

    def change_language(self, lang: str):
        """Setzt die Sprache, persistiert sie und stellt die Menueleiste live um."""
        self.settings.set_language(lang)
        if self.translator is not None:
            self.translator.set_language(lang)
        self.retranslate()
        if lang == "de":
            QMessageBox.information(
                self, "Sprache / Language",
                "Sprache auf Deutsch umgestellt. Einige Texte werden erst nach "
                "einem Neustart übersetzt.",
            )
        else:
            QMessageBox.information(
                self, "Sprache / Language",
                "Language switched to English. Some texts update after a restart.",
            )

    def retranslate(self):
        """Baut die Menueleiste in der aktuellen Sprache neu auf."""
        self.menuBar().clear()
        self._build_menu()

    def _action(self, text: str, slot):
        act = QAction(text, self)
        act.triggered.connect(slot)
        return act

    def _show_help(self):
        QMessageBox.information(
            self, "Anleitung",
            "• Doppelklick auf Liste: Bearbeiten\n"
            "• Drag & Drop auf Board rechts: Prompt anheften\n"
            "• Rechtsklick: Kontextmenü für Export/Löschen"
        )

    def _show_about(self):
        QMessageBox.information(self, "Über", "Prompt Manager v1.0.1\nModern Dark Edition")

    # --- Exports ---
    def export_all_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export TXT", "alle_prompts.txt", "Text (*.txt)")
        if not path:
            return
        prompts = self.storage.load_prompts()
        parts = []
        for p in prompts:
            lines = [f"=== {p.title} ===", f"Zweck: {p.purpose}", f"Tags: {', '.join(p.tags or [])}",
                     "", p.text or ""]
            for v in sorted(p.versions, key=lambda x: x.version_number):
                lines += ["", f"--- v{v.version_number}: {v.title} ---", v.text or ""]
            parts.append("\n".join(lines))
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(parts))
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Export", "TXT erfolgreich gespeichert.")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Fehler", f"TXT-Export fehlgeschlagen:\n{e}")

    def export_all_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "alle_prompts.pdf", "PDF (*.pdf)")
        if path: export_all_prompts(self.storage, self.settings, path, parent=self)

    def export_library_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Bibliothek exportieren",
            "profiprompt-library-v1.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            payload = write_library_export(self.storage, path)
            count = payload["stats"]["prompt_count"]
            QMessageBox.information(
                self,
                "Export",
                f"JSON-Bibliothek erfolgreich gespeichert ({count} Prompts).",
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"JSON-Export fehlgeschlagen:\n{e}")

    def export_current_prompt_txt(self):
        p = self.dashboard.get_current_prompt()
        if not p: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Prompt TXT", f"{p.title}.txt", "Text (*.txt)")
        if not path:
            return
        text = ClipboardManager(self.settings).build_copy_text(p)
        self._write_txt_export(path, text, "TXT erfolgreich gespeichert.")

    def export_current_prompt_pdf(self):
        p = self.dashboard.get_current_prompt()
        if not p: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Prompt PDF", f"{p.title}.pdf", "PDF (*.pdf)")
        if path: export_single_prompt(p, self.settings, path, parent=self)

    def export_current_version_txt(self):
        v = self.dashboard.get_current_version()
        if not v: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Version TXT", f"{v.title}.txt", "Text (*.txt)")
        if not path:
            return
        p = self.storage.get_prompt(v.prompt_id)
        if not p:
            QMessageBox.critical(self, "Fehler", "Zugehöriger Prompt nicht gefunden.")
            return
        text = ClipboardManager(self.settings).build_copy_text(p, v)
        self._write_txt_export(path, text, "TXT erfolgreich gespeichert.")

    def export_current_version_pdf(self):
        v = self.dashboard.get_current_version()
        if not v: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Version PDF", f"{v.title}.pdf", "PDF (*.pdf)")
        if path: export_single_version(v, path, parent=self, settings=self.settings)

    def _write_txt_export(self, path: str, text: str, success_message: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Export", success_message)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"TXT-Export fehlgeschlagen:\n{e}")

    # --- Handlers ---
    def open_copy_settings(self):
        CopySettingsDialog(self.settings, self).exec()

    def open_appearance_settings(self):
        """Darstellung (U2 Theme + U3 Kachelfarben); wendet Aenderungen live an."""
        dlg = AppearanceDialog(self.settings, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            # Theme app-weit live umschalten (Fusion-Palette + Stylesheet)
            if self.app is not None:
                apply_theme(self.app, self.settings.get_theme())
            # Dashboard neu laden -> theme-passende Tree-Icons neu waehlen (U4)
            self.dashboard.reload()
            # Board-Kacheln + Flaeche neu einfaerben (U2 Flaeche, U3 Farben)
            self.boardManager.apply_theme_and_reload()

    def handle_copy_request(self, kind, item_id, parent):
        clipboard = QApplication.clipboard()
        clip_mgr = ClipboardManager(self.settings)
        
        # Umweg, um das Objekt zu finden, da das Signal nur die ID sendet
        prompts = self.storage.load_prompts()
        target_p, target_v = None, None
        
        if kind == "prompt":
            target_p = next((p for p in prompts if p.id == item_id), None)
        elif kind == "version":
            for p in prompts:
                v = next((x for x in p.versions if x.id == item_id), None)
                if v:
                    target_p, target_v = p, v
                    break
        
        if target_p:
            text = clip_mgr.build_copy_text(target_p, target_v)
            clipboard.setText(text)
            if parent:
                parent.setToolTip("Kopiert! 📋")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: parent.setToolTip(""))

    def handle_drag_request(self, kind, ids):
        # ids ist tuple (prompt_id, version_id)
        pid, vid = ids
        board = self.boardManager.current_board()
        if not board:
            return

        # Dein storage.py gibt (bool, str|None) zurück
        success, _ = self.storage.add_item_to_board(board.id, pid, vid)
        if success:
            self.boardManager.reload()
            # Optional: Feedback
            bus.boardsChanged.emit()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Prompt Manager")

    settings = SettingsManager()
    # Theme aus den Einstellungen anwenden (Hell/Dunkel, U2)
    apply_theme(app, settings.get_theme())

    # Pfad aus settings oder standard
    storage = Storage(settings.get_data_path())

    w = MainWindow(storage, settings)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
