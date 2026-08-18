from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QImageReader, QKeySequence
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QToolBar

from waterfall_viewer.services.media_catalog import is_supported_image, scan_image_siblings
from waterfall_viewer.ui.image_canvas import ImageCanvas


class MainWindow(QMainWindow):
    """Initial single-image viewer prototype."""

    def __init__(self) -> None:
        super().__init__()
        self._images: list[Path] = []
        self._current_index = -1

        self.setWindowTitle("Waterfall Media Viewer")
        self.resize(1200, 800)

        self.canvas = ImageCanvas()
        self.setCentralWidget(self.canvas)
        self._status_label = QLabel("打开一张图片开始浏览")
        self.statusBar().addPermanentWidget(self._status_label, 1)
        self._create_toolbar()

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("图片工具", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_image)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        previous_action = QAction("上一张", self)
        previous_action.setShortcut(Qt.Key.Key_Left)
        previous_action.triggered.connect(self.show_previous)
        toolbar.addAction(previous_action)

        next_action = QAction("下一张", self)
        next_action.setShortcut(Qt.Key.Key_Right)
        next_action.triggered.connect(self.show_next)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        fit_action = QAction("适应窗口", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self.canvas.fit_to_window)
        toolbar.addAction(fit_action)

        actual_action = QAction("原始大小", self)
        actual_action.setShortcut("1")
        actual_action.triggered.connect(self.canvas.actual_size)
        toolbar.addAction(actual_action)

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.canvas.zoom(1.2))
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.canvas.zoom(1 / 1.2))
        toolbar.addAction(zoom_out_action)

        fullscreen_action = QAction("全屏", self)
        fullscreen_action.setShortcut(Qt.Key.Key_F11)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)

        exit_fullscreen_action = QAction("退出全屏", self)
        exit_fullscreen_action.setShortcut(Qt.Key.Key_Escape)
        exit_fullscreen_action.triggered.connect(self.exit_fullscreen)
        self.addAction(exit_fullscreen_action)

    def choose_image(self) -> None:
        filters = "图片 (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff *.ico);;所有文件 (*)"
        filename, _ = QFileDialog.getOpenFileName(self, "打开图片", "", filters)
        if filename:
            self.open_path(Path(filename))

    def open_path(self, path: Path) -> bool:
        path = path.expanduser().resolve()
        if not is_supported_image(path):
            self._show_error(f"不支持或不存在的图片：\n{path}")
            return False

        images = scan_image_siblings(path)
        try:
            current_index = images.index(path)
        except ValueError:
            images = [path]
            current_index = 0

        self._images = images
        self._current_index = current_index
        return self._load_current()

    def _load_current(self) -> bool:
        if not 0 <= self._current_index < len(self._images):
            return False

        path = self._images[self._current_index]
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self._show_error(f"无法读取图片：\n{path}\n\n{reader.errorString()}")
            return False

        self.canvas.set_image(image)
        self.setWindowTitle(f"{path.name} — Waterfall Media Viewer")
        self._status_label.setText(
            f"{self._current_index + 1} / {len(self._images)}    "
            f"{image.width()} × {image.height()}    {path}"
        )
        return True

    def show_previous(self) -> None:
        if not self._images:
            return
        self._current_index = (self._current_index - 1) % len(self._images)
        self._load_current()

    def show_next(self) -> None:
        if not self._images:
            return
        self._current_index = (self._current_index + 1) % len(self._images)
        self._load_current()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "无法打开", message)
