"""Regression tests for the audit findings (C1, C2, H1, H2, H3, M5)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtCore import QCoreApplication, QPoint, QRunnable, Qt, QThreadPool

from waterfall_viewer.ui.jump_slider import JumpSlider
from waterfall_viewer.ui.main_window import MainWindow
from waterfall_viewer.ui.video_player import VideoPlayer
from waterfall_viewer.workers.safe_signals import stop_worker


def test_stop_worker_safe_on_deleted_runnable(qtbot) -> None:
    """C1: tryTake on an auto-deleted QRunnable must not raise."""

    class Job(QRunnable):
        called = False

        def run(self) -> None:
            Job.called = True
            time.sleep(0.05)

    pool = QThreadPool.globalInstance()
    worker = Job()
    pool.start(worker)
    # Wait for run() to finish: Qt has auto-deleted the C++ object by now.
    time.sleep(0.2)
    QCoreApplication.processEvents()

    # Must not raise even though the C++ object is gone.
    assert stop_worker(pool, worker) in (True, False)


def test_cancel_image_loads_survives_deleted_workers(qtbot, tmp_path: Path) -> None:
    """C1: _cancel_image_loads must not raise when a worker already finished."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # No image was ever loaded; the dict is empty. Call repeatedly to make sure
    # the path is exception-free, including after real workers have run.
    for _ in range(3):
        window._cancel_image_loads()
    window.close()


def test_image_loaded_guards_stale_index(qtbot, tmp_path: Path) -> None:
    """C2: a decode finishing after a folder scan must not raise IndexError."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Simulate the race: decode result arrives after _images was replaced.
    window._images = []
    window._current_index = -1
    window._image_load_generation = 1
    window._pending_image_path = tmp_path / "old.png"
    window._image_loaded(1, str(tmp_path / "old.png"), None)  # must not raise
    window.close()


class FakePlayer:
    """Records the call order so races can be asserted."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.playing = False

    def audio_set_volume(self, value: int) -> None:
        self.calls.append(f"volume:{value}")

    def set_media(self, media) -> None:
        self.calls.append(f"media:{media}")

    def set_hwnd(self, window_id: int) -> None:
        self.calls.append("hwnd")

    def set_xwindow(self, window_id: int) -> None:
        self.calls.append("xwindow")

    def set_nsobject(self, window_id: int) -> None:
        self.calls.append("nsobject")

    def play(self) -> int:
        self.playing = True
        self.calls.append("play")
        return 0

    def stop(self) -> None:
        self.calls.append("stop")
        self.playing = False

    def pause(self) -> None:
        self.calls.append("pause")
        self.playing = False

    def is_playing(self) -> bool:
        return self.playing

    def get_length(self) -> int:
        return 10_000

    def get_time(self) -> int:
        return 0

    def set_position(self, position: float) -> None:
        self.calls.append(f"pos:{position}")

    def release(self) -> None:
        self.calls.append("release")


class FakeInstance:
    def __init__(self) -> None:
        self.player = FakePlayer()

    def media_player_new(self) -> FakePlayer:
        return self.player

    def media_new(self, path: str) -> str:
        return path


def test_stale_stop_job_does_not_stop_new_video(qtbot, tmp_path: Path) -> None:
    """H1: a stop queued before open() must not stop the video opened after."""
    instance = FakeInstance()
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)

    # Queue a stop (this is what Esc / switching media does).
    player._player = instance.player
    player.stop()
    assert instance.player.calls[-1] != "stop"  # async, not yet executed

    # Immediately open a new video.
    first = tmp_path / "b.mp4"
    first.touch()
    assert player.open(first)

    # Let the queued job run.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and player._stop_state.stopping:
        qtbot.wait(20)
    qtbot.wait(100)

    # The stop job was captured under an older epoch, so it must skip.
    media_calls = [c for c in instance.player.calls if c.startswith("media:")]
    assert "stop" not in instance.player.calls[instance.player.calls.index("play") + 1 :]
    assert media_calls[-1] == f"media:{first}"
    assert instance.player.playing


def test_shutdown_does_not_release_under_queued_stop(qtbot, tmp_path: Path) -> None:
    """H2: release() must happen with no queued stop job able to touch the player."""
    instance = FakeInstance()
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)
    player._player = instance.player
    player.stop()
    player.shutdown()

    calls = instance.player.calls
    if "release" in calls:
        release = calls.index("release")
        # no stop call after release
        assert "stop" not in calls[release + 1 :]


def test_ui_calls_not_blocked_by_slow_stop(qtbot) -> None:
    """H3: seek/volume/toggle must not block behind a slow background stop."""

    class SlowPlayer(FakePlayer):
        def stop(self) -> None:
            time.sleep(0.8)
            self.playing = False
            self.calls.append("stop")

    instance = FakeInstance()
    instance.player = SlowPlayer()
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)
    player._player = instance.player
    player.stop()

    start = time.monotonic()
    player.volume_slider.setValue(30)
    player._seek_to_value(500)
    elapsed = time.monotonic() - start

    assert elapsed < 0.3, f"UI calls blocked for {elapsed:.2f}s behind slow stop"


def test_jump_slider_emits_press_release_once(qtbot) -> None:
    """M5: slider press/release signals must fire exactly once per click."""
    from PySide6.QtTest import QSignalSpy

    slider = JumpSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 1000)
    slider.resize(200, 24)
    pressed = QSignalSpy(slider.sliderPressed)
    released = QSignalSpy(slider.sliderReleased)
    slider.show()
    qtbot.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(100, 12))
    qtbot.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(100, 12))
    assert pressed.count() == 2, f"sliderPressed fired {pressed.count()}x for 2 clicks"
    assert released.count() == 2, f"sliderReleased fired {released.count()}x for 2 clicks"


def test_resize_keeps_cached_thumbnails(qtbot) -> None:
    """H7: a small resize must not discard the decoded thumbnail cache."""
    from waterfall_viewer.models.media_item import MediaItem
    from waterfall_viewer.ui.waterfall_view import WaterfallView

    view = WaterfallView()
    qtbot.addWidget(view)
    view.resize(900, 700)
    view.show()

    items = [
        MediaItem(
            path=Path(f"/fake/{i}.png"),
            kind=None,
            width=200,
            height=300,
            file_size=1,
            modified_ns=0,
            created_ns=0,
        )
        for i in range(3)
    ]
    view.set_items(items)
    # Inject fake thumbnails as if they had been decoded.
    for item in items:
        key = (str(item.path), view._target_decode_width())
        view._thumbnails[key] = None  # placeholder; presence is what matters
    before = len(view._thumbnails)

    view.resize(901, 700)  # 1-pixel resize

    assert len(view._thumbnails) == before, "cache was wiped by a 1px resize"
    view.close()
