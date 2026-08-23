from pathlib import Path

from PySide6.QtGui import QColor, QImage

from waterfall_viewer.workers.image_loader import ImageLoadWorker


def test_worker_loads_valid_image(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "photo.png"
    source = QImage(200, 120, QImage.Format.Format_RGB32)
    source.fill(QColor("orange"))
    assert source.save(str(path))

    worker = ImageLoadWorker(path, generation=1)
    results: list[tuple[str, QImage]] = []
    worker.signals.loaded.connect(lambda generation, key, image: results.append((key, image)))
    worker.signals.failed.connect(lambda *args: results.append(("failed", None)))

    worker.run()

    assert len(results) == 1
    key, image = results[0]
    assert key == str(path)
    assert image is not None and image.size() == source.size()


def test_worker_reports_failure_for_broken_file(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "broken.png"
    path.write_bytes(b"not a real image")

    worker = ImageLoadWorker(path, generation=1)
    results: list[str] = []
    worker.signals.loaded.connect(lambda *args: results.append("loaded"))
    worker.signals.failed.connect(lambda generation, key, error: results.append(f"failed:{key}"))

    worker.run()

    assert results == [f"failed:{path}"]
