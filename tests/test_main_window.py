from pathlib import Path

from PySide6.QtGui import QColor, QImage

from waterfall_viewer.ui.main_window import MainWindow


def _write_image(path: Path, color: str) -> None:
    image = QImage(64, 48, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    assert image.save(str(path))


def test_window_opens_image_and_discovers_siblings(qtbot, tmp_path: Path) -> None:
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    _write_image(first, "red")
    _write_image(second, "blue")

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.open_path(first)
    assert window.canvas.has_image()
    assert "1 / 2" in window.statusBar().currentMessage() or "a.png" in window.windowTitle()

    window.show_next()
    assert "b.png" in window.windowTitle()
