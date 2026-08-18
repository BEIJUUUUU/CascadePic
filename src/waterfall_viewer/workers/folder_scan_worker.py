from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from waterfall_viewer.services.media_catalog import scan_image_folder


class FolderScanSignals(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)
    cancelled = Signal(int)


class FolderScanWorker(QRunnable):
    """Scan image metadata outside the GUI thread with cooperative cancellation."""

    def __init__(self, folder: Path, generation: int) -> None:
        super().__init__()
        self.folder = folder
        self.generation = generation
        self.signals = FolderScanSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            items = scan_image_folder(self.folder, self._cancelled.is_set)
        except OSError as error:
            if self._cancelled.is_set():
                self.signals.cancelled.emit(self.generation)
            else:
                self.signals.failed.emit(self.generation, str(error))
            return
        if self._cancelled.is_set():
            self.signals.cancelled.emit(self.generation)
            return
        self.signals.finished.emit(self.generation, items)
