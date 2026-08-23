from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QImage, QKeySequence, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QWidget,
)

from waterfall_viewer.models.media_item import MediaItem
from waterfall_viewer.services.media_catalog import (
    is_supported_image,
    is_supported_media,
    is_supported_video,
)
from waterfall_viewer.services.media_sort import SortMode, sort_media_items
from waterfall_viewer.ui.image_canvas import ImageCanvas
from waterfall_viewer.ui.video_player import VideoPlayer
from waterfall_viewer.ui.waterfall_view import WaterfallView
from waterfall_viewer.utils.formatting import format_duration
from waterfall_viewer.workers.folder_scan_worker import FolderScanWorker
from waterfall_viewer.workers.image_loader import ImageLoadWorker


class MainWindow(QMainWindow):
    """Main window containing the folder waterfall and single-image viewer."""

    def __init__(self) -> None:
        super().__init__()
        self._images: list[Path] = []
        self._current_index = -1
        self._folder_items: list[MediaItem] = []
        self._item_by_path: dict[Path, MediaItem] = {}
        self._scan_generation = 0
        self._scan_workers: dict[int, FolderScanWorker] = {}
        self._scan_selections: dict[int, Path | None] = {}
        self._scan_folders: dict[int, Path] = {}
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(2)
        self._image_pool = QThreadPool(self)
        self._image_pool.setMaxThreadCount(2)
        self._image_load_generation = 0
        self._pending_image_path: Path | None = None
        self._image_workers: dict[int, ImageLoadWorker] = {}
        self._image_cache: OrderedDict[str, QImage] = OrderedDict()
        self._image_cache_bytes = 0
        self._image_cache_limit = 512 * 1024 * 1024

        self.setWindowTitle("Waterfall Media Viewer")
        self.resize(1200, 800)

        self.canvas = ImageCanvas()
        self.canvas.navigate_requested.connect(self._navigate_by_wheel)
        self.video_player = VideoPlayer()
        self.video_player.playback_error.connect(self._video_playback_error)
        self.video_player.navigate_requested.connect(self._navigate_by_wheel)
        self.waterfall = WaterfallView()
        self.waterfall.activated.connect(self._open_from_waterfall)
        self._pages = QStackedWidget()
        self._pages.addWidget(self.waterfall)
        self._pages.addWidget(self.canvas)
        self._pages.addWidget(self.video_player)
        self.setCentralWidget(self._pages)

        self._viewer_close_button = QToolButton(self._pages)
        self._viewer_close_button.setObjectName("viewerCloseButton")
        self._viewer_close_button.setText("×")
        self._viewer_close_button.setToolTip("返回瀑布流 (Esc)")
        self._viewer_close_button.setFixedSize(38, 38)
        self._viewer_close_button.clicked.connect(self.show_waterfall)
        self._viewer_close_button.hide()

        self._status_label = QLabel("打开媒体文件或文件夹开始浏览")
        self.statusBar().addPermanentWidget(self._status_label, 1)
        self._create_toolbar()

    def _icon(self, name: str) -> QIcon:
        path = Path(__file__).parent.parent / "resources" / "icons" / f"{name}.svg"
        return QIcon(str(path))

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("浏览工具", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(21, 21))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(toolbar)

        open_action = QAction("打开媒体", self)
        open_action.setIcon(self._icon("image_open"))
        open_action.setToolTip("打开媒体  Ctrl+O")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_image)
        toolbar.addAction(open_action)

        folder_action = QAction("打开文件夹", self)
        folder_action.setIcon(self._icon("folder_open"))
        folder_action.setToolTip("打开文件夹  Ctrl+Shift+O")
        folder_action.setShortcut("Ctrl+Shift+O")
        folder_action.triggered.connect(self.choose_folder)
        toolbar.addAction(folder_action)

        toolbar.addSeparator()

        sort_label = QLabel("排序")
        sort_label.setObjectName("toolbarLabel")
        toolbar.addWidget(sort_label)
        self._sort_combo = QComboBox()
        self._sort_combo.addItem("名称（文件夹默认）", SortMode.NAME)
        self._sort_combo.addItem("修改时间（新→旧）", SortMode.MODIFIED)
        self._sort_combo.addItem("创建时间（新→旧）", SortMode.CREATED)
        self._sort_combo.currentIndexChanged.connect(self._apply_current_sort)
        toolbar.addWidget(self._sort_combo)

        toolbar.addSeparator()

        thumbnail_label = QLabel("缩略图")
        thumbnail_label.setObjectName("toolbarLabel")
        toolbar.addWidget(thumbnail_label)
        self._thumbnail_slider = QSlider(Qt.Orientation.Horizontal)
        self._thumbnail_slider.setRange(120, 480)
        self._thumbnail_slider.setSingleStep(20)
        self._thumbnail_slider.setPageStep(40)
        self._thumbnail_slider.setValue(220)
        self._thumbnail_slider.setFixedWidth(130)
        self._thumbnail_slider.valueChanged.connect(self.waterfall.set_thumbnail_width)
        toolbar.addWidget(self._thumbnail_slider)

        clear_cache_action = QAction("清缓存", self)
        clear_cache_action.setIcon(self._icon("delete"))
        clear_cache_action.setToolTip("清理缩略图缓存")
        clear_cache_action.triggered.connect(self.clear_thumbnail_cache)
        toolbar.addAction(clear_cache_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        previous_action = QAction("上一张", self)
        previous_action.setIcon(self._icon("previous"))
        previous_action.setToolTip("上一张  ← / 滚轮向上")
        previous_action.setShortcut(Qt.Key.Key_Left)
        previous_action.triggered.connect(self.show_previous)
        toolbar.addAction(previous_action)

        next_action = QAction("下一张", self)
        next_action.setIcon(self._icon("next"))
        next_action.setToolTip("下一张  → / 滚轮向下")
        next_action.setShortcut(Qt.Key.Key_Right)
        next_action.triggered.connect(self.show_next)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        fit_action = QAction("适应窗口", self)
        fit_action.setIcon(self._icon("fit"))
        fit_action.setToolTip("适应窗口  F")
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self.canvas.fit_to_window)
        toolbar.addAction(fit_action)

        actual_action = QAction("原始大小", self)
        actual_action.setIcon(self._icon("actual"))
        actual_action.setToolTip("原始大小  1")
        actual_action.setShortcut("1")
        actual_action.triggered.connect(self.canvas.actual_size)
        toolbar.addAction(actual_action)

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setIcon(self._icon("zoom_in"))
        zoom_in_action.setToolTip("放大  Ctrl++ / 右键+滚轮")
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.canvas.zoom(1.2))
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setIcon(self._icon("zoom_out"))
        zoom_out_action.setToolTip("缩小  Ctrl+- / 右键+滚轮")
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.canvas.zoom(1 / 1.2))
        toolbar.addAction(zoom_out_action)

        fullscreen_action = QAction("全屏", self)
        fullscreen_action.setShortcut(Qt.Key.Key_F11)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)

        close_viewer_action = QAction("返回瀑布流", self)
        close_viewer_action.setShortcut(Qt.Key.Key_Escape)
        close_viewer_action.triggered.connect(self.show_waterfall)
        self.addAction(close_viewer_action)

    def choose_image(self) -> None:
        filters = (
            "媒体 (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff *.ico "
            "*.mp4 *.mkv *.webm *.mov *.avi *.wmv *.m4v);;所有文件 (*)"
        )
        filename, _ = QFileDialog.getOpenFileName(self, "打开媒体", "", filters)
        if filename:
            self.open_path(Path(filename))

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "打开媒体文件夹")
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

        items = sort_media_items(items, self._current_sort_mode())
        self._folder_items = items
        self._item_by_path = {item.path: item for item in items}
        self._images = [item.path for item in items]
        self.waterfall.set_items(items)
        folder_label = folder or (items[0].path.parent if items else "当前文件夹")

        if selected_path is not None and selected_path in self._images:
            self._current_index = self._images.index(selected_path)
            selected_item = items[self._current_index]
            details = f"{selected_item.width} × {selected_item.height}"
            if selected_item.is_video and selected_item.duration_ms:
                details += f"    {format_duration(selected_item.duration_ms)}"
            self._status_label.setText(
                f"{self._current_index + 1} / {len(items)}    {details}    {selected_path}"
            )
            return

        self._current_index = -1
        self.video_player.stop()
        self._set_current_page(self.waterfall)
        self.setWindowTitle(f"{folder_label} — Waterfall Media Viewer")
        self._status_label.setText(f"共 {len(items)} 个媒体文件    {folder_label}")

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
        if not is_supported_media(path):
            self._show_error(f"不支持或不存在的媒体文件：\n{path}")
            return False

        self._folder_items = []
        self._item_by_path = {}
        self._images = [path]
        self._current_index = 0
        self._status_label.setText(f"正在扫描同目录媒体：{path.parent}")
        self._start_folder_scan(path.parent, selected_path=path)
        return self._load_current()

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
        if is_supported_video(path):
            if not self.video_player.open(path):
                self._show_error(f"无法播放视频，请确认 VLC 可用：\n{path}")
                return False
            self._set_current_page(self.video_player)
            self.setWindowTitle(f"{path.name} — Waterfall Media Viewer")
            item = self._item_by_path.get(path)
            duration = (
                f"    {format_duration(item.duration_ms)}"
                if item is not None and item.duration_ms
                else ""
            )
            self._status_label.setText(
                f"{self._current_index + 1} / {len(self._images)}{duration}    {path}"
            )
            return True

        if not is_supported_image(path):
            return False
        self.video_player.stop()
        self._set_current_page(self.canvas)
        self.setWindowTitle(f"{path.name} — Waterfall Media Viewer")
        self._status_label.setText(f"正在加载图片：{path.name}")
        self._start_image_load(path)
        return True

    def _start_image_load(self, path: Path) -> None:
        self._image_load_generation += 1
        generation = self._image_load_generation
        self._pending_image_path = path

        for old_generation, old_worker in list(self._image_workers.items()):
            old_worker.cancel()
            if self._image_pool.tryTake(old_worker):
                self._image_workers.pop(old_generation, None)

        key = str(path)
        cached = self._image_cache.get(key)
        if cached is not None:
            self._image_cache.move_to_end(key)
            self._image_loaded(generation, key, cached)
            return

        worker = ImageLoadWorker(path, generation)
        worker.signals.loaded.connect(self._image_loaded)
        worker.signals.failed.connect(self._image_load_failed)
        worker.signals.cancelled.connect(self._image_load_cancelled)
        self._image_workers[generation] = worker
        self._image_pool.start(worker)

    def _image_loaded(self, generation: int, path_str: str, image: QImage) -> None:
        self._image_workers.pop(generation, None)
        if generation != self._image_load_generation or path_str != str(self._pending_image_path):
            return
        self._pending_image_path = None
        self._cache_full_image(path_str, image)
        self.canvas.set_image(image)
        self._status_label.setText(
            f"{self._current_index + 1} / {len(self._images)}    "
            f"{image.width()} × {image.height()}    {self._images[self._current_index]}"
        )

    def _cache_full_image(self, path_str: str, image: QImage) -> None:
        size = max(1, image.sizeInBytes())
        previous = self._image_cache.pop(path_str, None)
        if previous is not None:
            self._image_cache_bytes -= max(1, previous.sizeInBytes())
        if size > self._image_cache_limit:
            return
        self._image_cache[path_str] = image
        self._image_cache_bytes += size
        while self._image_cache_bytes > self._image_cache_limit and self._image_cache:
            _, evicted = self._image_cache.popitem(last=False)
            self._image_cache_bytes -= max(1, evicted.sizeInBytes())

    def _image_load_failed(self, generation: int, path_str: str, error: str) -> None:
        self._image_workers.pop(generation, None)
        if generation != self._image_load_generation or path_str != str(self._pending_image_path):
            return
        self._pending_image_path = None
        self._show_error(f"无法读取图片：\n{path_str}\n\n{error}")

    def _image_load_cancelled(self, generation: int, _path_str: str) -> None:
        self._image_workers.pop(generation, None)

    def _current_sort_mode(self) -> SortMode:
        data = self._sort_combo.currentData()
        return data if isinstance(data, SortMode) else SortMode(data)

    def _apply_current_sort(self, _index: int = -1) -> None:
        if not self._folder_items:
            return
        current_path = (
            self._images[self._current_index]
            if 0 <= self._current_index < len(self._images)
            else None
        )
        self._folder_items = sort_media_items(self._folder_items, self._current_sort_mode())
        self._images = [item.path for item in self._folder_items]
        if current_path in self._images:
            self._current_index = self._images.index(current_path)
        self.waterfall.set_items(self._folder_items)

    def _set_current_page(self, page: QWidget) -> None:
        self._pages.setCurrentWidget(page)
        self._viewer_close_button.setVisible(page is not self.waterfall)
        self._position_viewer_close_button()

    def _position_viewer_close_button(self) -> None:
        if not hasattr(self, "_viewer_close_button"):
            return
        margin = 14
        self._viewer_close_button.move(
            self._pages.width() - self._viewer_close_button.width() - margin,
            margin,
        )
        self._viewer_close_button.raise_()

    def _navigate_by_wheel(self, direction: int) -> None:
        if direction < 0:
            self.show_previous()
        else:
            self.show_next()

    def show_waterfall(self) -> None:
        self.video_player.stop()
        self._set_current_page(self.waterfall)
        if not self._folder_items:
            self.setWindowTitle("Waterfall Media Viewer")
            self._status_label.setText("打开媒体文件或文件夹开始浏览")
            return
        folder = self._folder_items[0].path.parent
        self.setWindowTitle(f"{folder} — Waterfall Media Viewer")
        self._status_label.setText(f"共 {len(self._folder_items)} 个媒体文件    {folder}")

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

    def _video_playback_error(self, message: str) -> None:
        self._status_label.setText(message)

    def clear_thumbnail_cache(self) -> None:
        removed = self.waterfall.clear_thumbnail_cache()
        self._image_cache.clear()
        self._image_cache_bytes = 0
        self._status_label.setText(f"已清理 {removed} 个磁盘缩略图缓存文件和内存图片缓存")

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._position_viewer_close_button()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        for worker in self._scan_workers.values():
            worker.cancel()
        self._image_load_generation += 1
        self._pending_image_path = None
        for worker in self._image_workers.values():
            worker.cancel()
        self.video_player.stop()
        super().closeEvent(event)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "无法打开", message)
