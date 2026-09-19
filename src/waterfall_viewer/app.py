from __future__ import annotations

import json
import os
import sys
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication


def _configure_frozen_runtime() -> None:
    """Point python-vlc at the libVLC bundled next to a PyInstaller build."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).parent
    if (base / "libvlc.dll").is_file():
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", str(base / "libvlc.dll"))
        os.environ.setdefault("PYTHON_VLC_MODULE_PATH", str(base / "plugins"))


def _apply_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#faf9f8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1b1a19"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f3f2f1"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1b1a19"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1b1a19"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078d4"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def _apply_stylesheet(app: QApplication) -> None:
    stylesheet = Path(__file__).parent / "resources" / "styles" / "fluent_light.qss"
    with suppress(OSError):
        app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))


def _parse_args(
    argv: list[str],
) -> tuple[str | None, list[str], str | None]:
    smoke_path: str | None = None
    action: str | None = None
    media_args: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--smoke" and index + 1 < len(argv):
            smoke_path = argv[index + 1]
            index += 2
        elif token in ("--install-context-menu", "--install-shell"):
            action = "install"
            index += 1
        elif token in ("--uninstall-context-menu", "--uninstall-shell"):
            action = "uninstall"
            index += 1
        else:
            media_args.append(token)
            index += 1
    return smoke_path, media_args, action


def _run_shell_action(app: QApplication, action: str) -> int:
    """Install or remove the Explorer context menu and report the result."""
    from PySide6.QtWidgets import QMessageBox

    from waterfall_viewer.services.shell_integration import install, uninstall

    try:
        if action == "install":
            count = install()
            QMessageBox.information(
                None,
                "流瀑看图",
                "右键菜单安装完成。\n\n"
                "现在可以在文件夹、文件夹空白处或图片/视频上点右键，\n"
                "选择「用流瀑看图打开」。\n\n"
                f"已写入 {count} 处注册项（不需要管理员权限）。",
            )
        else:
            count = uninstall()
            QMessageBox.information(
                None,
                "流瀑看图",
                f"右键菜单已卸载，共清理 {count} 处注册项。",
            )
    except Exception as error:  # noqa: BLE001 - surface any failure to the user
        QMessageBox.warning(None, "流瀑看图", f"操作失败：\n{error}")
        return 1
    app.quit()
    return 0


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
    app.setApplicationName("CascadePic (流瀑看图)")
    app.setApplicationDisplayName("CascadePic 流瀑看图")
    app.setOrganizationName("CascadePic")
    app_icon = QIcon(str(Path(__file__).parent / "resources" / "icons" / "app_logo.png"))
    app.setWindowIcon(app_icon)
    app.setStyle("Fusion")
    _apply_palette(app)
    _apply_stylesheet(app)

    smoke_path, media_args, shell_action = _parse_args(sys.argv[1:])

    if shell_action is not None:
        return _run_shell_action(app, shell_action)

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
