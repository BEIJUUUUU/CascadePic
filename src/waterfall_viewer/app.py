from __future__ import annotations

import json
import os
import sys
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _configure_frozen_runtime() -> None:
    """Point python-vlc at the libVLC bundled next to a PyInstaller build."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).parent
    if (base / "libvlc.dll").is_file():
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", str(base / "libvlc.dll"))
        os.environ.setdefault("PYTHON_VLC_MODULE_PATH", str(base / "plugins"))


def _apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f3f6fb"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111821"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1b2430"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f3f6fb"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#222b36"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f3f6fb"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#60a5fa"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def _apply_stylesheet(app: QApplication) -> None:
    stylesheet = Path(__file__).parent / "resources" / "styles" / "fluent_dark.qss"
    with suppress(OSError):
        app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))


def _parse_args(
    argv: list[str],
) -> tuple[str | None, list[str]]:
    smoke_path: str | None = None
    media_args: list[str] = []
    index = 0
    while index < len(argv):
        if argv[index] == "--smoke" and index + 1 < len(argv):
            smoke_path = argv[index + 1]
            index += 2
        else:
            media_args.append(argv[index])
            index += 1
    return smoke_path, media_args


def _write_smoke_report(smoke_path: str) -> None:
    from waterfall_viewer.services.video_probe import find_ffmpeg, find_ffprobe
    from waterfall_viewer.ui.video_player import VideoPlayer

    player = VideoPlayer()
    report = {
        "ffmpeg": find_ffmpeg(),
        "ffprobe": find_ffprobe(),
        "vlc_available": player.is_available,
    }
    player.deleteLater()
    report_path = Path(smoke_path).with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    _configure_frozen_runtime()

    # Import after runtime configuration so bundled VLC is found by python-vlc.
    from waterfall_viewer.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Waterfall Media Viewer")
    app.setOrganizationName("Waterfall Media Viewer")
    app.setStyle("Fusion")
    _apply_dark_palette(app)
    _apply_stylesheet(app)

    smoke_path, media_args = _parse_args(sys.argv[1:])
    window = MainWindow()
    if media_args:
        window.open_input(Path(media_args[0]))
    window.show()
    if smoke_path:
        QTimer.singleShot(
            2000,
            lambda: (
                window.grab().save(smoke_path),
                _write_smoke_report(smoke_path),
                window.close(),
                app.quit(),
            ),
        )
    return app.exec()
