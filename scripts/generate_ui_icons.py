"""Erzeugt transparente UI-Icons fuer die Prompt-Liste (Welle-1 U4).

Ersetzt die frueheren, nicht transparenten .ico/.jpg-Icons (Clipboard,
Bueroklammer) durch echte transparente PNGs mit Alphakanal. Es werden je zwei
Varianten erzeugt:
  * <name>-light.png : helle Linien   -> fuer dunkles Theme
  * <name>-dark.png  : dunkle Linien  -> fuer helles Theme

Aufruf:  PYTHONIOENCODING=utf-8 python scripts/generate_ui_icons.py

Die Vektorquellen sind schlanke Linien-Icons (Feather-Stil, MIT); gerendert wird
zu 128x128 px transparentem PNG, damit die App zur Laufzeit keine SVG-Engine
braucht (robust auch im PyInstaller-Build).
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QByteArray  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

ICON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "icons"
)

_CLIPBOARD = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'
 stroke='{c}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
 <path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/>
 <rect x='8' y='2' width='8' height='4' rx='1' ry='1'/>
</svg>"""

_PAPERCLIP = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'
 stroke='{c}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
 <path d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'/>
</svg>"""

VARIANTS = {"light": "#E8EAED", "dark": "#3A3F45"}
SIZE = 128
ICONS = {"clipboard": _CLIPBOARD, "paperclip": _PAPERCLIP}


def render(svg_tpl: str, color: str, out_path: str):
    svg = svg_tpl.format(c=color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    if not img.save(out_path, "PNG"):
        raise RuntimeError(f"Konnte {out_path} nicht schreiben")
    print(f"[ok] {out_path}")


def main():
    _ = QApplication.instance() or QApplication(sys.argv)
    os.makedirs(ICON_DIR, exist_ok=True)
    for name, tpl in ICONS.items():
        for variant, color in VARIANTS.items():
            render(tpl, color, os.path.join(ICON_DIR, f"{name}-{variant}.png"))
    print(f"Fertig: {2 * len(ICONS)} transparente Icons in {ICON_DIR}")


if __name__ == "__main__":
    main()
