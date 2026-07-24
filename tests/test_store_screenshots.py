import os
import re
import struct
import sys
from pathlib import Path

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import generate_store_screenshots as gen
from generate_store_screenshots import render_store_screenshots

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except Exception:  # pragma: no cover
    _HAS_QT = False

GENERATOR_PATH = Path(__file__).resolve().parents[1] / "generate_store_screenshots.py"
STORE_DIR = GENERATOR_PATH.parent / "README" / "screenshots" / "store"
STORE_SHOTS = (
    "main-window.png",
    "search-and-versions.png",
    "boards-and-launch.png",
    "support-focus.png",
)


def _read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


# --- Tofu-Regression (Welle-1 U6) ------------------------------------------
# Root-Cause: QT_QPA_PLATFORM=offscreen + window.grab() rendert unter Windows
# keine echten Glyphen (.notdef-Kaestchen = Tofu). Fix: native Plattform +
# Qt.WA_DontShowOnScreen. Diese Tests sichern gegen einen Rueckfall.

def test_generator_source_uses_native_platform_not_offscreen():
    src = GENERATOR_PATH.read_text(encoding="utf-8")
    assert "WA_DontShowOnScreen" in src, "Fix (WA_DontShowOnScreen) fehlt"
    forces_offscreen = re.search(
        r"""environ\[["']QT_QPA_PLATFORM["']\]\s*=\s*["']offscreen["']""", src
    )
    assert not forces_offscreen, "Generator darf QT_QPA_PLATFORM nicht auf offscreen setzen"


def test_store_screenshots_present_and_nonempty():
    for name in STORE_SHOTS:
        path = STORE_DIR / name
        assert path.is_file(), f"Store-Screenshot {name} fehlt"
        assert path.stat().st_size > 10_000, f"Store-Screenshot {name} zu klein"


@pytest.mark.skipif(not _HAS_QT, reason="PySide6 fehlt")
def test_generator_guard_flags_tofu_under_offscreen():
    """Abnahmekriterium: unter offscreen bricht der Generator ab.

    Zwei getrennte Aussagen, die frueher vermengt waren:

    * ``_assert_font_rendering`` ist ein *Policy-Gate*: unter der
      offscreen-Plattform wirft es immer, unabhaengig von der gemessenen
      Schriftqualitaet. Das gilt auf jeder Plattform und wird hier gesichert.
    * ``font_rendering_works`` ist eine *Messung*. Dass offscreen Tofu liefert,
      ist eine Windows-Eigenart (siehe Kommentar oben); der Linux-Runner der
      GitHub Actions rendert offscreen via Fontconfig korrekt und meldet daher
      zu Recht True. Die Tofu-Erwartung gilt deshalb nur unter Windows -- dort
      bleibt sie als Welle-1-U6-Regressionsschutz scharf.
    """
    app = QApplication.instance()
    if app is None or QApplication.platformName() != "offscreen":
        pytest.skip("kein aktiver offscreen-Kontext")
    if sys.platform.startswith("win"):
        assert gen.font_rendering_works(app) is False, (
            "Guard erkennt offscreen-Tofu unter Windows nicht mehr"
        )
    with pytest.raises(RuntimeError):
        gen._assert_font_rendering(app)


def test_render_store_screenshots(tmp_path):
    """Integrationslauf: erzeugt echte Screenshots auf der nativen Plattform.

    Braucht echtes Font-Rendering. In der vollen Suite laeuft Qt offscreen
    (andere Testmodule setzen das) -> der Generator-Guard wuerde bewusst werfen
    und ein Aendern der globalen QApp-Plattform waere unerwuenscht. Dieser Lauf
    wird dann uebersprungen; er laeuft voll, wenn die Datei isoliert getestet
    wird (native Plattform) bzw. beim Deploy/CI.
    """
    if not _HAS_QT:
        pytest.skip("PySide6 fehlt")
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("offscreen-Umgebung - echtes Rendering nicht moeglich")
    if QApplication.instance() is not None and QApplication.platformName() == "offscreen":
        pytest.skip("offscreen-QApp aktiv - echtes Rendering nicht moeglich")

    output_dir = tmp_path / "store"
    try:
        summary = render_store_screenshots(output_dir)
    except RuntimeError as exc:
        pytest.skip(f"Font-Rendering nicht verfuegbar (Guard): {exc}")

    expected = {"main-window", "search-and-versions", "boards-and-launch", "support-focus"}
    assert set(summary["screenshots"]) == expected
    assert summary["qt_platform"] != "offscreen"

    for key, raw_path in summary["screenshots"].items():
        path = Path(raw_path)
        assert path.exists(), key
        assert path.suffix == ".png"
        assert path.stat().st_size > 10_000
        width, height = _read_png_size(path)
        assert width >= 1200
        assert height >= 700

    summary_path = output_dir / "summary.json"
    assert summary_path.exists()
