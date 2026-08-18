from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import vlc
except (ImportError, OSError):
    vlc = None

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from waterfall_viewer.ui.jump_slider import JumpSlider
from waterfall_viewer.utils.formatting import format_duration


class VideoPlayer(QWidget):
    """Small libVLC-backed video player suitable for the media viewer page."""

    playback_error = Signal(str)
    navigate_requested = Signal(int)

    def __init__(self, vlc_instance: Any | None = None) -> None:
        super().__init__()
        self._instance = vlc_instance
        self._player = None
        self._seeking = False

        self.setObjectName("videoPlayer")
        self.video_surface = QWidget()
        self.video_surface.setObjectName("videoSurface")
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_surface.installEventFilter(self)
        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("playButton")
        self.play_button.setToolTip("播放 / 暂停")
        self.position_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("positionSlider")
        self.position_slider.setRange(0, 1000)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("timeLabel")
        self.volume_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(120)

        controls_widget = QWidget()
        controls_widget.setObjectName("videoControls")
        controls = QHBoxLayout(controls_widget)
        controls.setContentsMargins(16, 10, 16, 10)
        controls.setSpacing(12)
        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(QLabel("音量"))
        controls.addWidget(self.volume_slider)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video_surface, 1)
        layout.addWidget(controls_widget)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._update_progress)
        self.play_button.clicked.connect(self.toggle_play)
        self.position_slider.sliderPressed.connect(self._begin_seek)
        self.position_slider.sliderReleased.connect(self._finish_seek)
        self.position_slider.jumped.connect(self._seek_to_value)
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
        self.play_button.setText("Ⅱ")
        self._timer.start()
        return True

    def toggle_play(self) -> None:
        if self._player is None:
            return
        if self._player.is_playing():
            self._player.pause()
            self.play_button.setText("▶")
        else:
            self._player.play()
            self.play_button.setText("Ⅱ")
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._player is not None:
            self._player.stop()
        self.position_slider.setValue(0)
        self.time_label.setText("0:00 / 0:00")
        self.play_button.setText("▶")

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
        self._seek_to_value(self.position_slider.value())

    def _seek_to_value(self, value: int) -> None:
        if self._player is not None:
            self._player.set_position(value / 1000)

    def _set_volume(self, value: int) -> None:
        if self._player is not None:
            self._player.audio_set_volume(value)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API name
        if watched is self.video_surface and event.type() is QEvent.Type.Wheel:
            self._emit_wheel_navigation(event)
            return True
        return super().eventFilter(watched, event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API name
        self._emit_wheel_navigation(event)

    def _emit_wheel_navigation(self, event: QWheelEvent) -> None:
        direction = -1 if event.angleDelta().y() > 0 else 1
        self.navigate_requested.emit(direction)
        event.accept()

    def _update_progress(self) -> None:
        if self._player is None:
            return
        if vlc is not None and hasattr(self._player, "get_state"):
            state = self._player.get_state()
            if state == vlc.State.Error:
                self._timer.stop()
                self.play_button.setText("▶")
                self.time_label.setText("播放失败")
                self.playback_error.emit("VLC 无法播放当前视频")
                return
            if state == vlc.State.Ended:
                self._timer.stop()
                self.play_button.setText("▶")
                return
        duration = max(0, self._player.get_length())
        current = max(0, self._player.get_time())
        if not self._seeking and duration > 0:
            self.position_slider.setValue(round(current / duration * 1000))
        self.time_label.setText(f"{format_duration(current)} / {format_duration(duration)}")
        if duration > 0 and current >= duration:
            self.play_button.setText("▶")
            self._timer.stop()
