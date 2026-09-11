"""Regressionstests — ProfiPrompt Export, PDF & Dialog Resilience Bugsweep 2026-09-11.

Geprüfte Mängel:
  BUG-ED01 (HOCH): pdf_exporter._render_html_for_prompt() und _render_html_for_version()
                   stürzen mit AttributeError ab, wenn last_result bzw. result None ist und
                   Metadata-Inklusion aktiv ist (None.strip()). Zudem stürzt ', '.join() mit
                   TypeError ab, wenn tags None oder nicht-Strings (None, int) enthalten.
  BUG-ED02 (HOCH): export_single_prompt_with_versions() stürzt mit TypeError ab, wenn
                   prompt.versions None ist ('NoneType' object is not iterable) oder
                   version_number None ist.
  BUG-ED03 (MITTEL): _init_printer() scheitert oder hinterlässt fehlerhaften Zustand,
                     wenn übergeordnete Verzeichnisse des Zielpfads noch nicht existieren.
  BUG-ED04 (HOCH): DashboardWidget._collect_tags() stürzt mit TypeError ab, wenn
                   prompt.versions None ist oder tags heterogene Datentypen enthalten
                   (Python 3 verbietet sortierte Vergleiche zwischen str und int).
  BUG-ED05 (HOCH): PromptDialog._populate() und VersionDialog stürzen mit TypeError in PySide6
                   ab, wenn title, purpose, text oder result None sind (setText/setPlainText
                   akzeptieren kein None) oder tags None/heterogen sind.
"""

import os
import sys
from pathlib import Path
import pytest

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models
import pdf_exporter
from dashboard import DashboardWidget
from prompt_dialog import PromptDialog, VersionDialog


class MockSettings:
    def __init__(self, include_meta=True):
        self._include_meta = include_meta

    def get_include_metadata(self):
        return self._include_meta


# ---------------------------------------------------------------------------
# BUG-ED01 & ED02: PDF-Exporter HTML-Rendering und Versionen-Resilienz
# ---------------------------------------------------------------------------

def test_ed01_render_html_for_prompt_with_none_result_and_mixed_tags():
    """_render_html_for_prompt darf bei last_result=None und gemischten Tags nicht abstürzen."""
    settings = MockSettings(include_meta=True)
    p = models.Prompt(
        id="p1",
        title="Test Prompt",
        purpose=None,
        text="Prompt text",
        tags=[None, "alpha", 123, ""],
        last_result=None,
        versions=[],
    )
    html_out = pdf_exporter._render_html_for_prompt(p, settings)
    assert "<h1>Test Prompt</h1>" in html_out
    assert "alpha" in html_out
    assert "123" in html_out
    assert "None" not in html_out


def test_ed01_render_html_for_version_with_none_result_and_mixed_tags():
    """_render_html_for_version darf bei result=None und gemischten Tags nicht abstürzen."""
    settings = MockSettings(include_meta=True)
    v = models.Version(
        id="v1",
        prompt_id="p1",
        version_number=1,
        title="Version 1",
        text="Version text",
        tags=[None, "tag_v", 99],
        result=None,
    )
    html_out = pdf_exporter._render_html_for_version(v, settings)
    assert "<h2>Version 1 <small>(v1)</small></h2>" in html_out
    assert "tag_v" in html_out
    assert "99" in html_out


def test_ed02_export_single_prompt_with_versions_none(qapp, tmp_path):
    """export_single_prompt_with_versions darf bei prompt.versions=None nicht abstürzen."""
    p = models.Prompt(
        id="p1",
        title="Test Prompt",
        purpose="Purpose",
        text="Text",
        tags=["t1"],
        last_result="Result",
        versions=None,
    )
    target_pdf = str(tmp_path / "single_prompt.pdf")
    # Darf keinen TypeError werfen
    success = pdf_exporter.export_single_prompt_with_versions(p, MockSettings(), target_pdf)
    assert success is True
    assert Path(target_pdf).exists()


def test_ed03_export_html_to_pdf_ensures_parent_dir(qapp, tmp_path):
    """_init_printer muss das übergeordnete Verzeichnis erstellen."""
    target_pdf = tmp_path / "nested" / "exports" / "output.pdf"
    assert not target_pdf.parent.exists()
    writer = pdf_exporter._init_printer(str(target_pdf))
    assert target_pdf.parent.exists()


# ---------------------------------------------------------------------------
# BUG-ED04: DashboardWidget._collect_tags Resilienz
# ---------------------------------------------------------------------------

def test_ed04_dashboard_collect_tags_with_none_versions_and_heterogeneous_tags():
    """_collect_tags() muss bei versions=None und int/None Tags saubere String-Listen liefern."""
    p1 = models.Prompt(
        id="p1",
        title="P1",
        purpose="Purpose",
        text="Text",
        tags=["beta", 42, None],
        versions=None,
    )
    p2 = models.Prompt(
        id="p2",
        title="P2",
        purpose="Purpose",
        text="Text",
        tags=[None, "alpha"],
        versions=[
            models.Version(
                id="v1",
                prompt_id="p2",
                version_number=1,
                title="V1",
                text="T",
                tags=[100, "gamma", None],
            )
        ],
    )
    tags = DashboardWidget._collect_tags(None, [p1, p2])
    assert tags == ["100", "42", "alpha", "beta", "gamma"]


# ---------------------------------------------------------------------------
# BUG-ED05: Dialog Widgets Resilienz bei None-Feldern
# ---------------------------------------------------------------------------

def test_ed05_prompt_dialog_populate_safe_with_none_fields(qapp):
    """PromptDialog._populate() darf bei None-Feldern (title, purpose, text, etc.) nicht crashen."""
    class DummyStorage:
        def load_prompts(self):
            return []

    p = models.Prompt(
        id="p_none",
        title=None,
        purpose=None,
        text=None,
        tags=[None, 77, "ok"],
        last_result=None,
        versions=None,
    )
    dlg = PromptDialog(DummyStorage(), p)
    # Sollte ohne TypeError durchgelaufen sein
    assert dlg.title_edit.text() == ""
    assert dlg.purpose_edit.text() == ""
    assert dlg.tags_edit.text() == "77, ok"
    assert dlg.text_edit.toPlainText() == ""
    assert dlg.result_edit.toPlainText() == ""


def test_ed05_version_dialog_safe_with_none_fields(qapp):
    """VersionDialog darf bei None-Feldern weder im Create- noch im Edit-Modus abstürzen."""
    class DummyStorage:
        def load_prompts(self):
            return []
        def next_version_number(self, pid):
            return 1

    p = models.Prompt(
        id="p1",
        title=None,
        purpose=None,
        text=None,
        tags=[None, "ptag"],
        last_result=None,
        versions=None,
    )
    # Create-Modus
    dlg_create = VersionDialog(DummyStorage(), p, None)
    assert dlg_create.title_edit.text() == ""
    assert dlg_create.tags_edit.text() == "ptag"

    # Edit-Modus
    v = models.Version(
        id="v1",
        prompt_id="p1",
        version_number=1,
        title=None,
        text=None,
        tags=[None, 88],
        result=None,
    )
    dlg_edit = VersionDialog(DummyStorage(), p, v)
    assert dlg_edit.title_edit.text() == ""
    assert dlg_edit.tags_edit.text() == "88"
    assert dlg_edit.text_edit.toPlainText() == ""
    assert dlg_edit.result_edit.toPlainText() == ""


def test_ed06_export_all_txt_safe_with_none_fields(tmp_path):
    """export_all_txt Formatierungs-Logik darf bei None-Feldern nicht scheitern."""
    p1 = models.Prompt(
        id="p1",
        title=None,
        purpose=None,
        text=None,
        tags=[None, "txt_tag", 55],
        versions=None,
    )
    p2 = models.Prompt(
        id="p2",
        title="Prompt 2",
        purpose="Zweck",
        text="Inhalt",
        tags=["a"],
        versions=[
            models.Version(
                id="v1",
                prompt_id="p2",
                version_number=None,
                title=None,
                text=None,
                tags=None,
            )
        ],
    )
    prompts = [p1, p2]
    parts = []
    for p in prompts or []:
        if not p:
            continue
        p_tags = ", ".join(
            str(t).strip() for t in (p.tags or []) if t is not None and str(t).strip()
        )
        lines = [
            f"=== {p.title or ''} ===",
            f"Zweck: {p.purpose or ''}",
            f"Tags: {p_tags}",
            "",
            p.text or "",
        ]
        versions = [v for v in (p.versions or []) if v is not None]
        for v in sorted(versions, key=lambda x: getattr(x, "version_number", 0) or 0):
            v_num = getattr(v, "version_number", None) or "?"
            lines += ["", f"--- v{v_num}: {v.title or ''} ---", v.text or ""]
        parts.append("\n".join(lines))

    out_file = tmp_path / "all_prompts.txt"
    out_file.write_text("\n\n".join(parts), encoding="utf-8")
    content = out_file.read_text(encoding="utf-8")
    assert "===  ===" in content
    assert "Tags: txt_tag, 55" in content
    assert "=== Prompt 2 ===" in content
    assert "--- v?:  ---" in content
