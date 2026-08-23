from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from threading import BoundedSemaphore, Event

from PySide6.QtCore import QObject, QRunnable, QSize, Signal, Slot
from PySide6.QtGui import QImage, QImageReader

from waterfall_viewer.models.media_item import MediaKind
from waterfall_viewer.services.thumbnail_cache import ThumbnailDiskCache
from waterfall_viewer.services.video_probe import extract_video_thumbnail

_VIDEO_DECODE_LIMIT = BoundedSemaphore(2)


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
        kind: MediaKind = MediaKind.IMAGE,
    ) -> None:
        super().__init__()
        self.path = path
        self.target_width = max(64, target_width)
        self.generation = generation
        self.disk_cache = disk_cache
        self.kind = kind
        self.signals = ThumbnailSignals()
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
        cached = self.disk_cache.load(self.path, self.target_width)
        if self._cancelled.is_set():
            self._emit(self.signals.cancelled, self.generation, key, self.target_width)
            return
        if cached is not None:
            self._emit(self.signals.loaded, self.generation, key, self.target_width, cached, True)
            return

        image = self._decode_video() if self.kind is MediaKind.VIDEO else self._decode_image()
        if self._cancelled.is_set():
            self._emit(self.signals.cancelled, self.generation, key, self.target_width)
            return
        if image is None or image.isNull():
            self._emit(self.signals.failed, self.generation, key, self.target_width)
            return
        self.disk_cache.store(self.path, self.target_width, image, self._cancelled.is_set)
        if self._cancelled.is_set():
            self._emit(self.signals.cancelled, self.generation, key, self.target_width)
            return
        self._emit(self.signals.loaded, self.generation, key, self.target_width, image, False)

    def _decode_video(self) -> QImage | None:
        with _VIDEO_DECODE_LIMIT:
            if self._cancelled.is_set():
                return None
            return extract_video_thumbnail(
                self.path,
                self.target_width,
                should_cancel=self._cancelled.is_set,
            )

    def _decode_image(self) -> QImage:
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
        return reader.read()
