from pathlib import Path

from PySide6.QtGui import QColor, QImage

from waterfall_viewer.models.media_item import MediaItem
from waterfall_viewer.ui.waterfall_view import WaterfallView


def _write_image(path: Path, width: int, height: int) -> None:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#3b82f6"))
    assert image.save(str(path))


def test_waterfall_layout_uses_image_aspect_ratios(qtbot, tmp_path: Path) -> None:
    wide = tmp_path / "wide.png"
    tall = tmp_path / "tall.png"
    _write_image(wide, 400, 200)
    _write_image(tall, 200, 400)
    view = WaterfallView()
    qtbot.addWidget(view)
    view.resize(500, 400)
    view.set_items(
        [
            MediaItem(wide, 400, 200),
            MediaItem(tall, 200, 400),
        ]
    )

    wide_rect = view.item_rect(0)
    tall_rect = view.item_rect(1)

    assert wide_rect.width() / wide_rect.height() == 2.0
    assert tall_rect.width() / tall_rect.height() == 0.5
    assert view.content_height > 0


def test_waterfall_thumbnail_width_is_bounded(qtbot) -> None:
    view = WaterfallView()
    qtbot.addWidget(view)
    view.resize(900, 500)
    items = [MediaItem(Path(f"{index}.jpg"), 100, 100) for index in range(8)]
    view.set_thumbnail_width(20)
    view.set_items(items)

    assert view.item_rect(0).width() >= 100


def test_visible_thumbnail_loads_asynchronously(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "thumbnail.png"
    _write_image(path, 640, 360)
    view = WaterfallView()
    qtbot.addWidget(view)
    view.resize(600, 400)
    view.set_items([MediaItem(path, 640, 360)])
    view.show()

    qtbot.waitUntil(lambda: view.thumbnail_count == 1, timeout=3000)

    assert view.thumbnail_count == 1


def test_stale_thumbnail_result_is_ignored(qtbot, tmp_path: Path) -> None:
    old_path = tmp_path / "old.png"
    new_path = tmp_path / "new.png"
    _write_image(old_path, 100, 100)
    _write_image(new_path, 100, 100)
    view = WaterfallView()
    qtbot.addWidget(view)
    view.set_items([MediaItem(old_path, 100, 100)])
    stale_generation = view._generation
    target_width = view._target_decode_width()

    view.set_items([MediaItem(new_path, 100, 100)])
    stale_image = QImage(100, 100, QImage.Format.Format_RGB32)
    view._thumbnail_loaded(stale_generation, str(old_path), target_width, stale_image)

    assert view.thumbnail_count == 0
