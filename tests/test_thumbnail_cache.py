import os
from pathlib import Path

from PySide6.QtGui import QColor, QImage

from waterfall_viewer.services.thumbnail_cache import ThumbnailDiskCache
from waterfall_viewer.workers.thumbnail_worker import ThumbnailWorker


def _write_image(path: Path, color: str = "red") -> QImage:
    image = QImage(160, 90, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    assert image.save(str(path))
    return image


def test_disk_cache_round_trip_and_clear(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache")

    assert cache.store(source, 160, image)
    loaded = cache.load(source, 160)

    assert loaded is not None
    assert loaded.size() == image.size()
    assert cache.total_size() > 0
    assert cache.clear() == 1
    assert cache.total_size() == 0


def test_cache_clear_ignores_in_progress_temp_files(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache")
    assert cache.store(source, 160, image)
    temporary = cache.root / ".writing.tmp.png"
    temporary.write_bytes(b"partial")

    assert cache.clear() == 1
    assert temporary.exists()


def test_disk_cache_invalidates_when_source_changes(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache")
    assert cache.store(source, 160, image)
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert cache.load(source, 160) is None


def test_disk_cache_prunes_to_size_budget(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache", max_bytes=1)
    assert cache.store(source, 160, image)

    assert cache.prune() == 1
    assert cache.total_size() == 0


def test_cancelled_disk_cache_write_does_not_create_entry(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache")

    assert not cache.store(source, 160, image, lambda: True)
    assert cache.total_size() == 0


def test_thumbnail_worker_reports_disk_cache_hit(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    image = _write_image(source)
    cache = ThumbnailDiskCache(tmp_path / "cache")
    assert cache.store(source, 160, image)
    results: list[bool] = []
    worker = ThumbnailWorker(source, 160, 7, cache)
    worker.signals.loaded.connect(
        lambda _generation, _path, _width, _image, hit: results.append(hit)
    )

    worker.run()

    assert results == [True]
