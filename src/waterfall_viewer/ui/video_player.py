from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import vlc
except (ImportError, OSError):
    vlc = None

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from waterfall_viewer.utils.formatting import format_duration


class VideoPlayer(QWidget):
    """Small libVLC-backed video player suitable for the media viewer page."""

    playback_error = Signal(str)

    def __init__(self, vlc_instance: Any | None = None) -> None:
        super().__init__()
        self._instance = vlc_instance
        self._player = None
        self._seeking = False

        self.video_surface = QWidget()
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_surface.setStyleSheet("background: black;")
        self.play_button = QPushButton("播放")
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.time_label = QLabel("0:00 / 0:00")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(QLabel("音量"))
        controls.addWidget(self.volume_slider)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_surface, 1)
        layout.addLayout(controls)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._update_progress)
        self.play_button.clicked.connect(self.toggle_play)
        self.position_slider.sliderPressed.connect(self._begin_seek)
        self.position_slider.sliderReleased.connect(self._finish_seek)
        self.volume_slider.valueChanged.connect(self._set_volume)
        self._initialize_backend()

    @property
    def is_available(self) -> bool:
        return self._player is not None

    def _initialize_backend(self) -> None:
        try:
            if self._instance is None:
                if vlc is None:
                    self._set_unavailable()
                    return
                self._instance = vlc.Instance("--no-video-title-show", "--quiet")
            if self._instance is None:
                self._set_unavailable()
                return
            self._player = self._instance.media_player_new()
            self._player.audio_set_volume(self.volume_slider.value())
        except Exception:
            self._set_unavailable()

    def _set_unavailable(self) -> None:
        self._instance = None
        self._player = None
        self.play_button.setEnabled(False)
        self.position_slider.setEnabled(False)
        self.volume_slider.setEnabled(False)
        self.time_label.setText("VLC 不可用")

    def open(self, path: Path) -> bool:
        if self._player is None or self._instance is None:
            return False
        self.stop()
        try:
            media = self._instance.media_new(str(path))
            self._player.set_media(media)
            self._bind_video_surface()
            result = self._player.play()
        except Exception:
            return False
        if result == -1:
            return False
        self.play_button.setText("暂停")
        self._timer.start()
        return True

    def toggle_play(self) -> None:
        if self._player is None:
            return
        if self._player.is_playing():
            self._player.pause()
            self.play_button.setText("播放")
        else:
            self._player.play()
            self.play_button.setText("暂停")
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._player is not None:
            self._player.stop()
        self.position_slider.setValue(0)
        self.time_label.setText("0:00 / 0:00")
        self.play_button.setText("播放")

    def _bind_video_surface(self) -> None:
        if self._player is None:
            return
        window_id = int(self.video_surface.winId())
        if sys.platform.startswith("win"):
            self._player.set_hwnd(window_id)
        elif sys.platform == "darwin":
            self._player.set_nsobject(window_id)
        else:
            self._player.set_xwindow(window_id)

    def _begin_seek(self) -> None:
        self._seeking = True

    def _finish_seek(self) -> None:
        self._seeking = False
        if self._player is not None:
            self._player.set_position(self.position_slider.value() / 1000)

    def _set_volume(self, value: int) -> None:
        if self._player is not None:
            self._player.audio_set_volume(value)

    def _update_progress(self) -> None:
        if self._player is None:
            return
        if vlc is not None and hasattr(self._player, "get_state"):
            state = self._player.get_state()
            if state == vlc.State.Error:
                self._timer.stop()
                self.play_button.setText("播放")
                self.time_label.setText("播放失败")
                self.playback_error.emit("VLC 无法播放当前视频")
                return
            if state == vlc.State.Ended:
                self._timer.stop()
                self.play_button.setText("播放")
                return
        duration = max(0, self._player.get_length())
        current = max(0, self._player.get_time())
        if not self._seeking and duration > 0:
            self.position_slider.setValue(round(current / duration * 1000))
        self.time_label.setText(f"{format_duration(current)} / {format_duration(duration)}")
        if duration > 0 and current >= duration:
            self.play_button.setText("播放")
            self._timer.stop()
