from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QSignalSpy

from waterfall_viewer.ui import video_player
from waterfall_viewer.ui.video_player import VideoPlayer
from waterfall_viewer.utils.formatting import format_duration


class FakePlayer:
    def __init__(self) -> None:
        self.media = None
        self.playing = False
        self.volume = 0
        self.position = 0.0
        self.time = 2_000
        self.length = 10_000
        self.window_id = None

    def audio_set_volume(self, value: int) -> None:
        self.volume = value

    def set_media(self, media) -> None:
        self.media = media

    def set_hwnd(self, window_id: int) -> None:
        self.window_id = window_id

    def set_xwindow(self, window_id: int) -> None:
        self.window_id = window_id

    def set_nsobject(self, window_id: int) -> None:
        self.window_id = window_id

    def play(self) -> int:
        self.playing = True
        return 0

    def stop(self) -> None:
        self.playing = False

    def pause(self) -> None:
        self.playing = False

    def is_playing(self) -> bool:
        return self.playing

    def get_length(self) -> int:
        return self.length

    def get_time(self) -> int:
        return self.time

    def set_position(self, position: float) -> None:
        self.position = position


class FakeVlcInstance:
    def __init__(self) -> None:
        self.player = FakePlayer()

    def media_player_new(self) -> FakePlayer:
        return self.player

    def media_new(self, path: str) -> str:
        return path


def test_duration_formatting() -> None:
    assert format_duration(65_000) == "1:05"
    assert format_duration(3_661_000) == "1:01:01"


def test_video_player_handles_missing_vlc(qtbot, monkeypatch) -> None:
    monkeypatch.setattr(video_player, "vlc", None)

    player = VideoPlayer()
    qtbot.addWidget(player)

    assert not player.is_available
    assert player.time_label.text() == "VLC 不可用"


def test_video_player_opens_and_controls_media(qtbot, tmp_path: Path) -> None:
    instance = FakeVlcInstance()
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)
    path = tmp_path / "clip.mp4"
    path.touch()

    assert player.open(path)
    assert instance.player.media == str(path)
    assert instance.player.playing

    player.toggle_play()
    assert not instance.player.playing
    player.volume_slider.setValue(35)
    assert instance.player.volume == 35

    player.resize(800, 500)
    player.show()
    qtbot.mouseClick(
        player.position_slider,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(player.position_slider.width() * 0.75), 5),
    )
    assert 0.73 <= instance.player.position <= 0.77

    qtbot.mouseClick(
        player.volume_slider,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(player.volume_slider.width() * 0.6), 5),
    )
    assert 58 <= instance.player.volume <= 62

    player.stop()
    assert player.position_slider.value() == 0
    qtbot.waitUntil(lambda: not instance.player.playing, timeout=2000)


def test_video_wheel_requests_media_navigation(qtbot) -> None:
    player = VideoPlayer(vlc_instance=FakeVlcInstance())
    qtbot.addWidget(player)
    spy = QSignalSpy(player.navigate_requested)
    event = QWheelEvent(
        QPointF(100, 100),
        QPointF(100, 100),
        QPoint(),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    player.wheelEvent(event)

    assert spy.count() == 1
    assert spy.at(0)[0] == 1
