from __future__ import annotations

import sys
from contextlib import suppress
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from waterfall_viewer.ui.main_window import MainWindow


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


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Waterfall Media Viewer")
    app.setOrganizationName("Waterfall Media Viewer")
    app.setStyle("Fusion")
    _apply_dark_palette(app)
    _apply_stylesheet(app)

    window = MainWindow()
    if len(sys.argv) > 1:
        window.open_input(Path(sys.argv[1]))
    window.show()
    return app.exec()
