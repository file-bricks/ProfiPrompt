"""Regressionstests — ProfiPrompt Dashboard, Search & Export Resilience Bugsweep 2026-09-26.

Geprüfte Mängel:
  BUG-DB01 (HOCH): DashboardWidget._apply_filters() stürzt mit AttributeError ab, wenn
                   p.versions None-Einträge enthält. Zudem scheitert der Tag-Filter bei
                   ungetrimmten (z.B. ' AI ') oder numerischen Tags (z.B. 2026).
  BUG-DB02 (HOCH): DashboardWidget._apply_filters() Volltextsuche ignoriert das Feld 'purpose'
                   sowie sämtliche Versionen (v.title, v.text, v.tags). Dadurch sind Prompts
                   über Versionsinhalte und Zweck unauffindbar.
  BUG-DB03 (MITTEL): DashboardWidget.get_current_prompt() liefert None, wenn eine Version im
                     Baum ausgewählt ist, wodurch Menüaktionen (z.B. Prompt-Export) ins Leere laufen.
  BUG-DB04 (MITTEL): Export-Dateinamen enthalten ungefilterte verbotene Zeichen (z.B. :, /, <, >, *),
                     was unter Windows zu I/O-Fehlern führt.
  BUG-DB05 (HOCH): DashboardWidget._export_prompt_txt(), _export_version_txt() und _export_bundle_txt()
                   erstellen keine übergeordneten Verzeichnisse und besitzen kein Exception-Handling,
                   sodass Dateisystemfehler die Anwendung zum Absturz bringen.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

_SRC = Path(os.environ.get("PP_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, str(_SRC))

import models
from dashboard import DashboardWidget, sanitize_export_filename
from storage import Storage
from settings_manager import SettingsManager


@pytest.fixture
def test_env(tmp_path):
    storage = Storage(tmp_path / "data")
    settings = SettingsManager()
    return storage, settings


def test_db01_tag_filter_with_none_version_and_untrimmed_tags(qapp, test_env):
    """Tag-Filter darf bei versions=[None] nicht abstürzen und muss ungetrimmte/int Tags matchen."""
    storage, settings = test_env
    p1 = models.Prompt(
        id="p1",
        title="Prompt Alpha",
        purpose="Test",
        text="Content",
        tags=["  MachineLearning  ", 2026],
        versions=[None]
    )
    p2 = models.Prompt(
        id="p2",
        title="Prompt Beta",
        purpose="Test",
        text="Content",
        tags=["Web"],
        versions=[
            None,
            models.Version(id="v1", prompt_id="p2", version_number=1, title="V1", text="T", tags=["  DeepLearning  "])
        ]
    )
    storage.upsert_prompt(p1)
    storage.upsert_prompt(p2)

    dash = DashboardWidget(storage, settings)
    dash._prompts_cache = [p1, p2]  # Direkt Cache setzen mit None-Versionen

    # Wähle Tag 'MachineLearning'
    idx = dash.tag_combo.findData("MachineLearning")
    assert idx >= 0, f"Tag 'MachineLearning' nicht im Dropdown: {[dash.tag_combo.itemData(i) for i in range(dash.tag_combo.count())]}"
    dash.tag_combo.setCurrentIndex(idx)
    dash._apply_filters()

    # p1 muss gefunden werden, trotz versions=[None] und Leerzeichen im Quelltag
    matched = [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())]
    assert matched == ["Prompt Alpha"]

    # Wähle Tag 'DeepLearning' (aus Version von p2)
    idx2 = dash.tag_combo.findData("DeepLearning")
    assert idx2 >= 0
    dash.tag_combo.setCurrentIndex(idx2)
    dash._apply_filters()
    matched2 = [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())]
    assert matched2 == ["Prompt Beta"]


def test_db02_search_filter_purpose_and_versions_coverage(qapp, test_env):
    """Volltextsuche muss in purpose, Version-Titel, Version-Text und Version-Tags suchen."""
    storage, settings = test_env
    p = models.Prompt(
        id="p_search",
        title="Architektur",
        purpose="Backend-Refactoring für Microservices",
        text="Haupttext ohne Schlagwort",
        tags=["dev"],
        versions=[
            None,
            models.Version(
                id="v1",
                prompt_id="p_search",
                version_number=1,
                title="Sonderedition Kubernetes",
                text="Detaillierte Pod-Konfiguration mit Helm-Charts",
                tags=["cloud", "orchestration"]
            )
        ]
    )
    storage.upsert_prompt(p)

    dash = DashboardWidget(storage, settings)
    dash._prompts_cache = [p]

    # 1. Suche nach 'Microservices' (im purpose)
    dash.search_edit.setText("microservices")
    dash._apply_filters()
    assert [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())] == ["Architektur"]

    # 2. Suche nach 'Kubernetes' (im version.title)
    dash.search_edit.setText("kubernetes")
    dash._apply_filters()
    assert [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())] == ["Architektur"]

    # 3. Suche nach 'Helm-Charts' (im version.text)
    dash.search_edit.setText("helm-charts")
    dash._apply_filters()
    assert [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())] == ["Architektur"]

    # 4. Suche nach 'orchestration' (im version.tags)
    dash.search_edit.setText("orchestration")
    dash._apply_filters()
    assert [dash.tree.topLevelItem(i).text(0) for i in range(dash.tree.topLevelItemCount())] == ["Architektur"]


def test_db03_get_current_prompt_resolves_when_version_selected(qapp, test_env):
    """get_current_prompt() muss den übergeordneten Prompt zurückgeben, wenn ein Versions-Item aktiv ist."""
    storage, settings = test_env
    v = models.Version(id="v1", prompt_id="p_parent", version_number=1, title="V1", text="Text")
    p = models.Prompt(id="p_parent", title="Parent Prompt", purpose="", text="Text", versions=[v])
    storage.upsert_prompt(p)

    dash = DashboardWidget(storage, settings)
    dash.reload()

    # Selektiere Kind-Element (Version)
    parent_item = dash.tree.topLevelItem(0)
    assert parent_item.childCount() == 1
    child_item = parent_item.child(0)
    dash.tree.setCurrentItem(child_item)

    curr_p = dash.get_current_prompt()
    assert curr_p is not None
    assert curr_p.id == "p_parent"
    assert curr_p.title == "Parent Prompt"


def test_db04_sanitize_export_filename():
    """sanitize_export_filename bereinigt illegale Zeichen und nutzt sichere Fallbacks."""
    assert sanitize_export_filename("Mein: Prompt / Test <1> * ?") == "Mein_ Prompt _ Test _1"
    assert sanitize_export_filename("   ") == "prompt"
    assert sanitize_export_filename(None) == "prompt"
    assert sanitize_export_filename("", default="custom_fallback") == "custom_fallback"
    assert sanitize_export_filename("..//\\\\") == "prompt"
    assert sanitize_export_filename("Gültiger_Name-123") == "Gültiger_Name-123"


def test_db05_export_txt_creates_parent_dir_and_handles_errors(qapp, test_env, tmp_path):
    """TXT-Exporte müssen Elternverzeichnisse anlegen und Fehler fangen statt zu crashen."""
    storage, settings = test_env
    v = models.Version(id="v1", prompt_id="p1", version_number=1, title="Ver 1", text="Text V")
    p = models.Prompt(id="p1", title="Prompt 1", purpose="Purp", text="Text P", versions=[v])
    storage.upsert_prompt(p)

    dash = DashboardWidget(storage, settings)

    # 1. Export in tief verschachtelten noch nicht existierenden Pfad
    target_prompt = tmp_path / "deep" / "nested" / "prompt_export.txt"
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(target_prompt), "")), \
         patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        dash._export_prompt_txt(p)
        assert target_prompt.exists()
        assert "Text P" in target_prompt.read_text(encoding="utf-8")
        assert mock_info.called

    # 2. Version Export in tief verschachtelten Pfad
    target_ver = tmp_path / "deep2" / "nested2" / "version_export.txt"
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(target_ver), "")), \
         patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        dash._export_version_txt(v)
        assert target_ver.exists()
        assert "Text V" in target_ver.read_text(encoding="utf-8")
        assert mock_info.called

    # 3. Bundle Export in tief verschachtelten Pfad
    target_bundle = tmp_path / "deep3" / "nested3" / "bundle_export.txt"
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(target_bundle), "")), \
         patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        dash._export_bundle_txt(p)
        assert target_bundle.exists()
        content = target_bundle.read_text(encoding="utf-8")
        assert "Text P" in content
        assert "Text V" in content
        assert mock_info.called

    # 4. Exception-Handling bei Schreibfehlern (darf nicht ungefangen crashen)
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(target_prompt), "")), \
         patch("builtins.open", side_effect=PermissionError("Permission denied")), \
         patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit:
        dash._export_prompt_txt(p)
        assert mock_crit.called
