from pathlib import Path

from waterfall_viewer.models.media_item import MediaItem
from waterfall_viewer.services.media_sort import SortMode, sort_media_items


def _item(name: str, created: int = 0, modified: int = 0) -> MediaItem:
    return MediaItem(
        Path(name),
        width=100,
        height=100,
        created_ns=created,
        modified_ns=modified,
    )


def test_name_sort_uses_natural_number_order() -> None:
    items = [_item("photo10.jpg"), _item("photo2.jpg"), _item("photo1.jpg")]

    result = sort_media_items(items, SortMode.NAME)

    assert [item.path.name for item in result] == [
        "photo1.jpg",
        "photo2.jpg",
        "photo10.jpg",
    ]


def test_modified_sort_places_newest_first() -> None:
    items = [_item("old.jpg", modified=10), _item("new.jpg", modified=30)]

    result = sort_media_items(items, SortMode.MODIFIED)

    assert [item.path.name for item in result] == ["new.jpg", "old.jpg"]


def test_created_sort_places_newest_first() -> None:
    items = [_item("old.jpg", created=10), _item("new.jpg", created=30)]

    result = sort_media_items(items, SortMode.CREATED)

    assert [item.path.name for item in result] == ["new.jpg", "old.jpg"]
