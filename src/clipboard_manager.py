from typing import Optional
from PySide6 import QtWidgets
from models import CopyMode, Prompt, Version
from settings_manager import SettingsManager

class ClipboardManager:
    def __init__(self, settings: SettingsManager):
        self.settings = settings

    def build_copy_text(
        self,
        prompt: Prompt,
        version: Optional[Version] = None
    ) -> str:
        mode         = self.settings.get_copy_mode()
        include_meta = self.settings.get_include_metadata()

        title  = version.title        if version else prompt.title
        text   = version.text         if version else prompt.text
        result = (version.result or "") if version else (prompt.last_result or "")

        parts = []
        if mode == CopyMode.TITLE:
            parts.append(title)
        elif mode == CopyMode.TEXT:
            parts.append(text)
        elif mode == CopyMode.RESULT:
            parts.append(result)
        elif mode == CopyMode.ALL:
            parts.append(f"{title}\n\n{text}")
            if result.strip():
                parts.append(f"--- Ergebnis ---\n{result}")

        if include_meta:
            tags = ", ".join((version.tags if version else prompt.tags) or [])
            parts.append(f"[Tags: {tags or '–'}]")

        return "\n".join(parts)

    def copy_to_clipboard(self, widget, text: str):
        QtWidgets.QApplication.clipboard().setText(text)
        QtWidgets.QToolTip.showText(
            widget.mapToGlobal(widget.rect().center()),
            "Kopiert 📋"
        )
