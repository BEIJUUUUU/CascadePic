from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QSize, Signal, Slot
from PySide6.QtGui import QImageReader

from waterfall_viewer.services.thumbnail_cache import ThumbnailDiskCache


class ThumbnailSignals(QObject):
    loaded = Signal(int, str, int, object, bool)
    failed = Signal(int, str, int)
    cancelled = Signal(int, str, int)


class ThumbnailWorker(QRunnable):
    """Load or decode one cancellable, generation-bound thumbnail."""

    def __init__(
        self,
        path: Path,
        target_width: int,
        generation: int,
        disk_cache: ThumbnailDiskCache,
    ) -> None:
        super().__init__()
        self.path = path
        self.target_width = max(64, target_width)
        self.generation = generation
        self.disk_cache = disk_cache
        self.signals = ThumbnailSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        key = str(self.path)
        cached = self.disk_cache.load(self.path, self.target_width)
        if self._cancelled.is_set():
            self.signals.cancelled.emit(self.generation, key, self.target_width)
            return
        if cached is not None:
            self.signals.loaded.emit(self.generation, key, self.target_width, cached, True)
            return

        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid():
            scale = min(1.0, self.target_width / size.width(), 4096 / size.height())
            if scale < 1.0:
                reader.setScaledSize(
                    QSize(
                        max(1, round(size.width() * scale)),
                        max(1, round(size.height() * scale)),
                    )
                )
        image = reader.read()
        if self._cancelled.is_set():
            self.signals.cancelled.emit(self.generation, key, self.target_width)
            return
        if image.isNull():
            self.signals.failed.emit(self.generation, key, self.target_width)
            return
        self.disk_cache.store(self.path, self.target_width, image, self._cancelled.is_set)
        if self._cancelled.is_set():
            self.signals.cancelled.emit(self.generation, key, self.target_width)
            return
        self.signals.loaded.emit(self.generation, key, self.target_width, image, False)
