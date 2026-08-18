from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ImageCanvas(QGraphicsView):
    """A graphics view that supports fit, actual size, zoom and drag navigation."""

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self.setScene(self._scene)

        self._fit_mode = True
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setBackgroundBrush(Qt.GlobalColor.black)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

    def has_image(self) -> bool:
        return not self._pixmap_item.pixmap().isNull()

    def set_image(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_window()

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._scene.setSceneRect(0, 0, 0, 0)
        self.resetTransform()

    def fit_to_window(self) -> None:
        if not self.has_image():
            return
        self._fit_mode = True
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def actual_size(self) -> None:
        if not self.has_image():
            return
        self._fit_mode = False
        self.resetTransform()
        self.centerOn(self._pixmap_item)

    def zoom(self, factor: float) -> None:
        if not self.has_image():
            return
        current = self.transform().m11()
        target = current * factor
        if 0.02 <= target <= 64.0:
            self._fit_mode = False
            self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API name
        if not self.has_image():
            super().wheelEvent(event)
            return
        self.zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        if self._fit_mode:
            self.fit_to_window()
