import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDockWidget,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import Qt

from settings_manager import SettingsManager
from storage import Storage
from event_bus import bus
from dashboard import DashboardWidget
from board_manager import BoardManager
from copy_settings_dialog import CopySettingsDialog
from clipboard_manager import ClipboardManager
from pdf_exporter import (
    export_all_prompts,
    export_single_prompt,
    export_single_version,
)

def apply_dark_theme(app):
    """Setzt ein modernes Dark-Theme (Fusion Style)."""
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    
    # Farbdefinitionen
    c_bg = QColor(40, 40, 40)
    c_base = QColor(30, 30, 30)
    c_text = QColor(220, 220, 220)
    c_highlight = QColor(66, 165, 245)  # Ein modernes Blau
    c_highlight_text = QColor(255, 255, 255)
    c_btn = QColor(50, 50, 50)

    dark_palette.setColor(QPalette.Window, c_bg)
    dark_palette.setColor(QPalette.WindowText, c_text)
    dark_palette.setColor(QPalette.Base, c_base)
    dark_palette.setColor(QPalette.AlternateBase, c_bg)
    dark_palette.setColor(QPalette.ToolTipBase, c_highlight)
    dark_palette.setColor(QPalette.ToolTipText, c_highlight_text)
    dark_palette.setColor(QPalette.Text, c_text)
    dark_palette.setColor(QPalette.Button, c_btn)
    dark_palette.setColor(QPalette.ButtonText, c_text)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, c_highlight)
    dark_palette.setColor(QPalette.Highlight, c_highlight)
    dark_palette.setColor(QPalette.HighlightedText, c_highlight_text)
    
    app.setPalette(dark_palette)

    # Globales CSS für Feinheiten
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {c_bg.name()};
        }}
        QToolTip {{ 
            color: #ffffff; 
            background-color: {c_highlight.name()}; 
            border: 1px solid {c_bg.name()}; 
        }}
        /* Eingabefelder */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: #2b2b2b;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            color: #eee;
            selection-background-color: {c_highlight.name()};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {c_highlight.name()};
        }}
        /* Listen und Bäume */
        QTreeWidget, QListWidget {{
            background-color: #2b2b2b;
            border: 1px solid #444;
            alternate-background-color: #323232;
        }}
        QHeaderView::section {{
            background-color: #383838;
            color: #ddd;
            padding: 4px;
            border: none;
            border-right: 1px solid #555;
            border-bottom: 1px solid #555;
        }}
        /* Buttons */
        QPushButton {{
            background-color: #3d3d3d;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px 12px;
            color: #eee;
        }}
        QPushButton:hover {{
            background-color: #4d4d4d;
            border-color: {c_highlight.name()};
        }}
        QPushButton:pressed {{
            background-color: {c_highlight.name()};
            color: white;
        }}
        /* Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: #2b2b2b;
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #555;
            min-height: 20px;
            border-radius: 5px;
        }}
        QDockWidget::title {{
            background: #323232;
            padding-left: 5px;
            padding-top: 4px;
        }}
    """)

class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, settings: SettingsManager):
        super().__init__()
        self.storage = storage
        self.settings = settings

        self.setWindowTitle("Prompt Manager")
        self.resize(1300, 850)

        # Zentraler Bereich: Dashboard
        self.dashboard = DashboardWidget(self.storage, self.settings)
        self.setCentralWidget(self.dashboard)

        # Dock: Boards
        self.boardDock = QDockWidget("Boards", self)
        self.boardDock.setObjectName("BoardsDock")
        self.boardDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.boardManager = BoardManager(self.storage, self.settings)
        self.boardDock.setWidget(self.boardManager)
        self.addDockWidget(Qt.RightDockWidgetArea, self.boardDock)

        # Menü & Aktionen
        self._build_menu()

        # Event-Bus Connects
        bus.promptsChanged.connect(self.dashboard.reload)
        bus.boardsChanged.connect(self.boardManager.reload)
        bus.copyRequested.connect(self.handle_copy_request)
        bus.dragRequested.connect(self.handle_drag_request)

    def _build_menu(self):
        menubar = self.menuBar()

        # Datei
        m_file = menubar.addMenu("Datei")
        m_file.addAction(self._action("Alle Prompts (TXT)", self.export_all_txt))
        m_file.addAction(self._action("Alle Prompts (PDF)", self.export_all_pdf))
        m_file.addSeparator()
        m_file.addAction(self._action("Aktueller Prompt (TXT)", self.export_current_prompt_txt))
        m_file.addAction(self._action("Aktueller Prompt (PDF)", self.export_current_prompt_pdf))
        m_file.addSeparator()
        m_file.addAction(self._action("Aktuelle Version (TXT)", self.export_current_version_txt))
        m_file.addAction(self._action("Aktuelle Version (PDF)", self.export_current_version_pdf))
        m_file.addSeparator()
        m_file.addAction(self._action("Beenden", QApplication.instance().quit))

        # Bearbeiten
        m_edit = menubar.addMenu("Bearbeiten")
        m_edit.addAction(self._action("Neuen Prompt erstellen", self.dashboard.create_prompt))
        m_edit.addAction(self._action("Kopier-Einstellungen …", self.open_copy_settings))

        # Ansicht
        m_view = menubar.addMenu("Ansicht")
        toggle_boards = QAction("Boards anzeigen/ausblenden", self, checkable=True)
        toggle_boards.setChecked(True)
        toggle_boards.toggled.connect(self.boardDock.setVisible)
        m_view.addAction(toggle_boards)

        # Hilfe
        m_help = menubar.addMenu("Hilfe")
        m_help.addAction(self._action("Anleitung", self._show_help))
        m_help.addAction(self._action("Über Prompt Manager", self._show_about))

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
        QMessageBox.information(self, "Über", "Prompt Manager v1.0\nModern Dark Edition")

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

    def export_current_prompt_txt(self):
        p = self.dashboard.get_current_prompt()
        if not p: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Prompt TXT", f"{p.title}.txt", "Text (*.txt)")
        if path: export_single_prompt(p, self.settings, path, parent=self)

    def export_current_prompt_pdf(self):
        p = self.dashboard.get_current_prompt()
        if not p: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Prompt PDF", f"{p.title}.pdf", "PDF (*.pdf)")
        if path: export_single_prompt(p, self.settings, path, parent=self)

    def export_current_version_txt(self):
        v = self.dashboard.get_current_version()
        if not v: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Version TXT", f"{v.title}.txt", "Text (*.txt)")
        if path: export_single_version(v, path, parent=self)

    def export_current_version_pdf(self):
        v = self.dashboard.get_current_version()
        if not v: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Version PDF", f"{v.title}.pdf", "PDF (*.pdf)")
        if path: export_single_version(v, path, parent=self)

    # --- Handlers ---
    def open_copy_settings(self):
        CopySettingsDialog(self.settings, self).exec()

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
    
    # Hier wird das Design geladen
    apply_dark_theme(app)

    settings = SettingsManager()
    # Pfad aus settings oder standard
    storage = Storage(settings.get_data_path())

    w = MainWindow(storage, settings)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()