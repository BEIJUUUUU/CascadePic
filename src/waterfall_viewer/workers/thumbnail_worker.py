from __future__ import annotations

from pathlib import Path
from threading import BoundedSemaphore, Event

from PySide6.QtCore import QObject, QRunnable, QSize, Signal, Slot
from PySide6.QtGui import QImage, QImageReader

from waterfall_viewer.models.media_item import MediaKind
from waterfall_viewer.services.thumbnail_cache import ThumbnailDiskCache
from waterfall_viewer.services.video_probe import extract_video_thumbnail
from waterfall_viewer.workers.safe_signals import safe_emit

# Video thumbnail extraction shells out to ffmpeg; cap how many run at once.
_VIDEO_DECODE_LIMIT = BoundedSemaphore(2)

# Longest edge cap for decoded thumbnails, to bound memory on huge sources.
_MAX_THUMBNAIL_EDGE = 4096


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
        duration_ms: int = 0,
    ) -> None:
        super().__init__()
        self.path = path
        self.target_width = max(64, target_width)
        self.generation = generation
        self.disk_cache = disk_cache
        self.kind = kind
        self.duration_ms = max(0, duration_ms)
        self.signals = ThumbnailSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        key = str(self.path)
        width = self.target_width
        try:
            cached = self.disk_cache.load(self.path, width)
            if self._cancelled.is_set():
                safe_emit(self.signals.cancelled, self.generation, key, width)
                return
            if cached is not None:
                safe_emit(self.signals.loaded, self.generation, key, width, cached, True)
                return

            image = self._decode_video() if self.kind is MediaKind.VIDEO else self._decode_image()
            if self._cancelled.is_set():
                safe_emit(self.signals.cancelled, self.generation, key, width)
                return
            if image is None or image.isNull():
                safe_emit(self.signals.failed, self.generation, key, width)
                return
            self.disk_cache.store(self.path, width, image, self._cancelled.is_set)
            if self._cancelled.is_set():
                safe_emit(self.signals.cancelled, self.generation, key, width)
                return
            safe_emit(self.signals.loaded, self.generation, key, width, image, False)
        except Exception:  # noqa: BLE001 - must always report back
            # Without this the entry lingers in the view's worker map forever,
            # eventually wedging the pending-thumbnail budget.
            safe_emit(self.signals.failed, self.generation, key, width)

    def _decode_video(self) -> QImage | None:
        with _VIDEO_DECODE_LIMIT:
            if self._cancelled.is_set():
                return None
            return extract_video_thumbnail(
                self.path,
                self.target_width,
                duration_ms=self.duration_ms,
                should_cancel=self._cancelled.is_set,
            )

    def _decode_image(self) -> QImage:
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        size = reader.size()
        # QSize(0, 100).isValid() is True, so also require positive dimensions
        # before dividing by them.
        if size.isValid() and size.width() > 0 and size.height() > 0:
            scale = min(
                1.0,
                self.target_width / size.width(),
                _MAX_THUMBNAIL_EDGE / size.height(),
            )
            if scale < 1.0:
                reader.setScaledSize(
                    QSize(
                        max(1, round(size.width() * scale)),
                        max(1, round(size.height() * scale)),
                    )
                )
        return reader.read()
