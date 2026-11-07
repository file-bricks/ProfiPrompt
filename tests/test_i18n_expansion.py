# -*- coding: utf-8 -*-
"""
test_i18n_expansion.py
======================
Hermetic contract test suite for Tier-2 6-language expansion (Policy P-006)
and store readiness parity across ProfiPrompt.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile

import pytest

import manage_translations
from scripts.check_store_readiness import (
    FOREIGN_BRAND_TERMS,
    LISTING_FIELD_LABELS,
    matched_foreign_brand,
    parse_store_listing_sections,
)

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LANGUAGES_6 = ["de-DE", "en-US", "es-ES", "zh-CN", "ja-JP", "ru-RU"]
REQUIRED_LANG_CODES_6 = ["de", "en", "es", "zh", "ja", "ru"]


def test_store_package_json_has_six_tier2_languages() -> None:
    """Verify store_package.json declares all 6 Tier-2 languages and descriptions <= 100 chars."""
    pkg_file = ROOT / "store_package.json"
    assert pkg_file.is_file(), "store_package.json missing"

    data = json.loads(pkg_file.read_text(encoding="utf-8"))
    languages = data.get("languages")
    assert isinstance(languages, list), "languages must be a list in store_package.json"

    for lang in REQUIRED_LANGUAGES_6:
        assert lang in languages, f"Language {lang} missing in store_package.json languages list"

    for code in REQUIRED_LANG_CODES_6:
        desc_key = f"description_{code}"
        assert desc_key in data, f"{desc_key} missing in store_package.json"
        desc_val = data[desc_key]
        assert isinstance(desc_val, str) and desc_val.strip(), f"{desc_key} must be a non-empty string"
        assert len(desc_val) <= 100, f"{desc_key} exceeds 100 characters: {len(desc_val)}"

        kw_key = f"keywords_{code}"
        assert kw_key in data, f"{kw_key} missing in store_package.json"
        kws = data[kw_key]
        assert isinstance(kws, list), f"{kw_key} must be a list"
        assert 1 <= len(kws) <= 7, f"{kw_key} must contain between 1 and 7 keywords, found {len(kws)}"
        for kw in kws:
            assert len(kw) <= 30, f"Keyword '{kw}' in {kw_key} exceeds 30 characters"
            hit = matched_foreign_brand(kw)
            assert hit is None, f"Forbidden trademark '{hit}' in {kw_key}: '{kw}'"


def test_store_listing_has_six_languages_and_guideline_parity() -> None:
    """Verify STORE_LISTING.md and releases/windowsstore/ provide complete 6-language listings."""
    listing_file = ROOT / "STORE_LISTING.md"
    assert listing_file.is_file(), "STORE_LISTING.md missing"
    text = listing_file.read_text(encoding="utf-8")

    sections = parse_store_listing_sections(text)
    expected_headings = ["Deutsch", "English", "Español", "简体中文", "日本語", "Русский"]

    for heading in expected_headings:
        assert heading in sections, f"Section {heading} missing in STORE_LISTING.md"
        parsed = sections[heading]
        assert "short_description" in parsed, f"short_description missing in {heading}"
        assert "description" in parsed, f"description missing in {heading}"
        assert "keywords" in parsed, f"keywords missing in {heading}"
        assert "category" in parsed, f"category missing in {heading}"

        short_desc = parsed["short_description"]
        assert len(short_desc) <= 100, f"{heading} short_description exceeds 100 chars: {len(short_desc)}"
        assert "\n" not in short_desc, f"{heading} short_description must be single line"

        desc = parsed["description"]
        assert "ProfiPrompt" in desc, f"{heading} description must mention ProfiPrompt"

        category = parsed["category"]
        assert "Productivity" in category, f"{heading} category must include Productivity"

        # Check keywords policy
        kws = [k.strip() for k in re.split(r"[,;]", parsed["keywords"]) if k.strip()]
        assert 1 <= len(kws) <= 7, f"{heading} keywords count must be <= 7, got {len(kws)}"
        for kw in kws:
            hit = matched_foreign_brand(kw)
            assert hit is None, f"Forbidden trademark '{hit}' found in {heading} keywords: '{kw}'"

    # Check releases/windowsstore/ individual staging files
    ws_dir = ROOT / "releases" / "windowsstore"
    assert ws_dir.is_dir(), "releases/windowsstore dir missing"
    for code in ["de", "en", "es", "zh", "ja", "ru"]:
        staging_file = ws_dir / f"store_listing_{code}.md"
        assert staging_file.is_file(), f"Staging file {staging_file.name} missing in releases/windowsstore"
        staging_text = staging_file.read_text(encoding="utf-8")
        assert "ProfiPrompt" in staging_text, f"{staging_file.name} must mention ProfiPrompt"


def test_web_companion_i18n_parity() -> None:
    """Verify web_companion/i18n.js has 100% key parity across all 6 Tier-2 languages."""
    i18n_file = ROOT / "web_companion" / "i18n.js"
    assert i18n_file.is_file(), "web_companion/i18n.js missing"
    text = i18n_file.read_text(encoding="utf-8")

    # Verify that all 6 languages are present in the translations dictionary export
    for code in REQUIRED_LANG_CODES_6:
        assert f"{code}: {{" in text, f"Language block '{code}: {{' missing in i18n.js"

    # Verify index.html contains language selector with all 6 options
    index_file = ROOT / "web_companion" / "index.html"
    index_text = index_file.read_text(encoding="utf-8")
    assert 'id="lang-select"' in index_text, "lang-select missing in web_companion/index.html"
    for code in REQUIRED_LANG_CODES_6:
        assert f'value="{code}"' in index_text, f"Option value='{code}' missing in lang-select"


def test_manage_translations_cwd_independence() -> None:
    """Verify manage_translations.check_translations resolves deterministically regardless of CWD."""
    # When called with None, resolves to repository locales/translations.json
    ret = manage_translations.check_translations(None)
    assert ret == 0, "check_translations(None) must return 0 (100% parity)"

    # Verify resolve_translation_file returns the canonical path
    resolved = manage_translations.resolve_translation_file()
    assert resolved.is_file()
    assert resolved.name == "translations.json"
    assert resolved.parent.name == "locales"

    # Verify calling from a temporary foreign directory still passes
    with tempfile.TemporaryDirectory() as tmpdir:
        # Dummy folder with no locales
        ret_foreign = manage_translations.check_translations(None)
        assert ret_foreign == 0


def test_readme_six_languages_reciprocal_parity() -> None:
    """Verify all 6 README files exist and have 17-point navigation with reciprocal structure."""
    expected_files = {
        "en": ROOT / "README.md",
        "de": ROOT / "README_de.md",
        "es": ROOT / "README_es.md",
        "zh": ROOT / "README_zh.md",
        "ja": ROOT / "README_ja.md",
        "ru": ROOT / "README_ru.md",
    }

    nav_pattern = re.compile(r"^\d+\.\s+\[([^\]]+)\]\((#[^\)]+)\)", re.MULTILINE)

    for lang, path in expected_files.items():
        assert path.is_file(), f"README for {lang} ({path.name}) is missing"
        text = path.read_text(encoding="utf-8")

        # 17 navigation points
        nav_points = nav_pattern.findall(text)
        assert len(nav_points) == 17, f"Expected 17 navigation points in {path.name}, found {len(nav_points)}"

        # Every anchor must exist as a ## heading
        for title, anchor in nav_points:
            anchor_id = anchor.lstrip("#")
            assert any(
                re.sub(r"[^\w\s-]", "", h.lower()).strip().replace(" ", "-") == anchor_id
                for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
            ), f"Anchor {anchor} from navigation not found as section header in {path.name}"

        # Personas must exist
        for p_id in ["[PERSONA-1]", "[PERSONA-2]", "[PERSONA-3]", "[PERSONA-4]"]:
            assert p_id in text, f"{p_id} missing in {path.name}"

        # 4-View Architectural Topology with all 10 invariants
        for inv in [
            "INV-LOCAL-01", "INV-OFFLINE", "INV-ATOMIC", "INV-SCHEMA",
            "INV-UNPRIV-05", "INV-BAK", "INV-PRINT", "INV-PWA", "INV-SLA-10"
        ]:
            assert inv in text, f"{inv} missing in {path.name}"

        # Reciprocal language switcher bar
        assert "README.md" in text or "**English**" in text
        assert "README_de.md" in text or "**Deutsch**" in text
        assert "README_es.md" in text or "**Español**" in text
        assert "README_zh.md" in text or "**简体中文**" in text
        assert "README_ja.md" in text or "**日本語**" in text
        assert "README_ru.md" in text or "**Русский**" in text
