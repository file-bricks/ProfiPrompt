"""Zentrale Laufzeit-Uebersetzung fuer alle ProfiPrompt-Widgets.

Bisher nutzte nur die Menueleiste den Translator; Tabellenkoepfe, Board-Leiste,
Kontextmenues, Dialoge und Meldungen blieben nach einem Sprachwechsel deutsch.
Dieses Modul stellt EINEN gemeinsamen Translator bereit:

  * ``tr(key, **kwargs)``   -- uebersetzt einen (deutschen) Quell-Key.
  * ``set_language(lang)``  -- schaltet die Sprache um und meldet das ueber
                               ``bus.languageChanged``; Widgets bauen ihre Texte
                               dann in ``retranslate_ui()`` live neu auf.

Laufzeit-Lookups registrieren KEINE fehlenden Keys in locales/translations.json
(``auto_register=False``), damit die gebuendelte Datei nie mit leeren Eintraegen
verunreinigt wird.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def app_base_dir() -> Path:
    """Basisverzeichnis fuer gebuendelte Daten (locales/translator).

    Frozen (PyInstaller): sys._MEIPASS; sonst der Repo-Root (Parent von src/).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return Path(__file__).resolve().parent.parent


_BASE_DIR = app_base_dir()
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

try:
    from translator import TranslationSystem
except Exception:  # pragma: no cover - Uebersetzung ist optional
    TranslationSystem = None

_translator = None


def make_translator(lang: str, *, auto_register: bool = False):
    """Erzeugt ein TranslationSystem mit robuster locales-Aufloesung (oder None)."""
    if TranslationSystem is None:
        return None
    try:
        return TranslationSystem(lang, app_dir=_BASE_DIR, auto_register=auto_register)
    except Exception:
        return None


def get_translator():
    """Gemeinsamer Translator (lazy, Default-Sprache 'de')."""
    global _translator
    if _translator is None:
        _translator = make_translator("de")
    return _translator


def init(lang: str):
    """Setzt die Startsprache ohne Signal (vor dem Aufbau der Widgets)."""
    tr_obj = get_translator()
    if tr_obj is not None:
        tr_obj.set_language(lang)
    return tr_obj


def get_language() -> str:
    tr_obj = get_translator()
    return tr_obj.get_language() if tr_obj is not None else "de"


def set_language(lang: str) -> bool:
    """Schaltet die Sprache um und benachrichtigt alle Widgets (live)."""
    tr_obj = get_translator()
    if tr_obj is None or not tr_obj.set_language(lang):
        return False
    from event_bus import bus
    bus.languageChanged.emit(lang)
    return True


def tr(key: str, **kwargs) -> str:
    """Uebersetzt key in die aktive Sprache (Fallback: key, ggf. formatiert)."""
    tr_obj = get_translator()
    if tr_obj is not None:
        return tr_obj.t(key, **kwargs)
    if kwargs:
        try:
            return key.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return key
    return key


def translate_with(translator: Optional[object], key: str, **kwargs) -> str:
    """Hilfsfunktion fuer Komponenten mit optional injiziertem Translator."""
    if translator is not None:
        return translator.t(key, **kwargs)
    return tr(key, **kwargs)
