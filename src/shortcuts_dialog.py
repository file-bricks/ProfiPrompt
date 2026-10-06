"""shortcuts_dialog.py — Barrierefreier Dialog für Tastaturkürzel nach WCAG 2.1 AA / BITV 2.0.

Strukturierte tabellarische Übersicht aller Tastenkombinationen, Konformitätshinweis,
Fokusführung und vollständige Tastaturbedienbarkeit (Escape, Return, Tab).
"""

from __future__ import annotations

from typing import List, Tuple, Optional
from PySide6.QtCore import Qt
from i18n import translate_with
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ShortcutsDialog(QDialog):
    """Barrierefreier Hilfedialog mit allen Tastaturkürzeln nach WCAG 2.1 AA / BITV 2.0."""

    SHORTCUTS: List[Tuple[str, str, str]] = [
        # (Kombination, Aktions-Schlüssel, Bereichs-Schlüssel)
        ("F1", "Tastaturkürzel & Hilfe anzeigen", "Global"),
        ("Ctrl+F", "Suche fokussieren", "Navigation"),
        ("Ctrl+N", "Neuen Prompt erstellen", "Global"),
        ("Ctrl+B", "Boards anzeigen/ausblenden", "Navigation"),
        ("Ctrl+1", "Prompt-Liste fokussieren", "Navigation"),
        ("Ctrl+2", "Board-Bereich fokussieren", "Navigation"),
        ("Ctrl+,", "Darstellungseinstellungen öffnen", "Global"),
        ("Ctrl+Shift+C", "Kopier-Einstellungen öffnen", "Global"),
        ("Ctrl+Q", "Anwendung beenden", "Global"),
        ("F5", "Ansicht & Daten aktualisieren", "Global"),
        ("Alt+D", "Menü Datei öffnen", "Navigation"),
        ("Alt+B", "Menü Bearbeiten öffnen", "Navigation"),
        ("Alt+A", "Menü Ansicht öffnen", "Navigation"),
        ("Alt+S", "Menü Sprache öffnen", "Navigation"),
        ("Alt+H", "Menü Hilfe öffnen", "Navigation"),
        ("Eingabe / Return", "Ausgewählten Prompt / Version bearbeiten", "Prompt-Liste"),
        ("Entf / Backspace", "Ausgewählten Prompt / Version löschen", "Prompt-Liste"),
        ("F2", "Ausgewählten Prompt bearbeiten", "Prompt-Liste"),
        ("Ctrl+C", "Prompt-Text in Zwischenablage kopieren", "Prompt-Liste"),
        ("Eingabe / Return", "Kachel bearbeiten / Details öffnen", "Board"),
        ("Leertaste", "Kachel aktivieren / auswählen", "Board"),
        ("Ctrl+C", "Kachel-Text in Zwischenablage kopieren", "Board"),
        ("Entf / Backspace", "Kachel vom Board entfernen", "Board"),
        ("Kontextmenü / Shift+F10", "Kachel auf anderes Board verschieben / duplizieren", "Board"),
        ("Kontextmenü / Shift+F10", "Kachelfarbe ändern", "Board"),
        ("Kontextmenü / Shift+F10", "Kontextmenü öffnen", "Global"),
    ]

    def __init__(self, parent: Optional[QWidget] = None, translator=None) -> None:
        super().__init__(parent)
        self.translator = translator
        self.setModal(True)
        self.setMinimumSize(660, 520)
        self.resize(720, 560)
        self.setObjectName("ShortcutsDialog")

        self._setup_ui()
        self.retranslate_ui()

    def _t(self, key: str) -> str:
        # Ohne injizierten Translator: gemeinsamer App-Translator (aktive Sprache)
        return translate_with(self.translator, key)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Titel & Überschrift
        self._lbl_titel = QLabel()
        self._lbl_titel.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        self._lbl_titel.setAccessibleName("Titel Tastaturkürzel und Barrierefreiheit")
        layout.addWidget(self._lbl_titel)

        # A11y / BITV 2.0 Hinweis
        self._lbl_a11y = QLabel()
        self._lbl_a11y.setWordWrap(True)
        self._lbl_a11y.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4;")
        self._lbl_a11y.setAccessibleName("Hinweis zur Barrierefreiheit")
        layout.addWidget(self._lbl_a11y)

        # Tabelle
        self._table = QTableWidget(self)
        self._table.setObjectName("ShortcutsTable")
        self._table.setColumnCount(3)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setAccessibleName("Tabelle der Tastenkombinationen")
        self._table.setAccessibleDescription("Übersicht aller verfügbaren Tastenkombinationen nach WCAG 2.1 AA")
        layout.addWidget(self._table)

        # Schließen-Button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self._btn_close = QPushButton()
        self._btn_close.setObjectName("ShortcutsCloseBtn")
        self._btn_close.setDefault(True)
        self._btn_close.setMinimumWidth(110)
        self._btn_close.clicked.connect(self.accept)
        self._btn_close.setAccessibleName("Schließen")
        self._btn_close.setAccessibleDescription("Schließt diesen Hilfedialog")
        bottom_layout.addWidget(self._btn_close)

        layout.addLayout(bottom_layout)

        # Initialer Fokus auf den Schließen-Button
        self._btn_close.setFocus()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self._t("Tastaturkürzel & Barrierefreiheit"))
        self._lbl_titel.setText(self._t("Tastaturkürzel & Barrierefreiheit"))
        self._lbl_a11y.setText(self._t(
            "Diese Anwendung unterstützt barrierefreie Tastaturbedienung nach BITV 2.0 und WCAG 2.1 AA. "
            "Alle Funktionen sind ohne Maus über standardisierte Tastaturbefehle erreichbar."
        ))

        self._table.setHorizontalHeaderLabels([
            self._t("Tastenkombination"),
            self._t("Funktion / Aktion"),
            self._t("Bereich"),
        ])

        self._table.setRowCount(len(self.SHORTCUTS))
        for row_idx, (keys, action, scope) in enumerate(self.SHORTCUTS):
            # Tastennamen wie "Entf", "Leertaste" sind sprachabhaengig
            item_keys = QTableWidgetItem(self._t(keys))
            item_keys.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            font = item_keys.font()
            font.setBold(True)
            item_keys.setFont(font)

            item_action = QTableWidgetItem(self._t(action))
            item_action.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            item_scope = QTableWidgetItem(self._t(scope))
            item_scope.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self._table.setItem(row_idx, 0, item_keys)
            self._table.setItem(row_idx, 1, item_action)
            self._table.setItem(row_idx, 2, item_scope)

        self._btn_close.setText(self._t("Schließen"))

    def get_shortcuts_list(self) -> List[Tuple[str, str, str]]:
        """Liefert alle Tastaturkürzel-Einträge für automatisierte Tests."""
        return list(self.SHORTCUTS)
