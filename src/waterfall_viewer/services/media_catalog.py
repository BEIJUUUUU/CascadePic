from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QImageReader

from waterfall_viewer.models.media_item import MediaItem, MediaKind
from waterfall_viewer.services.video_probe import find_ffprobe, probe_video

IMAGE_EXTENSIONS = frozenset(
    {
        ".bmp",
        ".gif",
        ".ico",
        ".jpeg",
        ".jfif",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)
VIDEO_EXTENSIONS = frozenset({".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm", ".wmv"})


def is_supported_image(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS


def is_supported_video(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in VIDEO_EXTENSIONS


def is_supported_media(path: Path) -> bool:
    return is_supported_image(path) or is_supported_video(path)


def scan_image_siblings(path: Path) -> list[Path]:
    try:
        return [item.path for item in scan_image_folder(path.parent)]
    except OSError:
        return []


def scan_media_folder(
    folder: Path, should_cancel: Callable[[], bool] | None = None
) -> list[MediaItem]:
    """Read image and video metadata in stable filename order."""
    folder = folder.expanduser().resolve()
    paths = _sorted_media_paths(folder)
    ffprobe = find_ffprobe()
    items: list[MediaItem] = []
    for path in paths:
        if should_cancel is not None and should_cancel():
            break
        if path.suffix.casefold() in IMAGE_EXTENSIONS:
            item = _read_image_item(path)
        else:
            item = _read_video_item(path, ffprobe, should_cancel)
        if item is not None:
            items.append(item)
    return items


def scan_image_folder(
    folder: Path, should_cancel: Callable[[], bool] | None = None
) -> list[MediaItem]:
    """Read only image metadata; retained for focused image operations and tests."""
    folder = folder.expanduser().resolve()
    paths = sorted(
        (item for item in folder.iterdir() if is_supported_image(item)),
        key=lambda item: (item.name.casefold(), item.name),
    )
    items: list[MediaItem] = []
    for path in paths:
        if should_cancel is not None and should_cancel():
            break
        item = _read_image_item(path)
        if item is not None:
            items.append(item)
    return items


def _sorted_media_paths(folder: Path) -> list[Path]:
    return sorted(
        (item for item in folder.iterdir() if is_supported_media(item)),
        key=lambda item: (item.name.casefold(), item.name),
    )


def _read_image_item(path: Path) -> MediaItem | None:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    if not reader.canRead():
        return None
    size = reader.size()
    if not size.isValid():
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return MediaItem(
        path=path,
        width=size.width(),
        height=size.height(),
        file_size=stat.st_size,
        kind=MediaKind.IMAGE,
        created_ns=stat.st_ctime_ns,
        modified_ns=stat.st_mtime_ns,
    )


def _read_video_item(
    path: Path,
    ffprobe: str | None,
    should_cancel: Callable[[], bool] | None,
) -> MediaItem | None:
    metadata = probe_video(path, ffprobe, should_cancel) if ffprobe is not None else None
    if ffprobe is not None and metadata is None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return MediaItem(
        path=path,
        width=metadata.width if metadata else 320,
        height=metadata.height if metadata else 180,
        file_size=stat.st_size,
        kind=MediaKind.VIDEO,
        duration_ms=metadata.duration_ms if metadata else 0,
        created_ns=stat.st_ctime_ns,
        modified_ns=stat.st_mtime_ns,
    )
