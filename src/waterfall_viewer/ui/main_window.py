from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QCloseEvent, QImageReader, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
)

from waterfall_viewer.models.media_item import MediaItem
from waterfall_viewer.services.media_catalog import is_supported_image
from waterfall_viewer.ui.image_canvas import ImageCanvas
from waterfall_viewer.ui.waterfall_view import WaterfallView
from waterfall_viewer.workers.folder_scan_worker import FolderScanWorker


class MainWindow(QMainWindow):
    """Main window containing the folder waterfall and single-image viewer."""

    def __init__(self) -> None:
        super().__init__()
        self._images: list[Path] = []
        self._current_index = -1
        self._folder_items: list[MediaItem] = []
        self._scan_generation = 0
        self._scan_workers: dict[int, FolderScanWorker] = {}
        self._scan_selections: dict[int, Path | None] = {}
        self._scan_folders: dict[int, Path] = {}
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(2)

        self.setWindowTitle("Waterfall Media Viewer")
        self.resize(1200, 800)

        self.canvas = ImageCanvas()
        self.waterfall = WaterfallView()
        self.waterfall.activated.connect(self._open_from_waterfall)
        self._pages = QStackedWidget()
        self._pages.addWidget(self.waterfall)
        self._pages.addWidget(self.canvas)
        self.setCentralWidget(self._pages)

        self._status_label = QLabel("打开图片或文件夹开始浏览")
        self.statusBar().addPermanentWidget(self._status_label, 1)
        self._create_toolbar()

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("浏览工具", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        open_action = QAction("打开图片", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_image)
        toolbar.addAction(open_action)

        folder_action = QAction("打开文件夹", self)
        folder_action.setShortcut("Ctrl+Shift+O")
        folder_action.triggered.connect(self.choose_folder)
        toolbar.addAction(folder_action)

        waterfall_action = QAction("瀑布流", self)
        waterfall_action.setShortcut(Qt.Key.Key_Escape)
        waterfall_action.triggered.connect(self.show_waterfall)
        toolbar.addAction(waterfall_action)

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

    def choose_image(self) -> None:
        filters = "图片 (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff *.ico);;所有文件 (*)"
        filename, _ = QFileDialog.getOpenFileName(self, "打开图片", "", filters)
        if filename:
            self.open_path(Path(filename))

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "打开图片文件夹")
        if folder:
            self.open_folder(Path(folder))

    def open_input(self, path: Path) -> bool:
        if path.is_dir():
            self.open_folder(path)
            return True
        return self.open_path(path)

    def open_folder(self, folder: Path) -> None:
        folder = folder.expanduser().resolve()
        self._status_label.setText(f"正在扫描：{folder}")
        self._start_folder_scan(folder, selected_path=None)

    def _start_folder_scan(self, folder: Path, selected_path: Path | None) -> None:
        for worker in self._scan_workers.values():
            worker.cancel()
        self._scan_workers.clear()
        self._scan_selections.clear()
        self._scan_folders.clear()

        self._scan_generation += 1
        generation = self._scan_generation
        worker = FolderScanWorker(folder, generation)
        worker.signals.finished.connect(self._folder_scan_finished)
        worker.signals.failed.connect(self._folder_scan_failed)
        worker.signals.cancelled.connect(self._folder_scan_cancelled)
        self._scan_workers[generation] = worker
        self._scan_selections[generation] = selected_path
        self._scan_folders[generation] = folder
        self._thread_pool.start(worker)

    def _folder_scan_finished(self, generation: int, items: list[MediaItem]) -> None:
        self._scan_workers.pop(generation, None)
        selected_path = self._scan_selections.pop(generation, None)
        folder = self._scan_folders.pop(generation, None)
        if generation != self._scan_generation:
            return

        self._folder_items = items
        self._images = [item.path for item in items]
        self.waterfall.set_items(items)
        folder_label = folder or (items[0].path.parent if items else "当前文件夹")

        if selected_path is not None and selected_path in self._images:
            self._current_index = self._images.index(selected_path)
            selected_item = items[self._current_index]
            self._status_label.setText(
                f"{self._current_index + 1} / {len(items)}    "
                f"{selected_item.width} × {selected_item.height}    {selected_path}"
            )
            return

        self._current_index = -1
        self._pages.setCurrentWidget(self.waterfall)
        self.setWindowTitle(f"{folder_label} — Waterfall Media Viewer")
        self._status_label.setText(f"共 {len(items)} 张图片    {folder_label}")

    def _folder_scan_failed(self, generation: int, error: str) -> None:
        self._scan_workers.pop(generation, None)
        self._scan_selections.pop(generation, None)
        self._scan_folders.pop(generation, None)
        if generation != self._scan_generation:
            return
        self._status_label.setText("文件夹扫描失败")
        self._show_error(f"无法扫描文件夹：\n{error}")

    def _folder_scan_cancelled(self, generation: int) -> None:
        self._scan_workers.pop(generation, None)
        self._scan_selections.pop(generation, None)
        self._scan_folders.pop(generation, None)

    def open_path(self, path: Path) -> bool:
        path = path.expanduser().resolve()
        if not is_supported_image(path):
            self._show_error(f"不支持或不存在的图片：\n{path}")
            return False

        self._folder_items = []
        self._images = [path]
        self._current_index = 0
        if not self._load_current():
            return False
        self._status_label.setText(f"正在扫描同目录图片：{path.parent}")
        self._start_folder_scan(path.parent, selected_path=path)
        return True

    def _open_from_waterfall(self, path: Path) -> None:
        try:
            self._current_index = self._images.index(path)
        except ValueError:
            return
        self._load_current()

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
        self._pages.setCurrentWidget(self.canvas)
        self.setWindowTitle(f"{path.name} — Waterfall Media Viewer")
        self._status_label.setText(
            f"{self._current_index + 1} / {len(self._images)}    "
            f"{image.width()} × {image.height()}    {path}"
        )
        return True

    def show_waterfall(self) -> None:
        if not self._folder_items:
            return
        self._pages.setCurrentWidget(self.waterfall)
        folder = self._folder_items[0].path.parent
        self.setWindowTitle(f"{folder} — Waterfall Media Viewer")
        self._status_label.setText(f"共 {len(self._folder_items)} 张图片    {folder}")

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

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        for worker in self._scan_workers.values():
            worker.cancel()
        super().closeEvent(event)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "无法打开", message)
