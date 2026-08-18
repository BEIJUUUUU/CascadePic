from __future__ import annotations

import re
from enum import StrEnum

from waterfall_viewer.models.media_item import MediaItem


class SortMode(StrEnum):
    NAME = "name"
    MODIFIED = "modified"
    CREATED = "created"


def sort_media_items(items: list[MediaItem], mode: SortMode) -> list[MediaItem]:
    """Return media in Explorer-like name order or newest timestamp order."""
    if mode is SortMode.MODIFIED:
        return sorted(
            items,
            key=lambda item: (-item.modified_ns, _natural_name_key(item.path.name)),
        )
    if mode is SortMode.CREATED:
        return sorted(
            items,
            key=lambda item: (-item.created_ns, _natural_name_key(item.path.name)),
        )
    return sorted(items, key=lambda item: _natural_name_key(item.path.name))


def _natural_name_key(name: str) -> tuple[tuple[int, int | str], ...]:
    parts = re.split(r"(\d+)", name.casefold())
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts if part)
