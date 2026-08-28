from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from PySide6.QtGui import QImage


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    width: int
    height: int
    duration_ms: int


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes = b""


def find_ffprobe() -> str | None:
    return _find_tool("WATERFALL_FFPROBE", "ffprobe.exe") or _find_tool(
        "WATERFALL_FFPROBE", "ffprobe"
    )


def find_ffmpeg() -> str | None:
    return _find_tool("WATERFALL_FFMPEG", "ffmpeg.exe") or _find_tool("WATERFALL_FFMPEG", "ffmpeg")


def probe_video(
    path: Path,
    executable: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> VideoMetadata | None:
    # 1. Try ffprobe first if available (fast json output)
    ffprobe_bin = executable or find_ffprobe()
    if ffprobe_bin is not None:
        command = [
            ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ]
        result = _run_process(command, timeout=20, should_cancel=should_cancel)
        if result is not None and result.returncode == 0:
            try:
                payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
                stream = payload.get("streams", [{}])[0]
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                duration_ms = max(0, round(float(payload.get("format", {}).get("duration", 0)) * 1000))
                if width > 0 and height > 0:
                    return VideoMetadata(width=width, height=height, duration_ms=duration_ms)
            except (ValueError, TypeError, IndexError, json.JSONDecodeError):
                pass

    # 2. Fallback to ffmpeg -i info header (allows omitting the ~80MB ffprobe binary!)
    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin is None:
        return None
    command = [ffmpeg_bin, "-hide_banner", "-i", str(path)]
    result = _run_process(command, timeout=20, should_cancel=should_cancel)
    if result is None:
        return None
    info = (result.stderr or result.stdout).decode("utf-8", errors="replace")
    
    # Parse Duration: HH:MM:SS.ms
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    duration_ms = 0
    if dur_match:
        h, m, s = dur_match.groups()
        duration_ms = int((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)

    # Parse Video Stream: Video: ..., 1920x1080 [SAR ...
    vid_match = re.search(r"Stream #.*?: Video: .*?, (\d{2,5})x(\d{2,5})", info)
    if not vid_match:
        return None
    width, height = int(vid_match.group(1)), int(vid_match.group(2))
    if width <= 0 or height <= 0:
        return None
    return VideoMetadata(width=width, height=height, duration_ms=duration_ms)


def extract_video_thumbnail(
    path: Path,
    target_width: int,
    executable: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> QImage | None:
    executable = executable or find_ffmpeg()
    if executable is None:
        return None
    scale_filter = f"scale={max(64, target_width)}:4096:force_original_aspect_ratio=decrease"
    command = [
        executable,
        "-v",
        "error",
        "-i",
        str(path),
        "-frames:v",
        "1",
        "-vf",
        scale_filter,
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "pipe:1",
    ]
    result = _run_process(command, timeout=30, should_cancel=should_cancel)
    if result is None or result.returncode != 0 or not result.stdout:
        return None
    image = QImage.fromData(result.stdout, "PNG")
    return None if image.isNull() else image


def _run_process(
    command: list[str],
    timeout: float,
    should_cancel: Callable[[], bool] | None = None,
) -> _ProcessResult | None:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=_creation_flags(),
        )
    except OSError:
        return None

    deadline = monotonic() + timeout
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.1)
            return _ProcessResult(process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            cancelled = should_cancel is not None and should_cancel()
            if not cancelled and monotonic() < deadline:
                continue
            process.terminate()
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            return None


def _find_tool(environment_name: str, executable_name: str) -> str | None:
    configured = os.environ.get(environment_name)
    if configured and Path(configured).is_file():
        return configured
    if getattr(sys, "frozen", False):
        bundled = Path(sys.executable).parent / executable_name
        if bundled.is_file():
            return str(bundled)
    return shutil.which(executable_name)


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
