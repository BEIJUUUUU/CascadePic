from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from waterfall_viewer.services.media_catalog import scan_media_folder
from waterfall_viewer.workers.safe_signals import safe_emit


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
            items = scan_media_folder(self.folder, self._cancelled.is_set)
        except Exception as error:  # noqa: BLE001 - must always report back
            # Catching broadly on purpose: an uncaught error here would emit no
            # signal at all, leaving the UI stuck on "正在扫描…" with no dialog.
            if self._cancelled.is_set():
                safe_emit(self.signals.cancelled, self.generation)
            else:
                safe_emit(self.signals.failed, self.generation, str(error))
            return
        if self._cancelled.is_set():
            safe_emit(self.signals.cancelled, self.generation)
            return
        safe_emit(self.signals.finished, self.generation, items)
