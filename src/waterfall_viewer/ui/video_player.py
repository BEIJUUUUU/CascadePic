from __future__ import annotations

import sys
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any

import shiboken6
from PySide6.QtCore import QEvent, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QWheelEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from waterfall_viewer.ui.jump_slider import JumpSlider
from waterfall_viewer.utils.formatting import format_duration

try:
    import vlc
except (ImportError, OSError):
    vlc = None


class _StopState:
    """Mutable state shared with a stop job.

    Kept as its own object so the job never holds a reference back to the
    widget, which would create a reference cycle through the thread pool.
    """

    __slots__ = ("epoch", "stopping")

    def __init__(self) -> None:
        self.stopping = False
        self.epoch = 0


class _StopJob(QRunnable):
    """Call the blocking VLC stop outside the UI thread.

    Holds only the player, the lock and a plain state object: the widget may be
    destroyed while this job is still queued, and touching it from a worker
    thread would raise or, worse, crash the interpreter.

    The epoch guard fixes the stop/open race: ``open()`` bumps the epoch, and a
    stop job captured under an older epoch skips the VLC call entirely instead
    of stopping the video that was opened after it was queued.
    """

    def __init__(self, player: Any, lock: threading.Lock, state: _StopState, epoch: int) -> None:
        super().__init__()
        self._player = player
        self._lock = lock
        self._state = state
        self._epoch = epoch

    @Slot()
    def run(self) -> None:
        with suppress(Exception), self._lock:
            if self._state.epoch == self._epoch:
                self._player.stop()
        self._state.stopping = False


class VideoPlayer(QWidget):
    """Small libVLC-backed video player suitable for the media viewer page."""

    playback_error = Signal(str)
    navigate_requested = Signal(int)

    def __init__(self, vlc_instance: Any | None = None) -> None:
        super().__init__()
        self._instance = vlc_instance
        self._player = None
        self._seeking = False
        self._length_ms = 0
        self._stop_state = _StopState()
        self._lock = threading.Lock()
        # A process-wide pool: giving the widget its own QThreadPool ties the
        # pool's lifetime to the widget, and destroying it while a stop job is
        # still running crashes inside Qt's thread cleanup.
        self._pool = QThreadPool.globalInstance()

        self.setObjectName("videoPlayer")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.installEventFilter(self)
        self.video_surface = QWidget()
        self.video_surface.setObjectName("videoSurface")
        self.video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_surface.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.video_surface.installEventFilter(self)
        self._icon_play = QIcon(
            str(Path(__file__).parent.parent / "resources" / "icons" / "play.svg")
        )
        self._icon_pause = QIcon(
            str(Path(__file__).parent.parent / "resources" / "icons" / "pause.svg")
        )
        self._icon_volume = QIcon(
            str(Path(__file__).parent.parent / "resources" / "icons" / "volume.svg")
        )

        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setIcon(self._icon_play)
        self.play_button.setIconSize(QSize(15, 15))
        self.play_button.setToolTip("播放 / 暂停 (Space)")
        self.position_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("positionSlider")
        self.position_slider.setRange(0, 1000)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("timeLabel")

        vol_icon_label = QLabel()
        vol_icon_label.setObjectName("volumeIcon")
        vol_icon_label.setPixmap(self._icon_volume.pixmap(16, 16))
        vol_icon_label.setToolTip("音量")

        self.volume_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)

        controls_widget = QWidget()
        controls_widget.setObjectName("videoControls")
        controls = QHBoxLayout(controls_widget)
        controls.setContentsMargins(16, 10, 16, 10)
        controls.setSpacing(12)
        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(vol_icon_label)
        controls.addWidget(self.volume_slider)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video_surface, 1)
        layout.addWidget(controls_widget)

        self._timer = QTimer(self)
        self._timer.setInterval(500)
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
                self._instance = vlc.Instance(
                    "--no-video-title-show",
                    "--quiet",
                    "--avcodec-hw=any",
                )
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
        self._reset_controls()
        # Invalidate any queued stop job so it cannot stop this new video
        # after we start it (the stale-stop race).
        self._stop_state.epoch += 1
        self._stop_state.stopping = False
        try:
            media = self._instance.media_new(str(path))
            self._player.set_media(media)
            self._bind_video_surface()
            result = self._player.play()
        except Exception:
            return False
        if result == -1:
            return False
        self.play_button.setIcon(self._icon_pause)
        self._timer.start()
        return True

    def toggle_play(self) -> None:
        if self._player is None:
            return
        # Lock-free for the same reason as _seek_to_value / _set_volume: the
        # shared lock would block the UI thread behind a background VLC stop.
        if self._player.is_playing():
            self._player.pause()
            self.play_button.setIcon(self._icon_play)
        else:
            self._player.play()
            self.play_button.setIcon(self._icon_pause)
            self._timer.start()

    def _reset_controls(self) -> None:
        self._timer.stop()
        self._length_ms = 0
        self.position_slider.setValue(0)
        self.time_label.setText("0:00 / 0:00")
        self.play_button.setIcon(self._icon_play)

    def stop(self) -> None:
        self._reset_controls()
        if self._player is None or self._stop_state.stopping:
            return
        self._stop_state.stopping = True
        self._pool.start(
            _StopJob(self._player, self._lock, self._stop_state, self._stop_state.epoch)
        )

    def shutdown(self) -> None:
        """Release native resources and detach the event filter before teardown.

        Called from the owning window's close handler: leaving the filter
        installed while the widget is destroyed is what produced a shiboken
        access violation at interpreter shutdown.
        """
        with suppress(RuntimeError):
            self._timer.stop()
        with suppress(RuntimeError):
            self.removeEventFilter(self)
            surface = getattr(self, "video_surface", None)
            if surface is not None:
                surface.removeEventFilter(self)
        player = self._player
        self._player = None
        if player is not None:
            # Bump the epoch so any queued stop job skips its VLC call, then
            # stop inline: releasing a player that a queued job may still call
            # is a use-after-release crash.
            self._stop_state.epoch += 1
            with self._lock, suppress(Exception):
                player.stop()
            with suppress(Exception):
                player.release()

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
        if self._player is None:
            return
        # No Python lock here: libVLC calls are internally thread-safe, and
        # serialising them against the background stop job would freeze the UI
        # thread for the whole duration of a blocking VLC stop.
        self._player.set_position(value / 1000)

    def _set_volume(self, value: int) -> None:
        if self._player is None:
            return
        self._player.audio_set_volume(value)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API name
        # Qt can deliver a final event after the underlying C++ object has been
        # destroyed (e.g. during interpreter shutdown), so validate the wrapper
        # before touching anything.
        if not shiboken6.isValid(self):
            return False
        try:
            is_wheel = event.type() is QEvent.Type.Wheel
        except RuntimeError:
            return False
        if is_wheel and watched in (self, getattr(self, "video_surface", None)):
            self._emit_wheel_navigation(event)
            return True
        # QWidget.eventFilter does nothing but return False. Calling it through
        # zero-argument super() is unsafe here: the shiboken wrapper can outlive
        # its type during teardown, raising
        # "super(type, obj): obj must be an instance or subtype of type".
        return False

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API name
        self._emit_wheel_navigation(event)

    def _emit_wheel_navigation(self, event: QWheelEvent) -> None:
        direction = -1 if event.angleDelta().y() > 0 else 1
        self.navigate_requested.emit(direction)
        event.accept()

    def _update_progress(self) -> None:
        if self._player is None:
            return
        try:
            if vlc is not None and hasattr(self._player, "get_state"):
                state = self._player.get_state()
                if state == vlc.State.Error:
                    self._timer.stop()
                    self.play_button.setIcon(self._icon_play)
                    self.time_label.setText("播放失败")
                    self.playback_error.emit("VLC 无法播放当前视频")
                    return
                if state == vlc.State.Ended:
                    self._timer.stop()
                    self.play_button.setIcon(self._icon_play)
                    return
            if self._length_ms <= 0:
                self._length_ms = max(0, self._player.get_length())
            duration = self._length_ms
            current = max(0, self._player.get_time())
        except Exception:
            self._timer.stop()
            return
        if not self._seeking and duration > 0:
            self.position_slider.setValue(round(current / duration * 1000))
        self.time_label.setText(f"{format_duration(current)} / {format_duration(duration)}")
        if duration > 0 and current >= duration:
            self.play_button.setIcon(self._icon_play)
            self._timer.stop()
