"""Theme- und Farb-Helfer fuer ProfiPrompt (Welle-1 U2 + U3).

Kapselt:
  * apply_theme(app, theme)      -- Hell-/Dunkel-Palette + globales Stylesheet.
  * board_surface_color(theme)   -- Hintergrund der Board-Flaeche je Theme.
  * derive_tile_palette(base)    -- aus EINER Basisfarbe eine kohaerente
                                    Kachel-Palette ableiten (U3).

Die Farbmathematik ist bewusst reines Python (keine Qt-Abhaengigkeit), damit
sie headless testbar bleibt.
"""
from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


# --- Standard-Kachelfarben (Default = bisherige Farben, U3) -------------------
DEFAULT_TILE_MAIN = "#5D4037"      # Haupt-Prompt: warmes Dunkel-Braun
DEFAULT_TILE_VERSION = "#37474F"   # Version: dunkles Slate-Blue

THEMES = ("dark", "light")


# --- Farb-Helfer (reines Python auf Hex-Strings) -----------------------------
def _clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(_clamp(r), _clamp(g), _clamp(b))


def lighten(hexcolor: str, factor: float) -> str:
    """Hellt eine Farbe um factor (0..1) Richtung Weiss auf."""
    r, g, b = _hex_to_rgb(hexcolor)
    return _rgb_to_hex(r + (255 - r) * factor,
                       g + (255 - g) * factor,
                       b + (255 - b) * factor)


def darken(hexcolor: str, factor: float) -> str:
    """Dunkelt eine Farbe um factor (0..1) Richtung Schwarz ab."""
    r, g, b = _hex_to_rgb(hexcolor)
    return _rgb_to_hex(r * (1 - factor), g * (1 - factor), b * (1 - factor))


def mix(hexcolor: str, other: str, factor: float) -> str:
    """Mischt hexcolor Richtung other (factor 0..1)."""
    r1, g1, b1 = _hex_to_rgb(hexcolor)
    r2, g2, b2 = _hex_to_rgb(other)
    return _rgb_to_hex(r1 + (r2 - r1) * factor,
                       g1 + (g2 - g1) * factor,
                       b1 + (b2 - b1) * factor)


def relative_luminance(hexcolor: str) -> float:
    """Relative Helligkeit 0..1 (Rec. 709)."""
    r, g, b = _hex_to_rgb(hexcolor)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def contrast_text(hexcolor: str) -> str:
    """Waehlt hellen oder dunklen Text passend zur Hintergrundfarbe."""
    return "#F5F5F5" if relative_luminance(hexcolor) < 0.5 else "#1A1A1A"


def normalize_hex(hexcolor: str, fallback: str) -> str:
    """Robuste Normalisierung auf '#RRGGBB' (Grossbuchstaben) mit Fallback."""
    try:
        r, g, b = _hex_to_rgb(hexcolor)
        return _rgb_to_hex(r, g, b)
    except Exception:
        return normalize_hex(fallback, "#000000")


# --- Kachel-Palette aus einer Basisfarbe (U3) --------------------------------
def derive_tile_palette(base_hex: str) -> dict:
    """Leitet aus einer Basis-/Hintergrundfarbe eine kohaerente Kachel-Palette ab.

    Der Nutzer waehlt pro Kacheltyp genau EINE Farbe (getrennte Farbwahl fuer
    Haupt-/Versionsprompt); Rand, Badge, Farbverlauf und Textfarben werden
    daraus deterministisch abgeleitet, damit jede Wunschfarbe stimmig wirkt und
    der Text lesbar bleibt.
    """
    base = normalize_hex(base_hex, DEFAULT_TILE_MAIN)
    text = contrast_text(base)
    badge_bg = lighten(base, 0.38)
    return {
        "base": base,
        "bg_top": base,
        "bg_bottom": darken(base, 0.15),
        "border": lighten(base, 0.22),
        "badge_bg": badge_bg,
        "badge_text": contrast_text(badge_bg),
        "text_col": text,
        "sub_col": mix(text, base, 0.35),
    }


def tile_stylesheet(palette: dict, font_family: str | None) -> str:
    """Baut das QSS einer PromptTile aus einer abgeleiteten Palette."""
    font_css = f"font-family:'{font_family}';" if font_family else ""
    bg_grad = (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 {palette['bg_top']}, stop:1 {palette['bg_bottom']})"
    )
    return f"""
    QFrame#PromptTile {{
        background: {bg_grad};
        border: 1px solid {palette['border']};
        border-radius: 8px;
        {font_css}
    }}
    QFrame#PromptTile:hover {{
        border: 1px solid {palette['badge_bg']};
    }}
    QLabel#PromptTitle {{
        font-size: 15px;
        font-weight: bold;
        color: {palette['text_col']};
    }}
    QLabel#Badge {{
        background-color: {palette['badge_bg']};
        color: {palette['badge_text']};
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 10px;
        font-weight: bold;
        max-width: 60px;
    }}
    QLabel#Subtitle {{
        color: {palette['sub_col']};
        font-size: 12px;
        font-style: italic;
    }}
    QLabel#Preview {{
        color: {palette['text_col']};
        font-size: 11px;
        background: transparent;
    }}
    """


def board_surface_color(theme: str) -> str:
    """Hintergrundfarbe der Board-Flaeche (ScrollArea/Container) je Theme."""
    return "#252525" if theme == "dark" else "#EEF1F5"


# --- Anwendungs-Themes -------------------------------------------------------
def _dark_palette() -> QPalette:
    p = QPalette()
    c_bg = QColor(40, 40, 40)
    c_base = QColor(30, 30, 30)
    c_text = QColor(220, 220, 220)
    c_highlight = QColor(66, 165, 245)
    c_highlight_text = QColor(255, 255, 255)
    c_btn = QColor(50, 50, 50)

    p.setColor(QPalette.Window, c_bg)
    p.setColor(QPalette.WindowText, c_text)
    p.setColor(QPalette.Base, c_base)
    p.setColor(QPalette.AlternateBase, c_bg)
    p.setColor(QPalette.ToolTipBase, c_highlight)
    p.setColor(QPalette.ToolTipText, c_highlight_text)
    p.setColor(QPalette.Text, c_text)
    p.setColor(QPalette.Button, c_btn)
    p.setColor(QPalette.ButtonText, c_text)
    p.setColor(QPalette.BrightText, Qt.red)
    p.setColor(QPalette.Link, c_highlight)
    p.setColor(QPalette.Highlight, c_highlight)
    p.setColor(QPalette.HighlightedText, c_highlight_text)
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
    return p


def _light_palette() -> QPalette:
    """Sauber definierte Hell-Palette (kein bloßes Invertieren)."""
    p = QPalette()
    c_window = QColor(245, 246, 248)
    c_base = QColor(255, 255, 255)
    c_alt = QColor(238, 241, 245)
    c_text = QColor(32, 32, 32)
    c_highlight = QColor(25, 118, 210)      # kraeftiges Blau
    c_highlight_text = QColor(255, 255, 255)
    c_btn = QColor(236, 236, 236)

    p.setColor(QPalette.Window, c_window)
    p.setColor(QPalette.WindowText, c_text)
    p.setColor(QPalette.Base, c_base)
    p.setColor(QPalette.AlternateBase, c_alt)
    p.setColor(QPalette.ToolTipBase, c_highlight)
    p.setColor(QPalette.ToolTipText, c_highlight_text)
    p.setColor(QPalette.Text, c_text)
    p.setColor(QPalette.Button, c_btn)
    p.setColor(QPalette.ButtonText, c_text)
    p.setColor(QPalette.BrightText, Qt.red)
    p.setColor(QPalette.Link, QColor(21, 101, 192))
    p.setColor(QPalette.Highlight, c_highlight)
    p.setColor(QPalette.HighlightedText, c_highlight_text)
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(160, 160, 160))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(160, 160, 160))
    return p


_DARK_CSS = """
    QMainWindow {{ background-color: #282828; }}
    QToolTip {{ color: #ffffff; background-color: #42A5F5; border: 1px solid #282828; }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: #2b2b2b; border: 1px solid #555; border-radius: 4px;
        padding: 4px; color: #eee; selection-background-color: #42A5F5;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid #42A5F5; }}
    QTreeWidget, QListWidget {{
        background-color: #2b2b2b; border: 1px solid #444; alternate-background-color: #323232;
    }}
    QHeaderView::section {{
        background-color: #383838; color: #ddd; padding: 4px; border: none;
        border-right: 1px solid #555; border-bottom: 1px solid #555;
    }}
    QPushButton {{
        background-color: #3d3d3d; border: 1px solid #555; border-radius: 4px;
        padding: 5px 12px; color: #eee;
    }}
    QPushButton:hover {{ background-color: #4d4d4d; border-color: #42A5F5; }}
    QPushButton:pressed {{ background-color: #42A5F5; color: white; }}
    QScrollBar:vertical {{ border: none; background: #2b2b2b; width: 10px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background: #555; min-height: 20px; border-radius: 5px; }}
    QDockWidget::title {{ background: #323232; padding-left: 5px; padding-top: 4px; }}
"""

_LIGHT_CSS = """
    QMainWindow {{ background-color: #F5F6F8; }}
    QToolTip {{ color: #ffffff; background-color: #1976D2; border: 1px solid #C4CAD2; }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: #ffffff; border: 1px solid #BBBBBB; border-radius: 4px;
        padding: 4px; color: #202020; selection-background-color: #1976D2;
        selection-color: #ffffff;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid #1976D2; }}
    QTreeWidget, QListWidget {{
        background-color: #ffffff; border: 1px solid #CCCCCC; alternate-background-color: #F0F3F7;
    }}
    QHeaderView::section {{
        background-color: #E6E8EB; color: #333; padding: 4px; border: none;
        border-right: 1px solid #CCC; border-bottom: 1px solid #CCC;
    }}
    QPushButton {{
        background-color: #ECECEC; border: 1px solid #BBBBBB; border-radius: 4px;
        padding: 5px 12px; color: #202020;
    }}
    QPushButton:hover {{ background-color: #E0E6EE; border-color: #1976D2; }}
    QPushButton:pressed {{ background-color: #1976D2; color: white; }}
    QScrollBar:vertical {{ border: none; background: #EDEDED; width: 10px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background: #C0C0C0; min-height: 20px; border-radius: 5px; }}
    QDockWidget::title {{ background: #E6E8EB; padding-left: 5px; padding-top: 4px; }}
"""


def apply_theme(app, theme: str = "dark") -> str:
    """Setzt Fusion-Style + Palette + globales Stylesheet fuer das gewaehlte Theme.

    Gibt das tatsaechlich angewandte Theme zurueck ('dark'/'light').
    Kann zur Laufzeit erneut aufgerufen werden (Live-Umschaltung).
    """
    theme = theme if theme in THEMES else "dark"
    app.setStyle("Fusion")
    if theme == "light":
        app.setPalette(_light_palette())
        app.setStyleSheet(_LIGHT_CSS.replace("{{", "{").replace("}}", "}"))
    else:
        app.setPalette(_dark_palette())
        app.setStyleSheet(_DARK_CSS.replace("{{", "{").replace("}}", "}"))
    return theme
