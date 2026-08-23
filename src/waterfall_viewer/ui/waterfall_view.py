from __future__ import annotations

from bisect import bisect_left
from collections import OrderedDict
from math import sqrt

from PySide6.QtCore import QPointF, QRectF, Qt, QThreadPool, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import QAbstractScrollArea

from waterfall_viewer.models.media_item import MediaItem
from waterfall_viewer.services.thumbnail_cache import ThumbnailDiskCache
from waterfall_viewer.utils.formatting import format_duration
from waterfall_viewer.workers.thumbnail_worker import ThumbnailWorker

ThumbnailKey = tuple[str, int]
WorkerKey = tuple[int, str, int]


class WaterfallView(QAbstractScrollArea):
    """Indexed custom-painted waterfall view with bounded asynchronous decoding."""

    activated = Signal(object)
    _MAX_PENDING_THUMBNAILS = 64

    def __init__(
        self,
        disk_cache: ThumbnailDiskCache | None = None,
        memory_cache_bytes: int = 256 * 1024 * 1024,
    ) -> None:
        super().__init__()
        self._items: list[MediaItem] = []
        self._item_keys: set[str] = set()
        self._rects: list[QRectF] = []
        self._columns: list[list[int]] = []
        self._column_bottoms: list[list[float]] = []
        self._column_target = 220
        self._column_width = 220.0
        self._gap = 12
        self._content_height = 0
        self._memory_cache_limit = max(1024 * 1024, memory_cache_bytes)
        self._memory_cache_bytes = 0
        self._generation = 0
        self._disk_cache = disk_cache or ThumbnailDiskCache()
        self._disk_cache_hits = 0
        self._thumbnails: OrderedDict[ThumbnailKey, QPixmap] = OrderedDict()
        self._thumbnail_sizes: dict[ThumbnailKey, int] = {}
        self._failed: set[ThumbnailKey] = set()
        self._workers: dict[WorkerKey, ThumbnailWorker] = {}
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(4)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self._hover_index = -1
        self._active_index = -1

    @property
    def items(self) -> tuple[MediaItem, ...]:
        return tuple(self._items)

    @property
    def content_height(self) -> int:
        return self._content_height

    @property
    def thumbnail_width(self) -> int:
        return self._column_target

    @property
    def thumbnail_count(self) -> int:
        return len(self._thumbnails)

    @property
    def pending_thumbnail_count(self) -> int:
        return len(self._workers)

    @property
    def memory_cache_bytes(self) -> int:
        return self._memory_cache_bytes

    @property
    def disk_cache_hits(self) -> int:
        return self._disk_cache_hits

    def disk_cache_size(self) -> int:
        return self._disk_cache.total_size()

    def clear_thumbnail_cache(self) -> int:
        self._reset_thumbnail_requests()
        removed = self._disk_cache.clear()
        self.viewport().update()
        return removed

    def set_items(self, items: list[MediaItem]) -> None:
        self._reset_thumbnail_requests()
        self._items = list(items)
        self._item_keys = {str(item.path) for item in items}
        self.verticalScrollBar().setValue(0)
        self._relayout()
        self.viewport().update()

    def clear(self) -> None:
        self.set_items([])

    def set_thumbnail_width(self, width: int) -> None:
        width = max(120, min(480, width))
        if width == self._column_target:
            return
        self._column_target = width
        self._reset_thumbnail_requests()
        self._relayout()
        self.viewport().update()

    def item_rect(self, index: int) -> QRectF:
        return QRectF(self._rects[index])

    def _reset_thumbnail_requests(self) -> None:
        self._generation += 1
        for worker_key, worker in list(self._workers.items()):
            worker.cancel()
            if self._thread_pool.tryTake(worker):
                self._workers.pop(worker_key, None)
        self._thumbnails.clear()
        self._thumbnail_sizes.clear()
        self._memory_cache_bytes = 0
        self._failed.clear()

    def _relayout(self) -> None:
        available = max(1, self.viewport().width())
        column_count = max(1, (available + self._gap) // (self._column_target + self._gap))
        self._column_width = (available - self._gap * (column_count - 1)) / column_count
        heights = [float(self._gap)] * column_count
        columns: list[list[int]] = [[] for _ in range(column_count)]
        rects: list[QRectF] = []

        for index, item in enumerate(self._items):
            column = min(range(column_count), key=heights.__getitem__)
            x = column * (self._column_width + self._gap)
            image_height = max(1.0, self._column_width / item.aspect_ratio)
            rect = QRectF(x, heights[column], self._column_width, image_height)
            rects.append(rect)
            columns[column].append(index)
            heights[column] = rect.bottom() + self._gap

        self._rects = rects
        self._columns = columns
        self._column_bottoms = [
            [self._rects[index].bottom() for index in column] for column in columns
        ]
        self._content_height = round(max(heights, default=0.0))
        maximum = max(0, self._content_height - self.viewport().height())
        self.verticalScrollBar().setRange(0, maximum)
        self.verticalScrollBar().setPageStep(self.viewport().height())
        self.verticalScrollBar().setSingleStep(80)

    def _indices_intersecting(self, area: QRectF) -> list[int]:
        result: list[int] = []
        for indices, bottoms in zip(self._columns, self._column_bottoms, strict=True):
            position = bisect_left(bottoms, area.top())
            for index in indices[position:]:
                rect = self._rects[index]
                if rect.top() > area.bottom():
                    break
                if rect.intersects(area):
                    result.append(index)
        return result

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt API name
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(event.rect(), QColor("#faf9f8"))

        scroll_y = self.verticalScrollBar().value()
        visible = QRectF(0, scroll_y, self.viewport().width(), self.viewport().height())
        preload = visible.adjusted(0, -self.viewport().height(), 0, self.viewport().height())
        visible_indices = self._indices_intersecting(visible)
        preload_indices = self._indices_intersecting(preload)

        for index in visible_indices:
            item = self._items[index]
            draw_rect = self._rects[index].translated(0, -scroll_y)
            self._paint_item(painter, item, draw_rect, index)

        visible_set = set(visible_indices)
        prioritized = visible_indices + [
            index for index in preload_indices if index not in visible_set
        ]
        desired_paths = {str(self._items[index].path) for index in prioritized}
        self._discard_obsolete_queued_workers(desired_paths)
        for index in prioritized:
            if len(self._workers) >= self._MAX_PENDING_THUMBNAILS:
                break
            self._request_thumbnail(self._items[index])

    def _paint_item(self, painter: QPainter, item: MediaItem, rect: QRectF, index: int) -> None:
        cache_key = (str(item.path), self._target_decode_width())
        pixmap = self._thumbnails.get(cache_key)

        is_hovered = index == self._hover_index
        active = index == self._active_index
        radius = 9.0
        card = rect.adjusted(0.5, 0.5, -0.5, -0.5)

        def _rounded(where: QRectF, r: float) -> QPainterPath:
            path = QPainterPath()
            path.addRoundedRect(where, r, r)
            return path

        # Soft drop shadow (two alpha-gradient layers, offset downward).
        for offset, alpha in ((2, 26), (1, 14)):
            painter.fillPath(
                _rounded(card.adjusted(0, offset, 0, offset), radius),
                QColor(0, 0, 0, alpha),
            )

        # Card body.
        card_path = _rounded(card, radius)
        if pixmap is None:
            painter.fillPath(card_path, QColor("#f0efed"))
            painter.setPen(QColor("#8a8886"))
            painter.drawText(
                card, Qt.AlignmentFlag.AlignCenter, item.path.suffix.upper().lstrip(".")
            )
            painter.setPen(QPen(QColor(0, 0, 0, 14), 1))
            painter.drawPath(card_path)
        else:
            self._thumbnails.move_to_end(cache_key)
            painter.save()
            painter.setClipPath(card_path)
            painter.drawPixmap(card, pixmap, QRectF(pixmap.rect()))
            painter.restore()
            painter.setPen(QPen(QColor(0, 0, 0, 18), 1))
            painter.drawPath(card_path)

        # Fluent accent outline on hover/active.
        if is_hovered or active:
            accent = QColor("#0067c0")
            accent.setAlpha(220 if active else 150)
            painter.setPen(QPen(accent, 2))
            painter.drawPath(_rounded(rect.adjusted(-1, -1, 1, 1), radius + 1))

        if item.is_video:
            label = format_duration(item.duration_ms) if item.duration_ms else "VIDEO"
            badge = QRectF(card.right() - 68, card.bottom() - 28, 60, 20)
            painter.fillPath(_rounded(badge, 6), QColor(0, 0, 0, 170))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API name
        content_point = event.position() + QPointF(0, self.verticalScrollBar().value())
        point_area = QRectF(content_point.x(), content_point.y(), 1, 1)
        previous = self._hover_index
        self._hover_index = -1
        for index in self._indices_intersecting(point_area):
            if self._rects[index].contains(content_point):
                self._hover_index = index
                break
        if self._hover_index != previous:
            self.viewport().update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self._hover_index != -1:
            self._hover_index = -1
            self.viewport().update()
        super().leaveEvent(event)

    def _target_decode_width(self) -> int:
        pixel_ratio = max(1.0, self.devicePixelRatioF())
        return min(1440, max(64, round(self._column_width * pixel_ratio)))

    def _request_thumbnail(self, item: MediaItem) -> None:
        path_key = str(item.path)
        target_width = self._target_decode_width()
        cache_key = (path_key, target_width)
        worker_key = (self._generation, path_key, target_width)
        if (
            cache_key in self._thumbnails
            or cache_key in self._failed
            or worker_key in self._workers
        ):
            return
        worker = ThumbnailWorker(
            item.path,
            target_width,
            self._generation,
            self._disk_cache,
            item.kind,
        )
        worker.signals.loaded.connect(self._thumbnail_loaded)
        worker.signals.failed.connect(self._thumbnail_failed)
        worker.signals.cancelled.connect(self._thumbnail_cancelled)
        self._workers[worker_key] = worker
        self._thread_pool.start(worker)

    def _discard_obsolete_queued_workers(self, desired_paths: set[str]) -> None:
        for worker_key, worker in list(self._workers.items()):
            generation, path_key, _ = worker_key
            if generation == self._generation and path_key in desired_paths:
                continue
            worker.cancel()
            if self._thread_pool.tryTake(worker):
                self._workers.pop(worker_key, None)

    def _thumbnail_loaded(
        self,
        generation: int,
        path_key: str,
        target_width: int,
        image: QImage,
        disk_cache_hit: bool,
    ) -> None:
        worker_key = (generation, path_key, target_width)
        self._workers.pop(worker_key, None)
        if generation != self._generation or path_key not in self._item_keys:
            return
        cache_key = (path_key, target_width)
        pixmap = QPixmap.fromImage(image)
        pixmap_bytes = max(1, pixmap.width() * pixmap.height() * 4)
        if pixmap_bytes > self._memory_cache_limit:
            scale = sqrt(self._memory_cache_limit / pixmap_bytes)
            pixmap = pixmap.scaled(
                max(1, round(pixmap.width() * scale)),
                max(1, round(pixmap.height() * scale)),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap_bytes = max(1, pixmap.width() * pixmap.height() * 4)
        previous_size = self._thumbnail_sizes.get(cache_key, 0)
        self._thumbnails[cache_key] = pixmap
        self._thumbnail_sizes[cache_key] = pixmap_bytes
        self._memory_cache_bytes += pixmap_bytes - previous_size
        self._thumbnails.move_to_end(cache_key)
        if disk_cache_hit:
            self._disk_cache_hits += 1
        while self._memory_cache_bytes > self._memory_cache_limit and self._thumbnails:
            evicted_key, _ = self._thumbnails.popitem(last=False)
            self._memory_cache_bytes -= self._thumbnail_sizes.pop(evicted_key, 0)
        self.viewport().update()

    def _thumbnail_failed(self, generation: int, path_key: str, target_width: int) -> None:
        worker_key = (generation, path_key, target_width)
        self._workers.pop(worker_key, None)
        if generation != self._generation or path_key not in self._item_keys:
            return
        self._failed.add((path_key, target_width))
        self.viewport().update()

    def _thumbnail_cancelled(self, generation: int, path_key: str, target_width: int) -> None:
        self._workers.pop((generation, path_key, target_width), None)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API name
        content_point = event.position() + QPointF(0, self.verticalScrollBar().value())
        point_area = QRectF(content_point.x(), content_point.y(), 1, 1)
        for index in self._indices_intersecting(point_area):
            if self._rects[index].contains(content_point):
                self._active_index = index
                self.viewport().update()
                self.activated.emit(self._items[index].path)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._reset_thumbnail_requests()
        self._relayout()
