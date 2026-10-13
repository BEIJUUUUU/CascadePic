"""Regression tests for the loop playback feature."""

from __future__ import annotations

from pathlib import Path

import pytest

from waterfall_viewer.ui import video_player
from waterfall_viewer.ui.video_player import VideoPlayer


class FakePlayer:
    def __init__(self, state=None) -> None:
        self.calls: list[str] = []
        self.playing = False
        self.time = 0
        self.restarts = 0
        self._state = state

    def get_state(self):
        return self._state

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
        self.restarts += 1
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

    def set_time(self, value: int) -> None:
        self.time = value
        self.calls.append(f"time:{value}")

    def set_position(self, position: float) -> None:
        self.calls.append(f"pos:{position}")

    def release(self) -> None:
        self.calls.append("release")


class FakeInstance:
    def __init__(self, state=None) -> None:
        self.player = FakePlayer(state)

    def media_player_new(self) -> FakePlayer:
        return self.player

    def media_new(self, path: str) -> str:
        return path


@pytest.fixture(autouse=True)
def _no_real_vlc(monkeypatch):
    monkeypatch.setattr(video_player, "vlc", __import__("vlc"))


def test_loop_restarts_on_end(qtbot) -> None:
    instance = FakeInstance(video_player.vlc.State.Ended)
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)
    player.open(Path("a.mp4"))
    instance.player.playing = False

    player._update_progress()

    assert instance.player.restarts == 2  # initial play + loop restart
    assert "time:0" in instance.player.calls
    assert player._timer.isActive()


def test_loop_disabled_stops_on_end(qtbot) -> None:
    instance = FakeInstance(video_player.vlc.State.Ended)
    player = VideoPlayer(vlc_instance=instance)
    qtbot.addWidget(player)
    player.open(Path("a.mp4"))
    player.loop_button.setChecked(False)
    instance.player.playing = False

    player._update_progress()

    assert instance.player.restarts == 1
    assert not player._timer.isActive()


def test_loop_toggle_updates_state(qtbot) -> None:
    player = VideoPlayer(vlc_instance=FakeInstance())
    qtbot.addWidget(player)

    player.loop_button.setChecked(False)
    assert player.loop_enabled is False
    player.loop_button.setChecked(True)
    assert player.loop_enabled is True
    # Default is on.
    player2 = VideoPlayer(vlc_instance=FakeInstance())
    qtbot.addWidget(player2)
    assert player2.loop_enabled is True
    assert player2.loop_button.isChecked()
