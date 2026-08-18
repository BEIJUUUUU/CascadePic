from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from waterfall_viewer.ui.main_window import MainWindow


def _apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#17191c"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f2f3f5"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111315"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#202328"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f2f3f5"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#25292e"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f2f3f5"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3b82f6"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Waterfall Media Viewer")
    app.setOrganizationName("Waterfall Media Viewer")
    app.setStyle("Fusion")
    _apply_dark_palette(app)

    window = MainWindow()
    if len(sys.argv) > 1:
        window.open_path(Path(sys.argv[1]))
    window.show()
    return app.exec()
