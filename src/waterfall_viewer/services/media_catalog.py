from __future__ import annotations

from pathlib import Path

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
    """Return supported images beside *path*, ordered case-insensitively by name."""
    folder = path.parent
    try:
        images = [item for item in folder.iterdir() if is_supported_image(item)]
    except OSError:
        return []
    return sorted(images, key=lambda item: (item.name.casefold(), item.name))
