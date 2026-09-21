"""App-Icon-Loader für ProfiPrompt mit robuster Multi-Pfad-Auflösung."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QIcon


def get_project_root() -> Path:
    """Ermittelt das Projekt-Root-Verzeichnis (Quelltext oder PyInstaller-Bundle)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def load_app_icon() -> QIcon:
    """Lädt das Anwendungs-Icon mit Multi-Pfad-Fallback.

    Unterstützt Quelltext-Ausführung, PyInstaller (_MEIPASS) und
    verschiedene Asset-Pfade (assets/app_icon.ico, assets/icon.ico,
    assets/profiprompt.ico, assets/DesktopIcon.ico, assets/icon.png,
    ProfiPrompt.ico, DesktopIcon.ico, ICO.ico, icon.ico, icon.png, DesktopIcon.png).
    """
    root = get_project_root()
    candidates = [
        root / "assets" / "app_icon.ico",
        root / "assets" / "icon.ico",
        root / "assets" / "profiprompt.ico",
        root / "assets" / "DesktopIcon.ico",
        root / "assets" / "icon.png",
        root / "ProfiPrompt.ico",
        root / "DesktopIcon.ico",
        root / "ICO.ico",
        root / "icon.ico",
        root / "icon.png",
        root / "DesktopIcon.png",
    ]
    for candidate in candidates:
        if candidate.is_file():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


get_app_icon = load_app_icon
