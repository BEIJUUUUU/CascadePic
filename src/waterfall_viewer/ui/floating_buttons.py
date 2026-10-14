"""Floating circular overlay buttons for image/video viewer navigation and exit.

Built as custom-painted QAbstractButton widgets with WA_TranslucentBackground
so Qt's stylesheet engine does not leave black rectangular bounding-box
artifacts over dark or colored image canvases.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton


class FloatingNavButton(QAbstractButton):
    """Floating circular previous/next arrow button with smooth drop shadow."""

    def __init__(self, is_next: bool, parent=None) -> None:
        super().__init__(parent)
        self._is_next = is_next
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setToolTip("下一张  →" if is_next else "上一张  ←")

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)

        # Soft drop shadow beneath circle
        shadow_rect = rect.adjusted(0, 1.5, 0, 1.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 38))
        painter.drawEllipse(shadow_rect)

        # Main circular disc
        if self.isDown():
            bg = QColor(225, 230, 238, 255)
        elif self.underMouse():
            bg = QColor(255, 255, 255, 255)
        else:
            bg = QColor(248, 249, 251, 235)

        painter.setBrush(bg)
        painter.setPen(QPen(QColor(0, 0, 0, 28), 1))
        painter.drawEllipse(rect)

        # Chevron arrow
        pen = QPen(
            QColor(20, 22, 26),
            2.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = rect.center().x()
        cy = rect.center().y()
        if self._is_next:
            painter.drawLine(QPointF(cx - 3, cy - 7), QPointF(cx + 4, cy))
            painter.drawLine(QPointF(cx + 4, cy), QPointF(cx - 3, cy + 7))
        else:
            painter.drawLine(QPointF(cx + 3, cy - 7), QPointF(cx - 4, cy))
            painter.drawLine(QPointF(cx - 4, cy), QPointF(cx + 3, cy + 7))


class FloatingCloseButton(QAbstractButton):
    """Floating circular close/exit button with smooth drop shadow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setToolTip("返回瀑布流 (Esc)")

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)

        # Soft drop shadow beneath circle
        shadow_rect = rect.adjusted(0, 1.2, 0, 1.2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 36))
        painter.drawEllipse(shadow_rect)

        # Main circular disc
        if self.isDown():
            bg = QColor(198, 42, 47, 255)
            cross_color = QColor(255, 255, 255)
            border_color = QColor(198, 42, 47)
        elif self.underMouse():
            bg = QColor(229, 72, 77, 255)
            cross_color = QColor(255, 255, 255)
            border_color = QColor(229, 72, 77)
        else:
            bg = QColor(248, 249, 251, 235)
            cross_color = QColor(20, 22, 26)
            border_color = QColor(0, 0, 0, 28)

        painter.setBrush(bg)
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(rect)

        # Cross mark (X)
        pen = QPen(
            cross_color,
            2.0,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = rect.center().x()
        cy = rect.center().y()
        offset = 5.0
        painter.drawLine(QPointF(cx - offset, cy - offset), QPointF(cx + offset, cy + offset))
        painter.drawLine(QPointF(cx + offset, cy - offset), QPointF(cx - offset, cy + offset))
