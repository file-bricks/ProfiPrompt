from typing import Optional
from PySide6 import QtWidgets
from models import CopyMode, Prompt, Version
from settings_manager import SettingsManager

class ClipboardManager:
    def __init__(self, settings: SettingsManager):
        self.settings = settings

    def build_copy_text(
        self,
        prompt: Optional[Prompt],
        version: Optional[Version] = None
    ) -> str:
        if prompt is None and version is None:
            return ""

        mode         = self.settings.get_copy_mode()
        include_meta = self.settings.get_include_metadata()

        title = (version.title or "") if version else ((prompt.title or "") if prompt else "")
        text = (version.text or "") if version else ((prompt.text or "") if prompt else "")
        result = (version.result or "") if version else ((prompt.last_result or "") if prompt else "")
        raw_tags = (version.tags or []) if version else ((prompt.tags or []) if prompt else [])

        parts = []
        if mode == CopyMode.TITLE:
            parts.append(title)
        elif mode == CopyMode.TEXT:
            parts.append(text)
        elif mode == CopyMode.RESULT:
            parts.append(result)
        elif mode == CopyMode.ALL:
            if title and text:
                parts.append(f"{title}\n\n{text}")
            elif title:
                parts.append(title)
            elif text:
                parts.append(text)
            else:
                parts.append("")
            if result.strip():
                parts.append(f"--- Ergebnis ---\n{result}")

        if include_meta:
            clean_tags = [str(t) for t in (raw_tags or []) if t is not None and str(t).strip()]
            tags = ", ".join(clean_tags)
            parts.append(f"[Tags: {tags or '–'}]")

        return "\n".join(parts)

    def copy_to_clipboard(self, widget, text: str):
        # Bugsweep 19 BUG-05: clipboard() kann None sein (keine QApplication-Instanz, z.B. Test/
        # Headless) -> .setText crashte. BUG-06: widget kann None sein (nicht-visueller Aufruf).
        cb = QtWidgets.QApplication.clipboard()
        if cb is not None:
            cb.setText(text)
        if widget is not None:
            QtWidgets.QToolTip.showText(
                widget.mapToGlobal(widget.rect().center()),
                "Kopiert 📋"
            )
