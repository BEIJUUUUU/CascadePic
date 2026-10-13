"""Verify the audit's Critical findings against the current code."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRunnable, QThreadPool, QCoreApplication
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import shiboken6


class Slow(QRunnable):
    def run(self) -> None:
        import time

        time.sleep(0.05)


pool = QThreadPool.globalInstance()
job = Slow()
pool.start(job)

# Wait for run() to finish so Qt auto-deletes the C++ object, but do NOT let
# the (nonexistent) queued signals process.
import time

time.sleep(0.35)
QCoreApplication.processEvents()

print("C1: shiboken6.isValid(job) =", shiboken6.isValid(job))
try:
    taken = pool.tryTake(job)
    print("C1: tryTake returned", taken, "-> NO RuntimeError")
except RuntimeError as error:
    print("C1: tryTake RAISED RuntimeError ->", error)

# C2: index validation
print()
print("C2: check _image_loaded guards index bounds")
src = Path("src/waterfall_viewer/ui/main_window.py").read_text(encoding="utf-8")
start = src.index("def _image_loaded")
body = src[start : start + 700]
print("   has bounds check:", "0 <= self._current_index < len(self._images)" in body)

print()
print("H5: folder_scan_worker exception handling")
scan = Path("src/waterfall_viewer/workers/folder_scan_worker.py").read_text(encoding="utf-8")
print("   except OSError only:", "except OSError" in scan and "except Exception" not in scan)

print()
print("H6: thumbnail_worker divide-by-zero guard")
tw = Path("src/waterfall_viewer/workers/thumbnail_worker.py").read_text(encoding="utf-8")
idx = tw.find("def _decode_image")
seg = tw[idx : idx + 400]
print("   guards width>0:", "width() > 0" in seg or "w > 0" in seg)
