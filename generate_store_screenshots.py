from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from PySide6 import QtCore
from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from models import Board, BoardItem, Prompt, Version
from platform_smoke import SmokeSettings
from profiprompt import MainWindow, apply_dark_theme
from storage import Storage


def seed_store_storage(storage: Storage) -> None:
    prompts = [
        Prompt(
            id="p-store-1",
            title="Kundenmail strukturiert beantworten",
            purpose="Antworten für Supportfälle konsistent aufbauen",
            text="Formuliere eine kurze, freundliche Antwort mit klaren nächsten Schritten.",
            tags=["support", "überblick", "deutsch"],
            last_result="Gerne. Hier sind die drei nächsten Schritte für Ihr Team.",
            created_at="2026-06-10T08:30:00+00:00",
            updated_at="2026-06-12T07:45:00+00:00",
            versions=[
                Version(
                    id="v-store-1a",
                    prompt_id="p-store-1",
                    version_number=1,
                    title="Kurzfassung",
                    text="Antworte knapp, freundlich und mit drei Stichpunkten.",
                    result="1. Problem bestätigen 2. Lösung nennen 3. Termin anbieten",
                    tags=["knapp", "mobil"],
                    created_at="2026-06-10T08:30:00+00:00",
                    updated_at="2026-06-10T08:30:00+00:00",
                ),
                Version(
                    id="v-store-1b",
                    prompt_id="p-store-1",
                    version_number=2,
                    title="Ausführlich",
                    text="Antworte empathisch, erkläre Ursache und gib einen klaren Maßnahmenplan.",
                    result="Vielen Dank für die Rückmeldung. Wir prüfen den Fall heute und senden bis 16 Uhr ein Update.",
                    tags=["support", "kundenkontakt"],
                    created_at="2026-06-11T09:00:00+00:00",
                    updated_at="2026-06-12T07:45:00+00:00",
                ),
            ],
        ),
        Prompt(
            id="p-store-2",
            title="Meeting-Zusammenfassung",
            purpose="Besprechungen für Teams und Stakeholder verdichten",
            text="Fasse das Meeting in Entscheidungen, Risiken und offenen Punkten zusammen.",
            tags=["meeting", "analyse"],
            last_result="Entscheidung: Pilot startet Montag. Risiko: fehlende Freigabe für iOS.",
            created_at="2026-06-09T11:15:00+00:00",
            updated_at="2026-06-11T15:00:00+00:00",
            versions=[
                Version(
                    id="v-store-2a",
                    prompt_id="p-store-2",
                    version_number=1,
                    title="Stakeholder",
                    text="Schreibe für Stakeholder mit Fokus auf Entscheidungen und Risiken.",
                    result="Pilot freigegeben, zwei Abhängigkeiten bleiben offen.",
                    tags=["stakeholder"],
                    created_at="2026-06-09T11:15:00+00:00",
                    updated_at="2026-06-11T15:00:00+00:00",
                )
            ],
        ),
        Prompt(
            id="p-store-3",
            title="Produkt-Briefing für Launch",
            purpose="Produkt- und Marketingteams auf denselben Stand bringen",
            text="Erstelle ein Briefing mit Zielgruppe, Nutzenversprechen und Risiken.",
            tags=["launch", "produkt"],
            last_result="Zielgruppe: Teams mit wiederkehrender Prompt-Arbeit. Risiko: fehlende Import-Schulung.",
            created_at="2026-06-08T07:00:00+00:00",
            updated_at="2026-06-10T12:20:00+00:00",
        ),
        Prompt(
            id="p-store-4",
            title="Social-Post für Release",
            purpose="Kurzen Launch-Post mit Call-to-Action formulieren",
            text="Schreibe einen klaren Post für LinkedIn mit Nutzen, Screenshot-Hinweis und Download-Link.",
            tags=["social", "release"],
            last_result="Neu in ProfiPrompt: Boards, Versionierung und Export ohne Cloud-Zwang.",
            created_at="2026-06-07T13:30:00+00:00",
            updated_at="2026-06-09T18:05:00+00:00",
        ),
    ]
    boards = [
        Board(
            id="b-store-1",
            title="Kundenarbeit",
            description="Prompts für Support und Kommunikation.",
            items=[
                BoardItem(
                    id="bi-store-1",
                    board_id="b-store-1",
                    prompt_id="p-store-1",
                    version_id="v-store-1b",
                    created_at="2026-06-12T07:45:00+00:00",
                ),
                BoardItem(
                    id="bi-store-2",
                    board_id="b-store-1",
                    prompt_id="p-store-2",
                    version_id="v-store-2a",
                    created_at="2026-06-11T15:00:00+00:00",
                ),
            ],
            created_at="2026-06-10T08:00:00+00:00",
        ),
        Board(
            id="b-store-2",
            title="Launch-Woche",
            description="Prompts für Release-Kommunikation und Briefings.",
            items=[
                BoardItem(
                    id="bi-store-3",
                    board_id="b-store-2",
                    prompt_id="p-store-3",
                    created_at="2026-06-10T12:20:00+00:00",
                ),
                BoardItem(
                    id="bi-store-4",
                    board_id="b-store-2",
                    prompt_id="p-store-4",
                    created_at="2026-06-09T18:05:00+00:00",
                ),
            ],
            created_at="2026-06-09T10:00:00+00:00",
        ),
    ]
    storage.save_prompts(prompts)
    storage.save_boards(boards)


def _force_native_platform() -> None:
    """Entfernt eine erzwungene offscreen-Plattform VOR der QApplication-Erzeugung.

    WICHTIG (Root-Cause des Tofu-Bugs): Unter QT_QPA_PLATFORM=offscreen rendert
    Qt auf Windows KEINE echten Glyphen -- jede Glyphe wird als .notdef-Kaestchen
    (Tofu) gerastert. window.grab() liefert dann ein Bild voller Kaestchen. Fuer
    lesbare Screenshots muss die native Plattform aktiv sein; das Fenster bleibt
    trotzdem unsichtbar (Qt.WA_DontShowOnScreen).
    """
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and QApplication.instance() is None:
        del os.environ["QT_QPA_PLATFORM"]


def _render_char(ch: str, font: QFont, size: QSize) -> bytes:
    pm = QPixmap(size)
    pm.fill(QtCore.Qt.white)
    p = QPainter(pm)
    p.setFont(font)
    p.drawText(pm.rect(), QtCore.Qt.AlignCenter, ch)
    p.end()
    return bytes(pm.toImage().constBits())


def font_rendering_works(app: QApplication) -> bool:
    """True, wenn die aktuelle Plattform echte Glyphen rendert.

    Rendert mehrere unterschiedliche Zeichen einzeln. Bei echtem Rendering sehen
    sie verschieden aus; bei Tofu ist jedes das gleiche .notdef-Kaestchen -> alle
    Renderings identisch.
    """
    font = app.font()
    size = QSize(48, 48)
    probes = ["A", "B", "g", "8", "M"]
    renders = [_render_char(ch, font, size) for ch in probes]
    blank = _render_char(" ", font, size)
    distinct = len(set(renders))
    non_blank = sum(1 for r in renders if r != blank)
    return distinct >= 3 and non_blank >= len(probes) - 1


def _assert_font_rendering(app: QApplication) -> None:
    platform = QApplication.platformName()
    if platform == "offscreen":
        raise RuntimeError(
            "Qt laeuft unter der 'offscreen'-Plattform -- Screenshots wuerden Tofu "
            "(Kaestchen statt Text) enthalten. QT_QPA_PLATFORM=offscreen nicht setzen; "
            "der Generator nutzt WA_DontShowOnScreen auf der nativen Plattform."
        )
    if not font_rendering_works(app):
        raise RuntimeError(
            f"Font-Rendering-Selbsttest fehlgeschlagen (Plattform '{platform}'): "
            "gerenderte Glyphen sind nicht unterscheidbar (Tofu-Verdacht). "
            "Abbruch, um kein defektes Screenshot-Set zu erzeugen."
        )


def _select_tree_item(window: MainWindow, prompt_index: int, version_index: int | None = None) -> None:
    tree = window.dashboard.tree
    item = tree.topLevelItem(prompt_index)
    if item is None:
        raise RuntimeError(f"Prompt-Index {prompt_index} ist nicht verfügbar.")
    if version_index is not None:
        item = item.child(version_index)
        if item is None:
            raise RuntimeError(
                f"Versions-Index {version_index} für Prompt {prompt_index} ist nicht verfügbar."
            )
    tree.setCurrentItem(item)
    tree.scrollToItem(item, tree.ScrollHint.PositionAtTop)


def _set_board(window: MainWindow, title: str) -> None:
    combo = window.boardManager.board_combo
    index = combo.findText(title)
    if index < 0:
        raise RuntimeError(f"Board '{title}' wurde nicht gefunden.")
    combo.setCurrentIndex(index)


def _capture(window: MainWindow, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = window.grab()
    if pixmap.isNull():
        raise RuntimeError(f"Screenshot konnte nicht erzeugt werden: {output_path}")
    if not pixmap.save(str(output_path), "PNG"):
        raise RuntimeError(f"Screenshot konnte nicht gespeichert werden: {output_path}")
    resolved = output_path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def render_store_screenshots(output_dir: str | Path, *, headless: bool = True) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if headless:
        _force_native_platform()

    app = QApplication.instance() or QApplication([])
    apply_dark_theme(app)
    _assert_font_rendering(app)

    summary_path = output_dir / "summary.json"

    with tempfile.TemporaryDirectory(prefix="profiprompt-store-") as temp_dir:
        storage = Storage(Path(temp_dir) / "data")
        settings = SmokeSettings()
        seed_store_storage(storage)

        window = MainWindow(storage, settings)
        # Fenster nie sichtbar zeigen, aber echtes Rendering auf nativer Plattform.
        window.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
        window.resize(1600, 960)
        window.show()
        window.raise_()
        window.boardDock.setMinimumWidth(420)
        window.resizeDocks([window.boardDock], [430], QtCore.Qt.Horizontal)
        app.processEvents()

        screenshots: dict[str, str] = {}

        _set_board(window, "Kundenarbeit")
        _select_tree_item(window, 0)
        app.processEvents()
        screenshots["main-window"] = _capture(window, output_dir / "main-window.png")

        window.dashboard.search_edit.setText("meeting")
        app.processEvents()
        _select_tree_item(window, 0, 0)
        app.processEvents()
        screenshots["search-and-versions"] = _capture(
            window, output_dir / "search-and-versions.png"
        )

        window.dashboard.search_edit.clear()
        _set_board(window, "Launch-Woche")
        app.processEvents()
        _select_tree_item(window, 2)
        app.processEvents()
        screenshots["boards-and-launch"] = _capture(
            window, output_dir / "boards-and-launch.png"
        )

        window.dashboard.search_edit.setText("support")
        app.processEvents()
        _select_tree_item(window, 0, 1)
        app.processEvents()
        screenshots["support-focus"] = _capture(window, output_dir / "support-focus.png")

        summary = {
            "headless": headless,
            "qt_platform": os.environ.get("QT_QPA_PLATFORM", ""),
            "screenshots": screenshots,
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        window.close()
        app.processEvents()

    return summary


def main() -> int:
    output_dir = PROJECT_ROOT / "README" / "screenshots" / "store"
    summary = render_store_screenshots(output_dir)
    print("Store-Screenshots erfolgreich erzeugt.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
