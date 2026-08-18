from pathlib import Path

from PySide6.QtGui import QAction, QColor, QImage

from waterfall_viewer.models.media_item import MediaItem
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
    qtbot.waitUntil(lambda: window.canvas.has_image(), timeout=3000)
    assert "a.png" in window.windowTitle()
    qtbot.waitUntil(lambda: len(window.waterfall.items) == 2, timeout=3000)

    window.show_next()
    qtbot.waitUntil(lambda: "b.png" in window.windowTitle(), timeout=3000)


def test_window_scans_folder_in_background(qtbot, tmp_path: Path) -> None:
    _write_image(tmp_path / "wide.png", "red")
    _write_image(tmp_path / "tall.png", "blue")
    window = MainWindow()
    qtbot.addWidget(window)

    window.open_folder(tmp_path)
    qtbot.waitUntil(lambda: len(window.waterfall.items) == 2, timeout=3000)

    assert len(window.waterfall.items) == 2
    assert "共 2 个媒体文件" in window._status_label.text()


def test_image_decode_does_not_block_ui_thread(qtbot, tmp_path: Path) -> None:
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    _write_image(first, "red")
    _write_image(second, "blue")
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.open_path(first)
    # The decode runs on a worker thread: the viewer must not be ready yet,
    # and the UI thread must keep processing events until it finishes.
    assert not window.canvas.has_image()
    assert "正在加载图片" in window._status_label.text()
    qtbot.waitUntil(lambda: window.canvas.has_image(), timeout=3000)
    qtbot.waitUntil(lambda: len(window.waterfall.items) == 2, timeout=3000)

    window.show_next()
    qtbot.waitUntil(lambda: "b.png" in window.windowTitle(), timeout=3000)


def test_thumbnail_slider_updates_waterfall_width(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window._thumbnail_slider.setValue(320)

    assert window.waterfall.thumbnail_width == 320


def test_sort_combo_reorders_media_by_modified_time(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    old = MediaItem(Path("old.jpg"), 100, 100, modified_ns=10)
    new = MediaItem(Path("new.jpg"), 100, 100, modified_ns=30)
    window._folder_items = [old, new]
    window._images = [old.path, new.path]

    window._sort_combo.setCurrentIndex(1)

    assert window._images == [new.path, old.path]


def test_viewer_close_button_replaces_waterfall_toolbar_action(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    action_texts = [action.text() for action in window.findChildren(QAction)]

    assert "瀑布流" not in action_texts
    window._set_current_page(window.canvas)
    assert not window._viewer_close_button.isHidden()

    window.show_waterfall()
    assert window._viewer_close_button.isHidden()
