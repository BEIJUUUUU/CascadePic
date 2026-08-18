from pathlib import Path

from PySide6.QtGui import QColor, QImage

from waterfall_viewer.models.media_item import MediaKind
from waterfall_viewer.services import media_catalog
from waterfall_viewer.services.media_catalog import (
    is_supported_image,
    scan_image_folder,
    scan_image_siblings,
    scan_media_folder,
)
from waterfall_viewer.services.video_probe import VideoMetadata


def test_supported_image_extensions_are_case_insensitive(tmp_path: Path) -> None:
    image = tmp_path / "PHOTO.JpG"
    image.touch()

    assert is_supported_image(image)


def test_scan_image_siblings_filters_and_sorts(tmp_path: Path) -> None:
    for name in ["b.PNG", "A.jpg", "c.webp"]:
        image = QImage(20, 10, QImage.Format.Format_RGB32)
        image.fill(QColor("blue"))
        assert image.save(str(tmp_path / name))
    (tmp_path / "notes.txt").touch()

    result = scan_image_siblings(tmp_path / "A.jpg")

    assert [item.name for item in result] == ["A.jpg", "b.PNG", "c.webp"]


def test_scan_image_siblings_handles_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "image.jpg"

    assert scan_image_siblings(missing) == []


def test_scan_image_folder_reads_dimensions_and_file_size(tmp_path: Path) -> None:
    path = tmp_path / "sample.png"
    image = QImage(320, 180, QImage.Format.Format_RGB32)
    image.fill(QColor("green"))
    assert image.save(str(path))

    items = scan_image_folder(tmp_path)

    assert len(items) == 1
    assert items[0].path == path
    assert (items[0].width, items[0].height) == (320, 180)
    assert items[0].file_size > 0
    assert items[0].created_ns > 0
    assert items[0].modified_ns > 0


def test_scan_image_folder_skips_corrupt_image(tmp_path: Path) -> None:
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    assert scan_image_folder(tmp_path) == []


def test_scan_image_folder_honors_cancellation(tmp_path: Path) -> None:
    path = tmp_path / "sample.png"
    image = QImage(20, 10, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    assert image.save(str(path))

    assert scan_image_folder(tmp_path, lambda: True) == []


def test_scan_media_folder_mixes_images_and_videos(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "a.png"
    image = QImage(320, 180, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    assert image.save(str(image_path))
    video_path = tmp_path / "b.mp4"
    video_path.write_bytes(b"video")
    monkeypatch.setattr(media_catalog, "find_ffprobe", lambda: "ffprobe")
    monkeypatch.setattr(
        media_catalog,
        "probe_video",
        lambda path, executable, should_cancel: VideoMetadata(1280, 720, 5_000),
    )

    items = scan_media_folder(tmp_path)

    assert [item.kind for item in items] == [MediaKind.IMAGE, MediaKind.VIDEO]
    assert items[1].duration_ms == 5_000
