# -*- coding: utf-8 -*-
"""Regressionstest fuer den reproduzierbaren Plattform-Smoke."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_run_platform_smoke_creates_expected_artifacts(tmp_path):
    from platform_smoke import run_platform_smoke

    summary = run_platform_smoke(tmp_path / "platform-smoke", headless=True)

    assert summary["stats"]["prompt_count"] == 1
    assert summary["stats"]["board_count"] == 1

    for artifact in summary["artifacts"].values():
        path = Path(artifact)
        assert path.exists()
        assert path.stat().st_size > 0

    exported = json.loads(
        Path(summary["artifacts"]["library_json"]).read_text(encoding="utf-8")
    )
    assert exported["schema_version"] == "profiprompt-library-v1"
    assert exported["prompts"][0]["title"] == "Grußprompt"
    txt_export = Path(summary["artifacts"]["prompt_txt"]).read_text(encoding="utf-8")
    assert "Begrüßung" in txt_export
    assert "überblick" in txt_export
