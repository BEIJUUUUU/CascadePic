import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage

from waterfall_viewer.services import video_probe


def test_probe_video_parses_ffprobe_json(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    path.touch()
    payload = {
        "streams": [{"width": 1920, "height": 1080}],
        "format": {"duration": "12.345"},
    }
    monkeypatch.setattr(
        video_probe,
        "_run_process",
        lambda *args, **kwargs: video_probe._ProcessResult(
            returncode=0, stdout=json.dumps(payload).encode()
        ),
    )

    metadata = video_probe.probe_video(path, executable="ffprobe")

    assert metadata is not None
    assert (metadata.width, metadata.height) == (1920, 1080)
    assert metadata.duration_ms == 12_345


def test_probe_video_accepts_unknown_duration(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "stream.webm"
    path.touch()
    payload = {
        "streams": [{"width": 1280, "height": 720}],
        "format": {"duration": "N/A"},
    }
    monkeypatch.setattr(
        video_probe,
        "_run_process",
        lambda *args, **kwargs: video_probe._ProcessResult(
            returncode=0, stdout=json.dumps(payload).encode()
        ),
    )

    metadata = video_probe.probe_video(path, executable="ffprobe")

    assert metadata is not None
    assert metadata.duration_ms == 0


def test_probe_video_returns_none_for_invalid_output(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "broken.mp4"
    path.touch()
    monkeypatch.setattr(
        video_probe,
        "_run_process",
        lambda *args, **kwargs: video_probe._ProcessResult(returncode=1, stdout=b"not-json"),
    )

    assert video_probe.probe_video(path, executable="ffprobe") is None


def test_extract_video_thumbnail_reads_png_pipe(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    path.touch()
    image = QImage(320, 180, QImage.Format.Format_RGB32)
    image.fill(QColor("purple"))
    data = QByteArray()
    buffer = QBuffer(data)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    monkeypatch.setattr(
        video_probe,
        "_run_process",
        lambda *args, **kwargs: video_probe._ProcessResult(returncode=0, stdout=bytes(data)),
    )

    thumbnail = video_probe.extract_video_thumbnail(path, 320, executable="ffmpeg")

    assert thumbnail is not None
    assert thumbnail.size() == image.size()


def test_process_runner_terminates_when_cancelled() -> None:
    started = time.perf_counter()

    result = video_probe._run_process(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=10,
        should_cancel=lambda: True,
    )

    assert result is None
    assert time.perf_counter() - started < 2


def test_find_tool_prefers_configured_environment(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "ffprobe.exe"
    configured.touch()
    monkeypatch.setenv("WATERFALL_FFPROBE", str(configured))

    assert video_probe._find_tool("WATERFALL_FFPROBE", "ffprobe.exe") == str(configured)


def test_find_tool_uses_frozen_executable_directory(monkeypatch, tmp_path: Path) -> None:
    bundled = tmp_path / "ffmpeg.exe"
    bundled.touch()
    monkeypatch.delenv("WATERFALL_FFMPEG", raising=False)
    monkeypatch.setattr(video_probe.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        video_probe.sys,
        "executable",
        str(tmp_path / "WaterfallMediaViewer.exe"),
        raising=False,
    )

    assert video_probe._find_tool("WATERFALL_FFMPEG", "ffmpeg.exe") == str(bundled)
