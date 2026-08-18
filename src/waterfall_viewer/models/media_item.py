from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


@dataclass(frozen=True, slots=True)
class MediaItem:
    """Lightweight metadata used to lay out an image or video tile."""

    path: Path
    width: int
    height: int
    file_size: int = 0
    kind: MediaKind = MediaKind.IMAGE
    duration_ms: int = 0

    @property
    def aspect_ratio(self) -> float:
        if self.width <= 0 or self.height <= 0:
            return 1.0
        return self.width / self.height

    @property
    def is_video(self) -> bool:
        return self.kind is MediaKind.VIDEO
