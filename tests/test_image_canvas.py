from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QSignalSpy

from waterfall_viewer.ui.image_canvas import ImageCanvas


def test_canvas_accepts_and_clears_image(qtbot) -> None:
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    image = QImage(320, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))

    canvas.set_image(image)
    assert canvas.has_image()

    canvas.clear_image()
    assert not canvas.has_image()


def test_canvas_zoom_changes_transform(qtbot) -> None:
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    canvas.resize(640, 480)
    image = QImage(320, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("blue"))
    canvas.set_image(image)
    canvas.actual_size()

    canvas.zoom(1.2)

    assert canvas.transform().m11() > 1.0


def _wheel_event(buttons: Qt.MouseButton = Qt.MouseButton.NoButton) -> QWheelEvent:
    return QWheelEvent(
        QPointF(100, 100),
        QPointF(100, 100),
        QPoint(),
        QPoint(0, 120),
        buttons,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


def test_plain_wheel_requests_previous_media(qtbot) -> None:
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    image = QImage(320, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("green"))
    canvas.set_image(image)
    spy = QSignalSpy(canvas.navigate_requested)

    canvas.wheelEvent(_wheel_event())

    assert spy.count() == 1
    assert spy.at(0)[0] == -1


def test_right_button_wheel_zooms_without_navigation(qtbot) -> None:
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    image = QImage(320, 200, QImage.Format.Format_RGB32)
    image.fill(QColor("green"))
    canvas.set_image(image)
    canvas.actual_size()
    spy = QSignalSpy(canvas.navigate_requested)

    canvas.wheelEvent(_wheel_event(Qt.MouseButton.RightButton))

    assert canvas.transform().m11() > 1.0
    assert spy.count() == 0
