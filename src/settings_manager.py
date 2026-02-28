from pathlib import Path
from PySide6 import QtCore
from models import CopyMode

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
