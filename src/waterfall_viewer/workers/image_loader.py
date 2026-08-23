from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtGui import QImageReader


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

    @staticmethod
    def _emit(signal, *args) -> None:
        with suppress(RuntimeError):
            signal.emit(*args)

    @Slot()
    def run(self) -> None:
        key = str(self.path)
        if self._cancelled.is_set():
            self._emit(self.signals.cancelled, self.generation, key)
            return
        reader = QImageReader(key)
        reader.setAutoTransform(True)
        image = reader.read()
        if self._cancelled.is_set():
            self.signals.cancelled.emit(self.generation, key)
        elif image.isNull():
            self._emit(self.signals.failed, self.generation, key, reader.errorString())
        else:
            self._emit(self.signals.loaded, self.generation, key, image)
