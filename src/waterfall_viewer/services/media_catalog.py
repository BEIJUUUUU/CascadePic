from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QImageReader

from waterfall_viewer.models.media_item import MediaItem

IMAGE_EXTENSIONS = frozenset(
    {
        ".bmp",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)


def is_supported_image(path: Path) -> bool:
    """Return whether *path* has an image extension supported by the MVP."""
    return path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS


def scan_image_siblings(path: Path) -> list[Path]:
    """Return readable images beside *path*, ordered case-insensitively by name."""
    try:
        return [item.path for item in scan_image_folder(path.parent)]
    except OSError:
        return []


def scan_image_folder(
    folder: Path, should_cancel: Callable[[], bool] | None = None
) -> list[MediaItem]:
    """Read lightweight metadata without decoding complete image pixels."""
    folder = folder.expanduser().resolve()
    paths = sorted(
        (item for item in folder.iterdir() if is_supported_image(item)),
        key=lambda item: (item.name.casefold(), item.name),
    )
    items: list[MediaItem] = []
    for path in paths:
        if should_cancel is not None and should_cancel():
            break
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        if not reader.canRead():
            continue
        size = reader.size()
        if not size.isValid():
            continue
        try:
            file_size = path.stat().st_size
        except OSError:
            continue
        items.append(
            MediaItem(
                path=path,
                width=size.width(),
                height=size.height(),
                file_size=file_size,
            )
        )
    return items
