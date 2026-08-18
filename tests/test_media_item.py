from pathlib import Path

from waterfall_viewer.models.media_item import MediaItem, MediaKind


def test_media_item_aspect_ratio() -> None:
    item = MediaItem(Path("photo.jpg"), width=400, height=200)

    assert item.aspect_ratio == 2.0


def test_media_item_invalid_dimensions_fall_back_to_square() -> None:
    item = MediaItem(Path("broken.jpg"), width=0, height=0)

    assert item.aspect_ratio == 1.0


def test_video_media_item_reports_kind_and_duration() -> None:
    item = MediaItem(
        Path("clip.mp4"),
        width=1920,
        height=1080,
        kind=MediaKind.VIDEO,
        duration_ms=65_000,
    )

    assert item.is_video
    assert item.duration_ms == 65_000
