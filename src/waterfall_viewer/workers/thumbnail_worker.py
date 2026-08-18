from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Signal, Slot
from PySide6.QtGui import QImageReader


class ThumbnailSignals(QObject):
    loaded = Signal(int, str, int, object)
    failed = Signal(int, str, int)


class ThumbnailWorker(QRunnable):
    """Decode one generation-bound, size-bounded thumbnail off the GUI thread."""

    def __init__(self, path: Path, target_width: int, generation: int) -> None:
        super().__init__()
        self.path = path
        self.target_width = max(64, target_width)
        self.generation = generation
        self.signals = ThumbnailSignals()

    @Slot()
    def run(self) -> None:
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and size.width() > self.target_width:
            target_height = max(1, round(size.height() * self.target_width / size.width()))
            reader.setScaledSize(QSize(self.target_width, target_height))
        image = reader.read()
        key = str(self.path)
        if image.isNull():
            self.signals.failed.emit(self.generation, key, self.target_width)
            return
        self.signals.loaded.emit(self.generation, key, self.target_width, image)
