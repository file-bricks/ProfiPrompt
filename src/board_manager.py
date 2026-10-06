# board_manager.py

from __future__ import annotations
import json
from typing import Optional, Dict

from PySide6 import QtWidgets, QtCore, QtGui

from models import Board, Prompt, Version, BoardItem, gen_id
from storage import Storage
from storage_actions import report_storage_errors
from settings_manager import SettingsManager
from event_bus import bus
from clipboard_manager import ClipboardManager
from prompt_dialog import PromptDialog, VersionDialog
from pdf_exporter import export_single_prompt, export_single_version
import theme as theme_mod
from i18n import tr

class PromptTile(QtWidgets.QFrame):
    clicked          = QtCore.Signal(str, object)
    doubleClicked    = QtCore.Signal(str, object)
    contextRequested = QtCore.Signal(QtWidgets.QFrame, QtCore.QPoint)
    dragStart        = QtCore.Signal(str, object)
    removeRequested  = QtCore.Signal(QtWidgets.QFrame)

    def __init__(self, prompt: Prompt, version: Optional[Version], font_family: Optional[str],
                 tile_palette: Optional[Dict] = None, parent=None, color: Optional[str] = None):
        super().__init__(parent)
        self.prompt = prompt
        self.version = version
        self.color = color  # individuelle Kachelfarbe (None => Standardfarbe der Kachelart)
        self._drag_start_pos: Optional[QtCore.QPoint] = None
        self._suppress_click = False

        self.setObjectName("PromptTile")
        self.setFixedSize(260, 190)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(self._tile_styles(font_family, tile_palette))
        if version:
            v_title = version.title or ""
            self.setAccessibleName(tr("Prompt-Kachel: {title}", title=f"{prompt.title} (v{version.version_number} — {v_title})").strip())
        else:
            self.setAccessibleName(tr("Prompt-Kachel: {title}", title=prompt.title))
        
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
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
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
        badge.setAccessibleName(tr("Kachel-Typ: {badge}", badge=badge_txt))
        
        subtitle = QtWidgets.QLabel(sub_txt)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAccessibleName(tr("Kachel-Untertitel: {text}", text=sub_txt))

        # Preview Text
        preview = QtWidgets.QLabel(prev_txt)
        preview.setObjectName("Preview")
        preview.setWordWrap(True)
        preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        preview.setAccessibleName(tr("Kachel-Vorschau: {text}", text=prev_txt))

        vbox.addWidget(badge)
        vbox.addWidget(subtitle)
        vbox.addSpacing(4)
        vbox.addWidget(preview, stretch=1)

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_custom_menu)
        self.setAccessibleDescription(f"{badge_txt}: {sub_txt}. {prev_txt}")

    def _tile_styles(self, font_family: Optional[str], palette: Optional[Dict] = None) -> str:
        # Kachelfarben sind konfigurierbar (U3): der Aufrufer liefert eine aus der
        # gewaehlten Basisfarbe abgeleitete Palette. Fallback = Default-Basisfarbe
        # der jeweiligen Kachelart (Haupt-Prompt vs. Version).
        if palette is None:
            base = (theme_mod.DEFAULT_TILE_MAIN if self.version is None
                    else theme_mod.DEFAULT_TILE_VERSION)
            palette = theme_mod.derive_tile_palette(base)
        return theme_mod.tile_stylesheet(palette, font_family)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        super().mouseMoveEvent(event)
        if not self._drag_start_pos: return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        dist = (pos - self._drag_start_pos).manhattanLength()
        if dist < QtWidgets.QApplication.startDragDistance(): return

        # Klick bei Drag-Release unterdrücken (BUG-BM05)
        self._suppress_click = True

        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        payload = f"{self.prompt.id}|{self.version.id if self.version else ''}"
        mime.setText(payload)
        arr_payload = json.dumps(["version" if self.version else "prompt", self.prompt.id, self.version.id if self.version else None])
        mime.setData(BoardManager.MIME, arr_payload.encode("utf-8"))
        drag.setMimeData(mime)
        
        # Pixmap für Drag erstellen (visuelles Feedback)
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaledToWidth(150, QtCore.Qt.TransformationMode.SmoothTransformation))
        drag.setHotSpot(QtCore.QPoint(75, 50))

        self.dragStart.emit(self.prompt.id, self.version.id if self.version else None)
        drag.exec(QtCore.Qt.DropAction.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not self._suppress_click:
                self.clicked.emit(self.prompt.id, self.version.id if self.version else None)
            self._suppress_click = False

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        super().mouseDoubleClickEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._suppress_click = True
            self.doubleClicked.emit(self.prompt.id, self.version.id if self.version else None)

    def _on_custom_menu(self, pos: QtCore.QPoint):
        self.contextRequested.emit(self, self.mapToGlobal(pos))


    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self.doubleClicked.emit(self.prompt.id, self.version.id if self.version else None)
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key.Key_Space:
            self.clicked.emit(self.prompt.id, self.version.id if self.version else None)
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key.Key_C and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            bus.copyRequested.emit("version" if self.version else "prompt", self.version.id if self.version else self.prompt.id, self)
            event.accept()
            return
        elif event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.removeRequested.emit(self)
            p = self.parent()
            while p and not hasattr(p, "remove_tile_item"):
                p = p.parent()
            if p and hasattr(p, "remove_tile_item"):
                p.remove_tile_item(self.prompt.id, self.version.id if self.version else None)
            event.accept()
            return
        elif event.key() in (QtCore.Qt.Key.Key_Menu, QtCore.Qt.Key.Key_F10):
            self.contextRequested.emit(self, self.mapToGlobal(QtCore.QPoint(10, 10)))
            event.accept()
            return
        super().keyPressEvent(event)

class BoardManager(QtWidgets.QWidget):
    MIME = "application/x-prompt-item"

    # Vordefinierte Kachelfarben fuer das Kontextmenue (Name = Uebersetzungs-Key).
    TILE_COLOR_PRESETS = (
        ("Rot", "#B23A48"),
        ("Orange", "#C8682C"),
        ("Gelb", "#C9A227"),
        ("Grün", "#3E7D4F"),
        ("Türkis", "#1F7A7A"),
        ("Blau", "#2F5D9E"),
        ("Violett", "#6A4C93"),
        ("Rosa", "#B0577E"),
        ("Grau", "#5F6B73"),
    )

    def __init__(self, storage: Storage, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self.clip = ClipboardManager(settings)

        # Header
        self.board_combo   = QtWidgets.QComboBox()
        self.btn_new_board = QtWidgets.QPushButton()
        self.btn_ren_board = QtWidgets.QPushButton()
        self.btn_del_board = QtWidgets.QPushButton()
        self.btn_font      = QtWidgets.QPushButton()

        self.lbl_board = QtWidgets.QLabel()
        self.lbl_board.setBuddy(self.board_combo)

        header = QtWidgets.QHBoxLayout()
        header.addWidget(self.lbl_board)
        header.addWidget(self.board_combo, stretch=1)
        header.addWidget(self.btn_new_board)
        header.addWidget(self.btn_ren_board)
        header.addWidget(self.btn_del_board)
        header.addWidget(self.btn_font)

        # Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QtWidgets.QWidget()
        self.container.setObjectName("BoardContainer")

        # Board-Flaechen-Hintergrund folgt dem Theme (U2)
        self._apply_surface_styles()

        self.grid = QtWidgets.QGridLayout(self.container)
        self.grid.setContentsMargins(20, 20, 20, 20)
        self.grid.setHorizontalSpacing(20)
        self.grid.setVerticalSpacing(20)
        self.grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.container)
        self.scroll.viewport().installEventFilter(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.scroll)

        self.retranslate_ui()

        # Connects
        self.board_combo.currentIndexChanged.connect(self.reload_items)
        self.btn_new_board.clicked.connect(self.create_board)
        self.btn_ren_board.clicked.connect(self.rename_current_board)
        self.btn_del_board.clicked.connect(self.delete_current_board)
        self.btn_font.clicked.connect(self.choose_tile_font)

        bus.boardsChanged.connect(self.reload)
        bus.promptsChanged.connect(self.reload_items)
        bus.languageChanged.connect(self._on_language_changed)

        self.setAcceptDrops(True)
        self.reload()

    def retranslate_ui(self):
        """Setzt alle statischen Texte der Board-Leiste in der aktiven Sprache."""
        self.lbl_board.setText(tr("Board:"))
        self.btn_new_board.setText(tr("Neu"))
        self.btn_ren_board.setText(tr("Umbenennen"))
        self.btn_del_board.setText(tr("Löschen"))
        self.btn_font.setText(tr("Schriftart"))

        self.board_combo.setAccessibleName(tr("Aktives Board"))
        self.board_combo.setAccessibleDescription(tr("Wählt das aktive Prompt-Board aus"))
        self.btn_new_board.setAccessibleName(tr("Neues Board"))
        self.btn_new_board.setAccessibleDescription(tr("Erstellt ein neues leeres Prompt-Board"))
        self.btn_ren_board.setAccessibleName(tr("Board umbenennen"))
        self.btn_ren_board.setAccessibleDescription(tr("Benennt das aktuell ausgewählte Prompt-Board um"))
        self.btn_del_board.setAccessibleName(tr("Board löschen"))
        self.btn_del_board.setAccessibleDescription(tr("Löscht das aktuell ausgewählte Prompt-Board"))
        self.btn_font.setAccessibleName(tr("Kachelschriftart wählen"))
        self.btn_font.setAccessibleDescription(tr("Öffnet die Schriftartenauswahl für Board-Kacheln"))

        self.scroll.setAccessibleName(tr("Board-Arbeitsfläche"))
        self.scroll.setAccessibleDescription(tr("Bereich mit angehefteten Prompt-Kacheln"))
        self.container.setAccessibleName(tr("Kachel-Raster"))

    def _on_language_changed(self, _lang: str = ""):
        self.retranslate_ui()
        # Kacheln tragen uebersetzte Accessible-Names -> neu aufbauen
        self.reload_items()

    def _get_tile_font_family(self) -> Optional[str]:
        fam = self.settings.qs.value("tiles/font_family", "", type=str)
        return fam or None

    def _apply_surface_styles(self):
        """Setzt den Board-Flaechen-Hintergrund passend zum aktuellen Theme (U2)."""
        surf = theme_mod.board_surface_color(self.settings.get_theme())
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {surf}; }}")
        self.container.setStyleSheet(f"QWidget#BoardContainer {{ background-color: {surf}; }}")

    def apply_theme_and_reload(self):
        """Nach Theme-/Farbwechsel: Flaeche + Kacheln neu einfaerben (Live-Umschaltung)."""
        self._apply_surface_styles()
        self.reload_items()

    def choose_tile_font(self):
        cur_fam = self._get_tile_font_family()
        cur_font = QtGui.QFont(cur_fam) if cur_fam else QtGui.QFont()
        ok, font = QtWidgets.QFontDialog.getFont(cur_font, self, tr("Schriftart wählen"))
        if ok:
            self.settings.qs.setValue("tiles/font_family", font.family())
            self.reload_items()

    def reload(self, select_board_id: Optional[str] = None):
        boards = self.storage.load_boards()
        cur_id = select_board_id or getattr(self, "_pending_select_board_id", None) or self.board_combo.currentData()
        self._pending_select_board_id = None
        
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        for b in boards:
            self.board_combo.addItem(b.title, b.id)
        self.board_combo.blockSignals(False)

        if cur_id:
            idx = self.board_combo.findData(cur_id)
            if idx >= 0:
                self.board_combo.setCurrentIndex(idx)
        
        if hasattr(self, "btn_del_board"):
            self.btn_del_board.setEnabled(len(boards) > 0)
        if hasattr(self, "btn_ren_board"):
            self.btn_ren_board.setEnabled(len(boards) > 0)

        self.reload_items()


    @report_storage_errors
    def remove_tile_item(self, prompt_id: str, version_id: Optional[str] = None):
        board = self.current_board()
        if not board:
            return
        msg = tr("Möchten Sie diese Kachel wirklich vom Board entfernen?")
        if QtWidgets.QMessageBox.question(
            self, tr("Kachel entfernen"), msg
        ) == QtWidgets.QMessageBox.StandardButton.Yes:
            success = self.storage.remove_item_from_board(board.id, prompt_id, version_id)
            if success:
                self.reload_items()
                bus.boardsChanged.emit()

    def current_board(self) -> Optional[Board]:
        bid = self.board_combo.currentData()
        if not bid: return None
        return next((b for b in self.storage.load_boards() if b.id == bid), None)

    TILE_WIDTH = 260

    def _column_count(self) -> int:
        """Spaltenzahl passend zur sichtbaren Breite (mind. 1, max. 6)."""
        m = self.grid.contentsMargins()
        avail = self.scroll.viewport().width() - m.left() - m.right()
        step = self.TILE_WIDTH + self.grid.horizontalSpacing()
        return max(1, min(6, (avail + self.grid.horizontalSpacing()) // step))

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                # Sofort verstecken: deleteLater greift erst im Event-Loop, bis dahin
                # blieben alte Kacheln sichtbar und ueberlappten die neuen.
                w.hide()
                w.deleteLater()

    def _layout_tiles(self, tiles):
        """Ordnet Kacheln im Raster an; Spaltenzahl folgt der Dock-Breite."""
        cols = self._column_count()
        self._layout_cols = cols
        for i, tile in enumerate(tiles):
            self.grid.addWidget(tile, i // cols, i % cols)
        # Spacer damit alles oben links bleibt
        rows = (len(tiles) + cols - 1) // cols
        spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.grid.addItem(spacer, rows, 0)

    def eventFilter(self, obj, event):
        # Viewport-Breite geaendert (Dock gezogen, Scrollbar ein/aus) -> Spalten anpassen
        if obj is self.scroll.viewport() and event.type() == QtCore.QEvent.Type.Resize:
            tiles = getattr(self, "_tiles", [])
            if tiles and self._column_count() != getattr(self, "_layout_cols", None):
                # Nur neu anordnen (kein Disk-Zugriff, Kacheln bleiben erhalten)
                while self.grid.count():
                    self.grid.takeAt(0)
                self._layout_tiles(tiles)
        return super().eventFilter(obj, event)

    def reload_items(self):
        self._clear_grid()
        self._tiles = []

        board = self.current_board()
        if not board: return

        prompts_map = {p.id: p for p in self.storage.load_prompts()}
        font_family = self._get_tile_font_family()

        # Konfigurierbare Kachelfarben (U3): je eine abgeleitete Palette fuer
        # Haupt-Prompt- und Versions-Kacheln, einmal pro Reload berechnet.
        main_pal = theme_mod.derive_tile_palette(self.settings.get_tile_color("main"))
        version_pal = theme_mod.derive_tile_palette(self.settings.get_tile_color("version"))
        # Individuelle Kachelfarben: Palette je Farbe nur einmal ableiten
        custom_pals: Dict[str, Dict] = {}

        tiles = []
        for item in board.items:
            if not item:
                continue
            p = prompts_map.get(item.prompt_id)
            if not p:
                continue

            v = None
            if item.version_id:
                versions = [x for x in (getattr(p, "versions", []) or []) if x is not None]
                v = next((x for x in versions if x.id == item.version_id), None)
                if v is None:
                    # BUG-BM01: Verwaiste Version-Items duerfen nicht faelschlich als
                    # Hauptprompt gerendert werden (fuehrt zu irrefuehrender UI & unloeschbaren Kacheln)
                    continue

            item_color = getattr(item, "color", None)
            if item_color:
                pal = custom_pals.get(item_color)
                if pal is None:
                    pal = custom_pals[item_color] = theme_mod.derive_tile_palette(item_color)
            else:
                pal = version_pal if v else main_pal

            tile = PromptTile(p, v, font_family, pal, self, color=item_color)
            tile.clicked.connect(self._on_tile_clicked)
            tile.doubleClicked.connect(self._on_tile_double_clicked)
            tile.contextRequested.connect(self._on_tile_context_menu)
            tile.removeRequested.connect(self._remove_item_from_board)
            tiles.append(tile)

        self._tiles = tiles
        self._layout_tiles(tiles)

    # --- Actions ---
    def _ask_board_title(self, title: str, default: str = "") -> Optional[str]:
        text, ok = QtWidgets.QInputDialog.getText(self, title, tr("Name:"), text=default)
        if ok and text.strip():
            return text.strip()
        return None

    @report_storage_errors
    def create_board(self) -> Optional[Board]:
        title = self._ask_board_title(tr("Neues Board"))
        if title:
            b = Board(id=gen_id(), title=title, items=[])
            self.storage.upsert_board(b)
            self._pending_select_board_id = b.id
            bus.boardsChanged.emit()
            return b
        return None

    @report_storage_errors
    def rename_current_board(self):
        b = self.current_board()
        if not b:
            return
        title = self._ask_board_title(tr("Board umbenennen"), b.title)
        if title and title != b.title and self.storage.rename_board(b.id, title):
            self._pending_select_board_id = b.id
            bus.boardsChanged.emit()

    @report_storage_errors
    def delete_current_board(self):
        b = self.current_board()
        if not b: return
        if QtWidgets.QMessageBox.question(
            self, tr("Löschen"), tr("Board „{title}“ wirklich löschen?", title=b.title)
        ) == QtWidgets.QMessageBox.StandardButton.Yes:
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

    @staticmethod
    def _color_icon(hexcolor: str) -> QtGui.QIcon:
        pm = QtGui.QPixmap(16, 16)
        pm.fill(QtGui.QColor(hexcolor))
        return QtGui.QIcon(pm)

    def build_tile_context_menu(self, tile) -> QtWidgets.QMenu:
        """Baut das Kachel-Kontextmenue (separat testbar, ohne exec())."""
        pid = tile.prompt.id
        vid = tile.version.id if tile.version else None
        menu = QtWidgets.QMenu(self)
        menu.addAction(tr("Kopieren"), lambda: self._on_tile_clicked(pid, vid))
        menu.addAction(tr("Bearbeiten"), lambda: self._on_tile_double_clicked(pid, vid))
        menu.addSeparator()

        # Auf anderes Board senden (verschieben) / duplizieren (kopieren)
        board = self.current_board()
        others = [b for b in self.storage.load_boards() if board is None or b.id != board.id]
        m_move = menu.addMenu(tr("Auf Board verschieben"))
        m_copy = menu.addMenu(tr("Auf Board duplizieren"))
        for sub, move in ((m_move, True), (m_copy, False)):
            for b in others:
                sub.addAction(b.title or tr("(ohne Titel)"),
                              lambda bid=b.id, mv=move: self.transfer_tile(tile, bid, move=mv))
            if others:
                sub.addSeparator()
            sub.addAction(tr("Neues Board …"),
                          lambda mv=move: self.transfer_tile_to_new_board(tile, move=mv))
        m_move.setEnabled(board is not None)
        m_copy.setEnabled(board is not None)

        # Kachelfarbe
        m_color = menu.addMenu(tr("Kachelfarbe"))
        act_default = m_color.addAction(tr("Standardfarbe"), lambda: self.set_tile_color(tile, None))
        act_default.setCheckable(True)
        act_default.setChecked(not tile.color)
        m_color.addSeparator()
        for name, hexcolor in self.TILE_COLOR_PRESETS:
            act = m_color.addAction(self._color_icon(hexcolor), tr(name),
                                    lambda c=hexcolor: self.set_tile_color(tile, c))
            act.setCheckable(True)
            act.setChecked((tile.color or "").upper() == hexcolor)
        m_color.addSeparator()
        m_color.addAction(tr("Eigene Farbe …"), lambda: self.choose_custom_tile_color(tile))

        menu.addSeparator()
        menu.addAction(tr("Vom Board entfernen"), lambda: self._remove_item_from_board(tile))
        return menu

    def _on_tile_context_menu(self, tile, gpos):
        self.build_tile_context_menu(tile).exec(gpos)

    @report_storage_errors
    def transfer_tile(self, tile, target_board_id: str, move: bool = False) -> bool:
        """Sendet (move=True) oder dupliziert (move=False) eine Kachel auf ein anderes Board."""
        board = self.current_board()
        if not board or not target_board_id:
            return False
        pid = tile.prompt.id
        vid = tile.version.id if tile.version else None
        ok, reason = self.storage.transfer_item(board.id, target_board_id, pid, vid, move=move)
        target = next((b for b in self.storage.load_boards() if b.id == target_board_id), None)
        target_title = target.title if target else ""
        if ok:
            if move:
                self.reload_items()
            bus.boardsChanged.emit()
            msg = (tr("Kachel auf Board „{title}“ verschoben.", title=target_title) if move
                   else tr("Kachel auf Board „{title}“ dupliziert.", title=target_title))
            self._show_status(msg)
            return True
        if reason == "duplicate":
            QtWidgets.QMessageBox.information(
                self, tr("Hinweis"),
                tr("Diese Kachel ist auf Board „{title}“ bereits vorhanden.", title=target_title))
        return False

    @report_storage_errors
    def transfer_tile_to_new_board(self, tile, move: bool = False) -> bool:
        title = self._ask_board_title(tr("Neues Board"))
        if not title:
            return False
        b = Board(id=gen_id(), title=title, items=[])
        self.storage.upsert_board(b)
        return self.transfer_tile(tile, b.id, move=move)

    @report_storage_errors
    def set_tile_color(self, tile, hexcolor: Optional[str]) -> bool:
        board = self.current_board()
        if not board:
            return False
        vid = tile.version.id if tile.version else None
        if self.storage.set_item_color(board.id, tile.prompt.id, vid, hexcolor):
            self.reload_items()
            return True
        return False

    def choose_custom_tile_color(self, tile):
        if tile.color:
            initial = QtGui.QColor(tile.color)
        else:
            initial = QtGui.QColor(self.settings.get_tile_color("version" if tile.version else "main"))
        chosen = QtWidgets.QColorDialog.getColor(initial, self, tr("Kachelfarbe wählen"))
        if chosen.isValid():
            self.set_tile_color(tile, chosen.name().upper())

    def _show_status(self, message: str):
        win = self.window()
        status = win.statusBar() if isinstance(win, QtWidgets.QMainWindow) else None
        if status is not None:
            status.showMessage(message, 4000)

    @report_storage_errors
    def _remove_item_from_board(self, tile):
        board = self.current_board()
        if not board: return

        pid = tile.prompt.id
        vid = tile.version.id if tile.version else None

        if self.storage.remove_item_from_board(board.id, pid, vid):
            self.reload_items()
            bus.boardsChanged.emit()

    # --- Drag & Drop ---
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasFormat(self.MIME) or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasFormat(self.MIME) or event.mimeData().hasText():
            event.acceptProposedAction()

    @report_storage_errors
    def dropEvent(self, event: QtGui.QDropEvent):
        event.ignore()
        md = event.mimeData()
        board = self.current_board()
        if not board:
            event.ignore()
            return

        pid, vid = None, None

        if md.hasFormat(self.MIME):
            # Format: json [kind, pid, vid?]
            # Bugsweep 19 BUG-04: json.loads + arr[1] ungeschuetzt -> korrupte/fremde MIME-Daten
            # (kein Array, zu kurz) crashten den Drop. Breit fangen und Drop ignorieren.
            try:
                blob = md.data(self.MIME).data().decode("utf-8")
                arr = json.loads(blob)
                pid = arr[1]
                if len(arr) > 2: vid = arr[2]
            except (json.JSONDecodeError, IndexError, TypeError, KeyError, UnicodeDecodeError):
                event.ignore()
                return
        
        elif md.hasText():
            # Format: "pid|vid" (aus PromptTile)
            parts = md.text().split("|")
            pid = parts[0].strip() or None
            if len(parts) > 1 and parts[1].strip():
                vid = parts[1].strip()

        if pid and self.storage.get_prompt(pid):
            if vid:
                if not self.storage.get_version(pid, vid):
                    # BUG-BM04: Ungueltigen/geloeschten Versions-Drop abweisen statt faelschlich Hauptprompt anzuhaengen
                    return
            ok, _ = self.storage.add_item_to_board(board.id, pid, vid)
            if ok:
                self.reload_items()
                bus.boardsChanged.emit()
                event.acceptProposedAction()
                return

        event.ignore()
