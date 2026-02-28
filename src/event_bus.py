from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    promptsChanged  = Signal()
    boardsChanged   = Signal()
    copyRequested   = Signal(str, str, object)  # kind, id, parent
    dragRequested   = Signal(str, object)       # kind, (prompt_id, version_id)
    dragItem        = Signal(object)

bus = EventBus()
