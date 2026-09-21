"""Vertragstests für App-Icons und Asset-Suiten von ProfiPrompt.

Prüft Master-Icons, Multi-Layer Windows-ICOs, Assets-Parität,
Mobile/PWA-Suite, Store-Assets und Laufzeit-Icon-Lader.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import struct

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_ico_sizes(ico_path: Path) -> list[tuple[int, int]]:
    with open(ico_path, "rb") as f:
        _reserved, ico_type, count = struct.unpack("<HHH", f.read(6))
        assert ico_type == 1, f"{ico_path.name} ist keine gültige ICO-Datei"
        sizes: list[tuple[int, int]] = []
        for _ in range(count):
            w, h, _colors, _res, _planes, _bpp, _size, _offset = struct.unpack(
                "<BBBBHHII", f.read(16)
            )
            sizes.append((w or 256, h or 256))
        return sizes


def test_master_icons_exist() -> None:
    desktop_png = PROJECT_ROOT / "DesktopIcon.png"
    icon_png = PROJECT_ROOT / "icon.png"
    profiprompt_png = PROJECT_ROOT / "ProfiPrompt.png"
    profiprompt_ico = PROJECT_ROOT / "ProfiPrompt.ico"
    desktop_ico = PROJECT_ROOT / "DesktopIcon.ico"
    root_ico = PROJECT_ROOT / "ICO.ico"
    icon_ico = PROJECT_ROOT / "icon.ico"
    fav_ico = PROJECT_ROOT / "favicon.ico"
    fav_png = PROJECT_ROOT / "favicon.png"

    assert desktop_png.is_file(), "DesktopIcon.png fehlt im Root"
    assert icon_png.is_file(), "icon.png fehlt im Root"
    assert profiprompt_png.is_file(), "ProfiPrompt.png fehlt im Root"
    assert profiprompt_ico.is_file(), "ProfiPrompt.ico fehlt im Root"
    assert desktop_ico.is_file(), "DesktopIcon.ico fehlt im Root"
    assert root_ico.is_file(), "ICO.ico fehlt im Root"
    assert icon_ico.is_file(), "icon.ico fehlt im Root"
    assert fav_ico.is_file(), "favicon.ico fehlt im Root"
    assert fav_png.is_file(), "favicon.png fehlt im Root"

    with Image.open(desktop_png) as img:
        assert img.size == (1024, 1024), "DesktopIcon.png muss 1024x1024 sein"

    with Image.open(icon_png) as img:
        assert img.size == (1024, 1024), "icon.png muss 1024x1024 sein"

    with Image.open(profiprompt_png) as img:
        assert img.size == (1024, 1024), "ProfiPrompt.png muss 1024x1024 sein"

    sizes = _read_ico_sizes(profiprompt_ico)
    assert len(sizes) == 7, f"ProfiPrompt.ico muss 7 Layer haben, hat {len(sizes)}"
    assert (16, 16) in sizes and (24, 24) in sizes and (32, 32) in sizes and (256, 256) in sizes

    sizes_desktop = _read_ico_sizes(desktop_ico)
    assert len(sizes_desktop) == 7, "DesktopIcon.ico muss 7 Layer haben"

    sizes_root = _read_ico_sizes(root_ico)
    assert len(sizes_root) == 7, "ICO.ico muss 7 Layer haben"

    sizes_icon = _read_ico_sizes(icon_ico)
    assert len(sizes_icon) == 7, "icon.ico muss 7 Layer haben"

    sizes_fav = _read_ico_sizes(fav_ico)
    assert len(sizes_fav) == 4, "favicon.ico muss 4 Layer haben"
    assert (16, 16) in sizes_fav and (32, 32) in sizes_fav


def test_assets_folder_parity() -> None:
    assets_dir = PROJECT_ROOT / "assets"
    assert assets_dir.is_dir(), "assets/ Verzeichnis fehlt"

    icon_png = assets_dir / "icon.png"
    desktop_png = assets_dir / "DesktopIcon.png"
    profiprompt_png = assets_dir / "ProfiPrompt.png"
    icon_ico = assets_dir / "icon.ico"
    app_icon_ico = assets_dir / "app_icon.ico"
    profiprompt_ico = assets_dir / "profiprompt.ico"
    desktop_ico = assets_dir / "DesktopIcon.ico"
    favicon_png = assets_dir / "favicon.png"
    favicon_ico = assets_dir / "favicon.ico"

    assert icon_png.is_file(), "assets/icon.png fehlt"
    assert desktop_png.is_file(), "assets/DesktopIcon.png fehlt"
    assert profiprompt_png.is_file(), "assets/ProfiPrompt.png fehlt"
    assert icon_ico.is_file(), "assets/icon.ico fehlt"
    assert app_icon_ico.is_file(), "assets/app_icon.ico fehlt"
    assert profiprompt_ico.is_file(), "assets/profiprompt.ico fehlt"
    assert desktop_ico.is_file(), "assets/DesktopIcon.ico fehlt"
    assert favicon_png.is_file(), "assets/favicon.png fehlt"
    assert favicon_ico.is_file(), "assets/favicon.ico fehlt"

    with Image.open(icon_png) as img:
        assert img.size == (1024, 1024), "assets/icon.png muss 1024x1024 sein"

    with Image.open(desktop_png) as img:
        assert img.size == (1024, 1024), "assets/DesktopIcon.png muss 1024x1024 sein"

    with Image.open(favicon_png) as img:
        assert img.size == (32, 32), "assets/favicon.png muss 32x32 sein"

    app_sizes = _read_ico_sizes(app_icon_ico)
    assert len(app_sizes) == 7, "assets/app_icon.ico muss 7 Layer haben"
    assert (24, 24) in app_sizes, "assets/app_icon.ico fehlt 24x24 Layer"

    profiprompt_sizes = _read_ico_sizes(profiprompt_ico)
    assert len(profiprompt_sizes) == 7, "assets/profiprompt.ico muss 7 Layer haben"

    icon_sizes = _read_ico_sizes(icon_ico)
    assert len(icon_sizes) == 7, "assets/icon.ico muss 7 Layer haben"

    desktop_sizes = _read_ico_sizes(desktop_ico)
    assert len(desktop_sizes) == 7, "assets/DesktopIcon.ico muss 7 Layer haben"

    fav_sizes = _read_ico_sizes(favicon_ico)
    assert (16, 16) in fav_sizes and (32, 32) in fav_sizes


def test_mobile_pwa_icons_and_manifest() -> None:
    mobile_dir = PROJECT_ROOT / "mobile_icons"
    assert mobile_dir.is_dir(), "mobile_icons/ Verzeichnis fehlt"

    required_files = [
        "icon.png",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-192.png",
        "icon-maskable-512.png",
        "apple-touch-icon.png",
        "apple-touch-icon-180.png",
        "favicon.png",
        "favicon.ico",
        "manifest.json",
    ]
    for fname in required_files:
        path = mobile_dir / fname
        assert path.is_file(), f"mobile_icons/{fname} fehlt"

    with Image.open(mobile_dir / "icon.png") as img:
        assert img.size == (1024, 1024)
    with Image.open(mobile_dir / "icon-192.png") as img:
        assert img.size == (192, 192)
    with Image.open(mobile_dir / "icon-512.png") as img:
        assert img.size == (512, 512)
    with Image.open(mobile_dir / "icon-maskable-192.png") as img:
        assert img.size == (192, 192)
    with Image.open(mobile_dir / "icon-maskable-512.png") as img:
        assert img.size == (512, 512)
    with Image.open(mobile_dir / "apple-touch-icon.png") as img:
        assert img.size == (180, 180)
    with Image.open(mobile_dir / "apple-touch-icon-180.png") as img:
        assert img.size == (180, 180)

    # Prüfe Unterordner icons/
    icons_sub = mobile_dir / "icons"
    assert icons_sub.is_dir(), "mobile_icons/icons/ fehlt"
    for fname in ("Icon-192.png", "Icon-512.png", "Icon-maskable-192.png", "Icon-maskable-512.png"):
        assert (icons_sub / fname).is_file(), f"mobile_icons/icons/{fname} fehlt"

    # W3C Web App Manifest Validierung
    manifest_data = json.loads((mobile_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["name"] == "ProfiPrompt"
    assert manifest_data["short_name"] == "ProfiPrompt"
    assert len(manifest_data["icons"]) >= 4
    for icon_entry in manifest_data["icons"]:
        icon_path = mobile_dir / icon_entry["src"]
        assert icon_path.is_file(), f"Manifest-Icon nicht gefunden: {icon_entry['src']}"


def test_store_assets() -> None:
    store_dir = PROJECT_ROOT / "store_assets"
    assert store_dir.is_dir(), "store_assets/ Verzeichnis fehlt"

    expected_sizes = {
        "icon_44x44.png": (44, 44),
        "Square44x44Logo.png": (44, 44),
        "icon_50x50.png": (50, 50),
        "Square50x50Logo.png": (50, 50),
        "StoreLogo.png": (50, 50),
        "icon_150x150.png": (150, 150),
        "Square150x150Logo.png": (150, 150),
        "icon_310x150.png": (310, 150),
        "Wide310x150Logo.png": (310, 150),
        "icon_310x310.png": (310, 310),
        "Square310x310Logo.png": (310, 310),
    }
    for filename, expected_size in expected_sizes.items():
        file_path = store_dir / filename
        assert file_path.is_file(), f"store_assets/{filename} fehlt"
        with Image.open(file_path) as img:
            assert img.size == expected_size, (
                f"{filename} hat Größe {img.size}, erwartet {expected_size}"
            )


def test_app_icon_loader_returns_valid_icon() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import sys
    from PySide6.QtWidgets import QApplication

    src_dir = PROJECT_ROOT / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from app_icon_loader import load_app_icon, get_app_icon
    from profiprompt import load_app_icon as profi_load_app_icon

    _app = QApplication.instance() or QApplication([])
    icon = load_app_icon()
    assert not icon.isNull(), "load_app_icon() liefert ein leeres (null) QIcon zurück"
    assert not get_app_icon().isNull(), "get_app_icon() liefert ein leeres (null) QIcon zurück"
    assert not profi_load_app_icon().isNull(), "profiprompt.load_app_icon() liefert ein leeres QIcon zurück"

    sizes = [s.toTuple() for s in icon.availableSizes()]
    assert (16, 16) in sizes
    assert (32, 32) in sizes
    assert (256, 256) in sizes


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main(["-v", __file__]))
