from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtGui import QImageReader


class ImageLoadSignals(QObject):
    loaded = Signal(str, object)
    failed = Signal(str, str)


class ImageLoadWorker(QRunnable):
    """Decode one full-size image off the UI thread."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.signals = ImageLoadSignals()

    @Slot()
    def run(self) -> None:
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self.signals.failed.emit(str(self.path), reader.errorString())
        else:
            self.signals.loaded.emit(str(self.path), image)
