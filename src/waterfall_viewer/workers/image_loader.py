from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtGui import QImageReader

from waterfall_viewer.workers.safe_signals import safe_emit


class ImageLoadSignals(QObject):
    loaded = Signal(int, str, object)
    failed = Signal(int, str, str)
    cancelled = Signal(int, str)


class ImageLoadWorker(QRunnable):
    """Decode one cancellable, generation-bound full-size image."""

    def __init__(self, path: Path, generation: int) -> None:
        super().__init__()
        self.path = path
        self.generation = generation
        self.signals = ImageLoadSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        key = str(self.path)
        if self._cancelled.is_set():
            safe_emit(self.signals.cancelled, self.generation, key)
            return
        try:
            reader = QImageReader(key)
            reader.setAutoTransform(True)
            image = reader.read()
            error = reader.errorString()
        except Exception as error:  # noqa: BLE001 - must always report back
            safe_emit(self.signals.failed, self.generation, key, str(error))
            return
        if self._cancelled.is_set():
            safe_emit(self.signals.cancelled, self.generation, key)
        elif image.isNull():
            safe_emit(self.signals.failed, self.generation, key, error)
        else:
            safe_emit(self.signals.loaded, self.generation, key, image)
