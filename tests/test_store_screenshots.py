import os
import struct
import sys
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from generate_store_screenshots import render_store_screenshots


def _read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_render_store_screenshots(tmp_path):
    output_dir = tmp_path / "store"
    summary = render_store_screenshots(output_dir)

    expected = {
        "main-window",
        "search-and-versions",
        "boards-and-launch",
        "support-focus",
    }
    assert set(summary["screenshots"]) == expected

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
    assert "offscreen" in summary["qt_platform"] or summary["qt_platform"] == ""
