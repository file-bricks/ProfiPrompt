from pathlib import Path
from PySide6 import QtCore
from models import CopyMode
import theme as theme_mod

class SettingsManager(QtCore.QObject):
    copyModeChanged        = QtCore.Signal(CopyMode)
    includeMetadataChanged = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.qs = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "PromptManager", "PromptManager"
        )

    def get_data_path(self) -> Path:
        base = self.qs.value("paths/data", "", type=str)
        if not base:
            default = Path.home() / ".prompt_manager"
            self.qs.setValue("paths/data", str(default))
            self.qs.sync()
            base = str(default)
        path = Path(base)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_copy_mode(self) -> CopyMode:
        raw = self.qs.value("copy/mode", CopyMode.TEXT.value, type=str)
        try:
            return CopyMode(raw)
        except ValueError:
            return CopyMode.TEXT

    def set_copy_mode(self, mode: CopyMode):
        if not isinstance(mode, CopyMode):
            raise TypeError(f"expected CopyMode, got {type(mode)}")
        old = self.get_copy_mode()
        if old != mode:
            self.qs.setValue("copy/mode", mode.value)
            self.qs.sync()
            self.copyModeChanged.emit(mode)

    def get_language(self) -> str:
        """Gespeicherte UI-Sprache ('de'/'en'), Default 'de'."""
        lang = self.qs.value("ui/language", "de", type=str)
        return lang if lang in ("de", "en") else "de"

    def set_language(self, lang: str):
        """Persistiert die UI-Sprache in den QSettings."""
        if lang in ("de", "en"):
            self.qs.setValue("ui/language", lang)
            self.qs.sync()

    # --- Theme (Welle-1 U2: Hell/Dunkel) ---
    def get_theme(self) -> str:
        """Gespeichertes UI-Theme ('dark'/'light'), Default 'dark'."""
        t = self.qs.value("ui/theme", "dark", type=str)
        return t if t in ("dark", "light") else "dark"

    def set_theme(self, theme: str):
        """Persistiert das UI-Theme in den QSettings."""
        if theme in ("dark", "light"):
            self.qs.setValue("ui/theme", theme)
            self.qs.sync()

    # --- Kachelfarben (Welle-1 U3: konfigurierbar) ---
    def _default_tile_color(self, kind: str) -> str:
        return (theme_mod.DEFAULT_TILE_MAIN if kind == "main"
                else theme_mod.DEFAULT_TILE_VERSION)

    def get_tile_color(self, kind: str) -> str:
        """Basisfarbe einer Kachelart ('main'/'version'); Default = bisherige Farbe."""
        default = self._default_tile_color(kind)
        val = self.qs.value(f"tiles/color_{kind}", default, type=str)
        return theme_mod.normalize_hex(val or default, default)

    def set_tile_color(self, kind: str, hexcolor: str):
        """Persistiert die Basisfarbe einer Kachelart."""
        if kind in ("main", "version"):
            self.qs.setValue(f"tiles/color_{kind}",
                             theme_mod.normalize_hex(hexcolor, self._default_tile_color(kind)))
            self.qs.sync()

    def reset_tile_colors(self):
        """Setzt beide Kachelfarben auf die Standardwerte zurueck."""
        self.qs.remove("tiles/color_main")
        self.qs.remove("tiles/color_version")
        self.qs.sync()

    def get_include_metadata(self) -> bool:
        return self.qs.value("copy/include_metadata", False, type=bool)

    def set_include_metadata(self, flag: bool):
        if not isinstance(flag, bool):
            raise TypeError(f"expected bool, got {type(flag)}")
        old = self.get_include_metadata()
        if old != flag:
            self.qs.setValue("copy/include_metadata", flag)
            self.qs.sync()
            self.includeMetadataChanged.emit(flag)
