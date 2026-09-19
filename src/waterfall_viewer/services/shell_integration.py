"""Windows Explorer integration: register/unregister the CascadePic context menu.

Everything is written to HKEY_CURRENT_USER, so no administrator rights and no
UAC prompt are required. Unregistering removes every key that was created.
"""

from __future__ import annotations

import sys
from pathlib import Path

VERB_KEY = "CascadePic"
VERB_LABEL = "用流瀑看图打开"
FRIENDLY_NAME = "CascadePic 流瀑看图"

MEDIA_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".jfif",
    ".png",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
    ".ico",
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".wmv",
    ".m4v",
)

_BASE_KEYS = (
    r"Software\Classes\Directory\shell",
    r"Software\Classes\Directory\Background\shell",
    r"Software\Classes\Applications\CascadePic.exe",
)


def is_context_menu_installed() -> bool:
    """True when the CascadePic verb is currently registered for folders."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\Directory\shell\{VERB_KEY}\command",
        ):
            return True
    except OSError:
        return False


def resolve_executable() -> Path:
    """Return the CascadePic executable used by the context menu entry."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    # Development checkout: prefer an existing packaged build.
    root = Path(__file__).resolve().parents[3]
    packaged = root / "dist" / "CascadePic" / "CascadePic.exe"
    if packaged.is_file():
        return packaged
    return Path(sys.executable).resolve()


def _notify_shell() -> None:
    """Ask Explorer to refresh its context menu cache."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass


def _menu_keys() -> list[str]:
    keys = list(_BASE_KEYS[:2])
    keys.extend(rf"Software\Classes\SystemFileAssociations\{ext}\shell" for ext in MEDIA_EXTENSIONS)
    return keys


def install(exe_path: Path | None = None) -> int:
    """Register the context menu. Returns the number of created locations."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("右键菜单集成仅支持 Windows。")

    import winreg

    exe = (exe_path or resolve_executable()).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"找不到可执行文件：{exe}")
    exe_text = str(exe)

    created = 0

    def write_verb(base_key: str, argument: str) -> None:
        nonlocal created
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{base_key}\{VERB_KEY}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, VERB_LABEL)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f"{exe_text},0")
            # Multi-select opens a single window instead of one per file.
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Single")
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, rf"{base_key}\{VERB_KEY}\command"
        ) as command:
            winreg.SetValueEx(command, "", 0, winreg.REG_SZ, f'"{exe_text}" "{argument}"')
        created += 1

    # Selected folder and empty folder background.
    write_verb(r"Software\Classes\Directory\shell", "%1")
    write_verb(r"Software\Classes\Directory\Background\shell", "%V")

    # Media files.
    for extension in MEDIA_EXTENSIONS:
        write_verb(rf"Software\Classes\SystemFileAssociations\{extension}\shell", "%1")

    # "Open with" candidate list.
    app_key = r"Software\Classes\Applications\CascadePic.exe"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key}\shell\open\command") as command:
        winreg.SetValueEx(command, "", 0, winreg.REG_SZ, f'"{exe_text}" "%1"')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key) as key:
        winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, FRIENDLY_NAME)
        winreg.SetValueEx(key, "DefaultIcon", 0, winreg.REG_SZ, f"{exe_text},0")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key}\SupportedTypes") as types:
        for extension in MEDIA_EXTENSIONS:
            winreg.SetValueEx(types, extension, 0, winreg.REG_SZ, "")
    created += 1

    _notify_shell()
    return created


def uninstall() -> int:
    """Remove every key created by :func:`install`. Returns removal count."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("右键菜单集成仅支持 Windows。")

    import winreg

    removed = 0

    def delete_tree(path: str) -> bool:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            # Non-empty: clear children first.
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS
                ) as key:
                    names = []
                    index = 0
                    while True:
                        try:
                            names.append(winreg.EnumKey(key, index))
                            index += 1
                        except OSError:
                            break
                for name in names:
                    delete_tree(rf"{path}\{name}")
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
                return True
            except OSError:
                return False

    for base in _menu_keys():
        if delete_tree(rf"{base}\{VERB_KEY}"):
            removed += 1

    if delete_tree(r"Software\Classes\Applications\CascadePic.exe"):
        removed += 1

    _notify_shell()
    return removed
