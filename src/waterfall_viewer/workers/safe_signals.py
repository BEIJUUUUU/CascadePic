"""Shared plumbing for the QRunnable workers.

Centralising these three things fixes a class of bugs that kept recurring while
each worker implemented them separately:

* ``SafeSignals``  — emitting after the C++ object was deleted must not raise.
* ``safe_emit``    — same guard, usable without holding a signals object.
* ``stop_worker``  — cancelling a worker that Qt has already auto-deleted used
  to raise from ``QThreadPool.tryTake``. Every call site needs this guard, so
  it lives in one place instead of being copy-pasted.
"""

from __future__ import annotations

from contextlib import suppress

import shiboken6
from PySide6.QtCore import QObject, QThreadPool


def safe_emit(signal, *args) -> None:
    """Emit unless the underlying C++ object has already been destroyed."""
    if not shiboken6.isValid(signal):
        return
    with suppress(RuntimeError):
        signal.emit(*args)


class SafeSignals(QObject):
    """Base for worker signal holders that outlive their C++ object briefly."""

    def emit_safe(self, signal, *args) -> None:
        safe_emit(signal, *args)


def stop_worker(pool: QThreadPool, worker) -> bool:
    """Cancel ``worker`` and drop it from the queue if it is still queued.

    Returns True when the worker was successfully removed from the queue (so
    the caller can forget about it). Qt deletes a QRunnable as soon as ``run()``
    returns, and dereferencing that dead wrapper through ``tryTake`` raises
    ``RuntimeError`` — which is what previously aborted ``paintEvent``,
    ``set_items``, ``resizeEvent`` and ``closeEvent``.
    """
    with suppress(Exception):
        worker.cancel()
    if not shiboken6.isValid(worker):
        # Already finished and collected by Qt; nothing left to take.
        return True
    with suppress(RuntimeError):
        return pool.tryTake(worker)
    return False
