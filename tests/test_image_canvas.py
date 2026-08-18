from PySide6.QtGui import QColor, QImage

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
