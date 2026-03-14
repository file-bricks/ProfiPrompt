# board_manager.py

from __future__ import annotations
import json
from typing import Optional, Dict

from PySide6 import QtWidgets, QtCore, QtGui

from models import Board, Prompt, Version, BoardItem, gen_id
from storage import Storage
from settings_manager import SettingsManager
from event_bus import bus
from clipboard_manager import ClipboardManager
from prompt_dialog import PromptDialog, VersionDialog
from pdf_exporter import export_single_prompt, export_single_version

class PromptTile(QtWidgets.QFrame):
    clicked          = QtCore.Signal(str, object)
    doubleClicked    = QtCore.Signal(str, object)
    contextRequested = QtCore.Signal(QtWidgets.QFrame, QtCore.QPoint)
    dragStart        = QtCore.Signal(str, object)

    def __init__(self, prompt: Prompt, version: Optional[Version], font_family: Optional[str], parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.version = version
        self._drag_start_pos: Optional[QtCore.QPoint] = None
        self._suppress_click = False

        self.setObjectName("PromptTile")
        self.setFixedSize(260, 190)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet(self._tile_styles(font_family))
        
        # Etwas dezenterer Schatten für Dark Mode
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        # Layout
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(14, 12, 14, 12)
        vbox.setSpacing(6)

        # Title
        title_lbl = QtWidgets.QLabel(prompt.title)
        title_lbl.setObjectName("PromptTitle")
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        vbox.addWidget(title_lbl)

        # Content Logic
        if version:
            badge_txt = f"v{version.version_number}"
            sub_txt = version.title or ""
            raw_text = version.text or ""
        else:
            badge_txt = "PROMPT"
            sub_txt = prompt.purpose or ""
            raw_text = prompt.text or ""
        
        prev_txt = raw_text[:140].replace("\n", " ")
        if len(raw_text) > 140: prev_txt += "…"

        # Badge & Subtitle
        top_row = QtWidgets.QHBoxLayout()
        badge = QtWidgets.QLabel(badge_txt)
        badge.setObjectName("Badge")
        
        subtitle = QtWidgets.QLabel(sub_txt)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)

        # Preview Text
        preview = QtWidgets.QLabel(prev_txt)
        preview.setObjectName("Preview")
        preview.setWordWrap(True)
        preview.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        vbox.addWidget(badge)
        vbox.addWidget(subtitle)
        vbox.addSpacing(4)
        vbox.addWidget(preview, stretch=1)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_custom_menu)

    def _tile_styles(self, font_family: Optional[str]) -> str:
        # DARK MODE FARBEN
        # Main Prompt: Warmes Dunkel-Orange/Braun
        # Version: Dunkles Slate-Blue
        
        font_css = f"font-family:'{font_family}';" if font_family else ""

        if self.version is None:
            # Haupt-Prompt Design
            bg_grad = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5D4037, stop:1 #4E342E)"
            border = "#8D6E63"
            badge_bg = "#FF7043"
            text_col = "#EFEBE9"
            sub_col = "#BCAAA4"
        else:
            # Version Design
            bg_grad = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #37474F, stop:1 #263238)"
            border = "#78909C"
            badge_bg = "#42A5F5"
            text_col = "#ECEFF1"
            sub_col = "#B0BEC5"

        return f"""
        QFrame#PromptTile {{
            background: {bg_grad};
            border: 1px solid {border};
            border-radius: 8px;
            {font_css}
        }}
        QFrame#PromptTile:hover {{
            border: 1px solid {badge_bg};
        }}
        QLabel#PromptTitle {{
            font-size: 15px;
            font-weight: bold;
            color: {text_col};
        }}
        QLabel#Badge {{
            background-color: {badge_bg};
            color: white;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
            max-width: 60px; /* Begrenzung damit es wie ein Tag aussieht */
        }}
        QLabel#Subtitle {{
            color: {sub_col};
            font-size: 12px;
            font-style: italic;
        }}
        QLabel#Preview {{
            color: {text_col};
            font-size: 11px;
            background: transparent;
        }}
        """

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        super().mouseMoveEvent(event)
        if not self._drag_start_pos: return
        dist = (event.pos() - self._drag_start_pos).manhattanLength()
        if dist < QtWidgets.QApplication.startDragDistance(): return

        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        payload = f"{self.prompt.id}|{self.version.id if self.version else ''}"
        mime.setText(payload)
        drag.setMimeData(mime)
        
        # Pixmap für Drag erstellen (visuelles Feedback)
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaledToWidth(150, QtCore.Qt.SmoothTransformation))
        drag.setHotSpot(QtCore.QPoint(75, 50))

        self.dragStart.emit(self.prompt.id, self.version.id if self.version else None)
        drag.exec(QtCore.Qt.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            if not self._suppress_click:
                self.clicked.emit(self.prompt.id, self.version.id if self.version else None)
            self._suppress_click = False

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        super().mouseDoubleClickEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._suppress_click = True
            self.doubleClicked.emit(self.prompt.id, self.version.id if self.version else None)

    def _on_custom_menu(self, pos: QtCore.QPoint):
        self.contextRequested.emit(self, self.mapToGlobal(pos))

class BoardManager(QtWidgets.QWidget):
    MIME = "application/x-prompt-item"

    def __init__(self, storage: Storage, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.clip = ClipboardManager(settings)

        # Header
        self.board_combo   = QtWidgets.QComboBox()
        self.btn_new_board = QtWidgets.QPushButton("Neu")
        self.btn_del_board = QtWidgets.QPushButton("Löschen")
        self.btn_font      = QtWidgets.QPushButton("Font")
        
        # Icons (optional, hier textbasiert um Ressource-Fehler zu vermeiden)
        # self.btn_new_board.setIcon(...) 

        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel("Board:"))
        header.addWidget(self.board_combo, stretch=1)
        header.addWidget(self.btn_new_board)
        header.addWidget(self.btn_del_board)
        header.addWidget(self.btn_font)

        # Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        # Style für ScrollArea Container Background im Darkmode
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #252525; }")
        
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("BoardContainer")
        self.container.setStyleSheet("QWidget#BoardContainer { background-color: #252525; }")
        
        self.grid = QtWidgets.QGridLayout(self.container)
        self.grid.setContentsMargins(20, 20, 20, 20)
        self.grid.setHorizontalSpacing(20)
        self.grid.setVerticalSpacing(20)
        self.scroll.setWidget(self.container)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.scroll)

        # Connects
        self.board_combo.currentIndexChanged.connect(self.reload_items)
        self.btn_new_board.clicked.connect(self.create_board)
        self.btn_del_board.clicked.connect(self.delete_current_board)
        self.btn_font.clicked.connect(self.choose_tile_font)
        
        bus.boardsChanged.connect(self.reload)
        bus.promptsChanged.connect(self.reload_items)

        self.setAcceptDrops(True)
        self.reload()

    def _get_tile_font_family(self) -> Optional[str]:
        fam = self.settings.qs.value("tiles/font_family", "", type=str)
        return fam or None

    def choose_tile_font(self):
        cur_fam = self._get_tile_font_family()
        cur_font = QtGui.QFont(cur_fam) if cur_fam else QtGui.QFont()
        ok, font = QtWidgets.QFontDialog.getFont(cur_font, self, "Schriftart wählen")
        if ok:
            self.settings.qs.setValue("tiles/font_family", font.family())
            self.reload_items()

    def reload(self):
        boards = self.storage.load_boards()
        cur_id = self.board_combo.currentData()
        
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        for b in boards:
            self.board_combo.addItem(b.title, b.id)
        self.board_combo.blockSignals(False)

        if cur_id:
            idx = self.board_combo.findData(cur_id)
            if idx >= 0:
                self.board_combo.setCurrentIndex(idx)
        
        self.reload_items()

    def current_board(self) -> Optional[Board]:
        bid = self.board_combo.currentData()
        if not bid: return None
        return next((b for b in self.storage.load_boards() if b.id == bid), None)

    def reload_items(self):
        # Clear Grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        board = self.current_board()
        if not board: return

        prompts_map = {p.id: p for p in self.storage.load_prompts()}
        font_family = self._get_tile_font_family()

        # Responsive Grid Logic (fixe Spaltenanzahl ist oft unflexibel, hier 3)
        cols = 3 
        row, col = 0, 0
        
        for item in board.items:
            p = prompts_map.get(item.prompt_id)
            if not p: continue
            
            v = None
            if item.version_id:
                v = next((x for x in p.versions if x.id == item.version_id), None)

            tile = PromptTile(p, v, font_family, self)
            tile.clicked.connect(self._on_tile_clicked)
            tile.doubleClicked.connect(self._on_tile_double_clicked)
            tile.contextRequested.connect(self._on_tile_context_menu)

            self.grid.addWidget(tile, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        # Spacer damit alles oben links bleibt
        spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.grid.addItem(spacer, row + 1, 0)

    # --- Actions ---
    def create_board(self):
        title, ok = QtWidgets.QInputDialog.getText(self, "Neues Board", "Name:")
        if ok and title.strip():
            b = Board(id=gen_id(), title=title.strip(), items=[])
            self.storage.upsert_board(b)
            bus.boardsChanged.emit()

    def delete_current_board(self):
        b = self.current_board()
        if not b: return
        if QtWidgets.QMessageBox.question(self, "Löschen", f"Board '{b.title}' wirklich löschen?") == QtWidgets.QMessageBox.Yes:
            self.storage.delete_board(b.id)
            bus.boardsChanged.emit()

    # --- Interactions ---
    def _on_tile_clicked(self, pid, vid):
        p = self.storage.get_prompt(pid)
        if not p: return
        v = self.storage.get_version(pid, vid) if vid else None
        txt = self.clip.build_copy_text(p, v)
        self.clip.copy_to_clipboard(self, txt)

    def _on_tile_double_clicked(self, pid, vid):
        p = self.storage.get_prompt(pid)
        if not p: return
        if vid:
            v = self.storage.get_version(pid, vid)
            if VersionDialog(self.storage, p, v, self).exec():
                bus.promptsChanged.emit()
        else:
            if PromptDialog(self.storage, p, self).exec():
                bus.promptsChanged.emit()

    def _on_tile_context_menu(self, tile, gpos):
        menu = QtWidgets.QMenu(self)
        menu.addAction("Kopieren", lambda: self._on_tile_clicked(tile.prompt.id, tile.version.id if tile.version else None))
        menu.addAction("Bearbeiten", lambda: self._on_tile_double_clicked(tile.prompt.id, tile.version.id if tile.version else None))
        menu.addSeparator()
        menu.addAction("Vom Board entfernen", lambda: self._remove_item_from_board(tile))
        menu.exec(gpos)

    def _remove_item_from_board(self, tile):
        board = self.current_board()
        if not board: return

        pid = tile.prompt.id
        vid = tile.version.id if tile.version else None

        # Nur das ERSTE passende Item entfernen (pop by index), Duplikate bleiben erhalten
        removed_one = False
        new_items = []
        for i in board.items:
            if not removed_one and i.prompt_id == pid and i.version_id == vid:
                removed_one = True
                continue
            new_items.append(i)

        board.items = new_items
        self.storage.upsert_board(board)
        self.reload_items()

    # --- Drag & Drop ---
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasFormat(self.MIME) or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasFormat(self.MIME) or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent):
        md = event.mimeData()
        board = self.current_board()
        if not board: return

        pid, vid = None, None

        if md.hasFormat(self.MIME):
            # Format: json [kind, pid, vid?]
            blob = md.data(self.MIME).data().decode("utf-8")
            arr = json.loads(blob)
            pid = arr[1]
            if len(arr) > 2: vid = arr[2]
        
        elif md.hasText():
            # Format: "pid|vid" (aus PromptTile)
            parts = md.text().split("|")
            pid = parts[0]
            if len(parts) > 1 and parts[1]: vid = parts[1]

        if pid:
            ok, _ = self.storage.add_item_to_board(board.id, pid, vid)
            if ok: self.reload_items()
            
        event.acceptProposedAction()