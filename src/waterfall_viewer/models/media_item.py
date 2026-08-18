from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MediaItem:
    """Lightweight metadata used to lay out a media item without decoding it."""

    path: Path
    width: int
    height: int
    file_size: int = 0

    @property
    def aspect_ratio(self) -> float:
        if self.width <= 0 or self.height <= 0:
            return 1.0
        return self.width / self.height
