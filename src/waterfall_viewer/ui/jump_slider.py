from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSlider


class JumpSlider(QSlider):
    """Slider that jumps directly to a clicked or dragged position."""

    jumped = Signal(int)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API name
        if event.button() is not Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setSliderDown(True)
        self.sliderPressed.emit()
        self._set_value_from_position(event)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API name
        if self.isSliderDown() and event.buttons() & Qt.MouseButton.LeftButton:
            self._set_value_from_position(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API name
        if event.button() is Qt.MouseButton.LeftButton and self.isSliderDown():
            self._set_value_from_position(event)
            self.setSliderDown(False)
            self.sliderReleased.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _set_value_from_position(self, event: QMouseEvent) -> None:
        if self.orientation() is Qt.Orientation.Horizontal:
            ratio = event.position().x() / max(1, self.width())
        else:
            ratio = 1 - event.position().y() / max(1, self.height())
        ratio = max(0.0, min(1.0, ratio))
        value = round(self.minimum() + ratio * (self.maximum() - self.minimum()))
        self.setValue(value)
        self.jumped.emit(value)
