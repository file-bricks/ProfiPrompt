"""
TranslationSystem - Multi-Language Support fuer ProfiPrompt
===========================================================
Version: 2.0.0 (Policy P-006 Tier-2 6-Sprachen-Standard)
Quelle: Policy P-006 / CONVENTIONS.md

Unterstützte Sprachen:
- de: Deutsch (Standard)
- en: English
- es: Español
- zh: 简体中文
- ja: 日本語
- ru: Русский

Deterministische 4-Stufen-Fallback-Kette:
  target_lang -> 'en' -> 'de' -> key

Verwendung:
-----------
from translator import get_translator, t, TranslationSystem

translator = get_translator('de')
label.setText(t('Datei'))
translator.set_language('es')
label.setText(t('Datei'))
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class TranslationSystem:
    """Multi-Language Support System v2.0 with deterministic fallbacks."""

    SUPPORTED_LANGUAGES = ("de", "en", "es", "zh", "ja", "ru")
    FALLBACK_LANGUAGES = ("en", "de")
    LANGUAGE_NAMES = {
        "de": "Deutsch",
        "en": "English",
        "es": "Español",
        "zh": "简体中文",
        "ja": "日本語",
        "ru": "Русский",
    }
    LANGUAGE_DISPLAY_NAMES = {
        "de": "Deutsch (de)",
        "en": "English (en)",
        "es": "Español (es)",
        "zh": "简体中文 (zh)",
        "ja": "日本語 (ja)",
        "ru": "Русский (ru)",
    }

    def __init__(self, default_lang: str = "de", app_dir: Optional[Path] = None):
        """
        Initialisiert Translation-System.

        Args:
            default_lang: Standard-Sprache ('de', 'en', 'es', 'zh', 'ja', 'ru')
            app_dir: Verzeichnis der Anwendung (default: Verzeichnis von translator.py)
        """
        self.current_lang = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "de"

        if app_dir is None:
            app_dir = Path(__file__).resolve().parent
        self.app_dir = Path(app_dir)

        self.translations_file = self.app_dir / "locales" / "translations.json"

        self.string_patterns = [
            re.compile(r'setText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setWindowTitle\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QLabel\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'QPushButton\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addAction\s*\([^,]*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setToolTip\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'setPlaceholderText\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'text\s*=\s*"([^"]+)"'),
        ]

        self.german_hints = [
            "datei", "bearbeiten", "ansicht", "hilfe", "oeffnen", "speichern",
            "schliessen", "einstellungen", "abbrechen", "ok", "ja", "nein",
            "start", "stop", "pause", "fortsetzen", "laden", "aktualisieren",
            "filter", "fehler", "export", "import", "optionen", "anzeigen",
            "prompt", "version", "board", "zwischenablage", "sprache", "anleitung",
            "ueber", "zuruecksetzen", "loeschen", "kopieren",
        ]

        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        if self.translations_file.exists():
            try:
                with open(self.translations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.translations = data
                else:
                    self.translations = {}
            except Exception:
                self.translations = {}
        else:
            self.translations = {}

    def _save_translations(self) -> None:
        self.translations_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.translations_file.with_suffix(self.translations_file.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.translations, f, indent=2, ensure_ascii=False)
        tmp.replace(self.translations_file)

    def _new_translation_entry(self, de: str, en: str) -> Dict[str, str]:
        return {
            "de": de,
            "en": en,
            "es": "",
            "zh": "",
            "ja": "",
            "ru": "",
        }

    def t(self, key: str, **kwargs) -> str:
        """
        Uebersetzt einen Key in die aktuelle Sprache mit 4-stufiger Fallback-Hierarchie:
        target -> en -> de -> key.

        Args:
            key: Translation-Key
            **kwargs: Optionale Platzhalter fuer .format()

        Returns:
            Uebersetzter und formatierter Text
        """
        entry = self.translations.get(key)
        if isinstance(entry, dict):
            fallback_chain = (self.current_lang, *self.FALLBACK_LANGUAGES)
            for language in fallback_chain:
                value = entry.get(language)
                if isinstance(value, str) and value:
                    if kwargs:
                        try:
                            return value.format(**kwargs)
                        except (KeyError, IndexError, ValueError):
                            return value
                    return value

        if self._is_german(key) and key not in self.translations:
            self.translations[key] = self._new_translation_entry(key, "")
            self._save_translations()

        if kwargs:
            try:
                return key.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return key
        return key

    def set_language(self, lang: str) -> bool:
        """Setzt die aktive Sprache, falls sie unterstützt wird."""
        if lang in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang
            return True
        return False

    def get_language(self) -> str:
        return self.current_lang

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Return the supported language codes."""
        return list(cls.SUPPORTED_LANGUAGES)

    @classmethod
    def get_language_names(cls) -> Dict[str, str]:
        """Return a mapping of language codes to native language names."""
        return dict(cls.LANGUAGE_NAMES)

    @classmethod
    def get_language_display_names(cls) -> Dict[str, str]:
        """Return a mapping of language codes to display strings."""
        return dict(cls.LANGUAGE_DISPLAY_NAMES)

    def add_translation(self, key: str, de: str, en: str, **other_langs):
        entry = self._new_translation_entry(de, en)
        for lang, val in other_langs.items():
            if lang in self.SUPPORTED_LANGUAGES:
                entry[lang] = val
        self.translations[key] = entry
        self._save_translations()

    def scan_and_update(self, project_dir: Optional[Path] = None) -> Dict:
        """Scannt Projekt-Dateien nach deutschen Strings und aktualisiert translations.json."""
        if project_dir is None:
            project_dir = self.app_dir

        found_strings = self._find_german_strings(Path(project_dir))

        added = []
        for string in sorted(found_strings):
            if string not in self.translations:
                self.translations[string] = self._new_translation_entry(string, "")
                added.append(string)

        if added:
            self._save_translations()

        missing = {
            lang: [k for k, v in self.translations.items() if not v.get(lang)]
            for lang in self.SUPPORTED_LANGUAGES
        }

        return {
            "total": len(self.translations),
            "added": added,
            "missing": missing,
        }

    def _find_german_strings(self, directory: Path) -> Set[str]:
        german_strings = set()
        skip_dirs = {"build", "dist", "venv", ".venv", "__pycache__", "releases", "web_companion"}

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(".py"):
                    try:
                        with open(Path(root) / file, "r", encoding="utf-8") as f:
                            content = f.read()
                        for pattern in self.string_patterns:
                            for match in pattern.findall(content):
                                if self._is_german(match):
                                    german_strings.add(match.strip())
                    except Exception:
                        pass
        return german_strings

    def _is_german(self, text: str) -> bool:
        if any(ch in text for ch in "äöüÄÖÜß"):
            return True
        text_lower = text.lower()
        return any(hint in text_lower for hint in self.german_hints)


_default_translator: Optional[TranslationSystem] = None


def get_translator(lang: str = "de", app_dir: Optional[Path] = None) -> TranslationSystem:
    global _default_translator
    if _default_translator is None or (app_dir is not None and _default_translator.app_dir != Path(app_dir)):
        _default_translator = TranslationSystem(lang, app_dir)
    elif lang != _default_translator.current_lang:
        _default_translator.set_language(lang)
    return _default_translator


def t(key: str, **kwargs) -> str:
    return get_translator().t(key, **kwargs)
