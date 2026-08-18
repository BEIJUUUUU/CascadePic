from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from threading import Lock, get_ident

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QImage


class ThumbnailDiskCache:
    """Content-invalidating PNG thumbnail cache with a bounded disk budget."""

    def __init__(self, root: Path | None = None, max_bytes: int = 512 * 1024 * 1024) -> None:
        if root is None:
            cache_root = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.CacheLocation
            )
            root = Path(cache_root) / "thumbnails"
        self.root = root
        self.max_bytes = max(0, max_bytes)
        self._lock = Lock()
        self._writes_since_prune = 0

    def load(self, source: Path, target_width: int) -> QImage | None:
        entry = self._entry_path(source, target_width)
        if entry is None or not entry.is_file():
            return None
        image = QImage(str(entry))
        if image.isNull():
            with suppress(OSError):
                entry.unlink()
            return None
        with suppress(OSError):
            os.utime(entry, None)
        return image

    def store(
        self,
        source: Path,
        target_width: int,
        image: QImage,
        should_cancel: Callable[[], bool] | None = None,
    ) -> bool:
        entry = self._entry_path(source, target_width)
        if entry is None or image.isNull() or self.max_bytes == 0:
            return False
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False

        temporary = self.root / f".{entry.stem}.{get_ident()}.tmp.png"
        if not image.save(str(temporary), "PNG"):
            with suppress(OSError):
                temporary.unlink()
            return False
        try:
            with self._lock:
                if should_cancel is not None and should_cancel():
                    with suppress(OSError):
                        temporary.unlink()
                    return False
                os.replace(temporary, entry)
                self._writes_since_prune += 1
                should_prune = self._writes_since_prune >= 32
                if should_prune:
                    self._writes_since_prune = 0
        except OSError:
            with suppress(OSError):
                temporary.unlink()
            return False

        if should_prune:
            self.prune()
        return True

    def clear(self) -> int:
        removed = 0
        with self._lock:
            for entry in self._entries():
                try:
                    entry.unlink()
                    removed += 1
                except OSError:
                    continue
        return removed

    def total_size(self) -> int:
        total = 0
        for entry in self._entries():
            try:
                total += entry.stat().st_size
            except OSError:
                continue
        return total

    def prune(self) -> int:
        with self._lock:
            entries: list[tuple[Path, int, int]] = []
            total = 0
            for entry in self._entries():
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                entries.append((entry, stat.st_size, stat.st_mtime_ns))
                total += stat.st_size
            if total <= self.max_bytes:
                return 0

            removed = 0
            for entry, size, _ in sorted(entries, key=lambda value: value[2]):
                try:
                    entry.unlink()
                except OSError:
                    continue
                total -= size
                removed += 1
                if total <= self.max_bytes:
                    break
            return removed

    def _entry_path(self, source: Path, target_width: int) -> Path | None:
        try:
            stat = source.stat()
            normalized = str(source.resolve()).casefold()
        except OSError:
            return None
        identity = f"{normalized}\0{stat.st_size}\0{stat.st_mtime_ns}\0{target_width}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.png"

    def _entries(self) -> list[Path]:
        try:
            return [
                entry
                for entry in self.root.iterdir()
                if entry.is_file()
                and entry.suffix.casefold() == ".png"
                and not entry.name.startswith(".")
            ]
        except OSError:
            return []
