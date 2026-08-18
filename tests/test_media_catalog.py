from pathlib import Path

from waterfall_viewer.services.media_catalog import is_supported_image, scan_image_siblings


def test_supported_image_extensions_are_case_insensitive(tmp_path: Path) -> None:
    image = tmp_path / "PHOTO.JpG"
    image.touch()

    assert is_supported_image(image)


def test_scan_image_siblings_filters_and_sorts(tmp_path: Path) -> None:
    for name in ["b.PNG", "A.jpg", "notes.txt", "c.webp"]:
        (tmp_path / name).touch()

    result = scan_image_siblings(tmp_path / "A.jpg")

    assert [item.name for item in result] == ["A.jpg", "b.PNG", "c.webp"]


def test_scan_image_siblings_handles_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "image.jpg"

    assert scan_image_siblings(missing) == []
