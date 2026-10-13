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

# Folder locations use their own label so the menu entry states the folder
# semantics explicitly instead of reusing the generic media wording.
FOLDER_VERB_KEY = "CascadePicFolder"
FOLDER_VERB_LABEL = "用流瀑看图浏览此文件夹"

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

# Folder locations get the folder-specific verb key and label; media files
# keep the generic media entry.
_MENU_LOCATIONS = (
    # Right-click on a folder icon.
    (r"Software\Classes\Directory\shell", "%1", FOLDER_VERB_KEY, FOLDER_VERB_LABEL),
    # Right-click on empty space inside a folder window.
    (r"Software\Classes\Directory\Background\shell", "%V", FOLDER_VERB_KEY, FOLDER_VERB_LABEL),
    # Right-click on empty space on the desktop.
    (r"Software\Classes\DesktopBackground\shell", "%V", FOLDER_VERB_KEY, FOLDER_VERB_LABEL),
    # Right-click on a drive letter in "This PC".
    (r"Software\Classes\Drive\shell", "%1", FOLDER_VERB_KEY, FOLDER_VERB_LABEL),
)

_APPLICATION_KEY = r"Software\Classes\Applications\CascadePic.exe"


def is_context_menu_installed() -> bool:
    """True when either CascadePic verb is currently registered for folders."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg

        for verb in (VERB_KEY, FOLDER_VERB_KEY):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"Software\Classes\Directory\shell\{verb}\command",
                ):
                    return True
            except OSError:
                continue
        return False
    except ImportError:
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


def _refresh_explorer() -> None:
    """Make Explorer pick up a change immediately.

    ``SHChangeNotify`` alone does not reliably invalidate the context-menu cache
    for newly added verb keys, so also broadcast a global setting-changed
    message that running Explorer windows react to.
    """
    if not sys.platform.startswith("win"):
        return
    import contextlib
    import ctypes

    with contextlib.suppress(Exception):
        # SHCNE_ASSOCCHANGED: associations changed.
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    with contextlib.suppress(Exception):
        # WM_SETTINGCHANGE broadcast, picked up by running Explorer windows.
        # Prototypes are declared so ctypes marshals the arguments correctly;
        # the result pointer is NULL because the reply is not needed (a
        # DWORD_PTR out-param would need an 8-byte buffer on Win64).
        send = ctypes.windll.user32.SendMessageTimeoutW
        send.argtypes = [
            ctypes.c_void_p,  # hWnd
            ctypes.c_uint,  # Msg
            ctypes.c_size_t,  # wParam
            ctypes.c_wchar_p,  # lParam
            ctypes.c_uint,  # fuFlags
            ctypes.c_uint,  # uTimeout
            ctypes.c_void_p,  # lpdwResult
        ]
        send.restype = ctypes.c_ssize_t
        send(0xFFFF, 0x001A, 0, "Shell", 0x0002, 2000, None)


def _menu_keys() -> list[str]:
    keys = [base for base, _, _, _ in _MENU_LOCATIONS]
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

    def write_verb(
        base_key: str, argument: str, verb_key: str = VERB_KEY, label: str = VERB_LABEL
    ) -> None:
        nonlocal created
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{base_key}\{verb_key}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f"{exe_text},0")
            # Multi-select opens a single window instead of one per file.
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Single")
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, rf"{base_key}\{verb_key}\command"
        ) as command:
            winreg.SetValueEx(command, "", 0, winreg.REG_SZ, f'"{exe_text}" "{argument}"')
        created += 1

    # Folders, folder background, desktop background and drives: each entry
    # names the folder action explicitly so it reads as "browse this folder".
    for base_key, argument, verb_key, label in _MENU_LOCATIONS:
        write_verb(base_key, argument, verb_key, label)

    # Media files. Registered in two layers:
    #   * SystemFileAssociations\<ext>\shell — always exists, but Explorer can
    #     collapse these into the extended ("Show more options") area.
    #   * The file's *current* ProgID under HKCU\Software\Classes — this is the
    #     same layer Honeyview uses, and it is what puts the entry level with
    #     "Open" in the menu the user actually sees.
    progids: set[str] = set()
    for extension in MEDIA_EXTENSIONS:
        write_verb(rf"Software\Classes\SystemFileAssociations\{extension}\shell", "%1")
        progids.update(_progids_for_extension(winreg, extension))
    for progid in sorted(progids):
        write_verb(rf"Software\Classes\{progid}\shell", "%1")

    # "Open with" candidate list.
    app_key = _APPLICATION_KEY
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key}\shell\open\command") as command:
        winreg.SetValueEx(command, "", 0, winreg.REG_SZ, f'"{exe_text}" "%1"')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key) as key:
        winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, FRIENDLY_NAME)
        winreg.SetValueEx(key, "DefaultIcon", 0, winreg.REG_SZ, f"{exe_text},0")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key}\SupportedTypes") as types:
        for extension in MEDIA_EXTENSIONS:
            winreg.SetValueEx(types, extension, 0, winreg.REG_SZ, "")
    created += 1

    _refresh_explorer()
    return created


def _progids_for_extension(winreg, extension: str) -> set[str]:
    """Return the ProgIDs currently associated with ``extension``.

    Covers both the machine default (HKCR\\<ext>) and the per-user choice
    (FileExts\\<ext>\\UserChoice), since either can own the right-click menu.
    Only ProgIDs that already exist under HKCU\\Software\\Classes are returned:
    writing there needs no admin rights, and skipping machine-only ProgIDs
    keeps the installer from silently failing on half its work.
    """
    progids: set[str] = set()

    def add(value) -> None:
        if isinstance(value, str) and value:
            progids.add(value)

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
            add(winreg.QueryValueEx(key, "")[0])
    except OSError:
        pass
    try:
        ext_key = (
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{extension}\UserChoice"
        )
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ext_key) as key:
            add(winreg.QueryValueEx(key, "ProgId")[0])
    except OSError:
        pass

    writable: set[str] = set()
    for progid in progids:
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}").Close()
        except OSError:
            continue
        writable.add(progid)
    return writable


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
        # Both verb keys: folders use CascadePicFolder, files use CascadePic.
        if delete_tree(rf"{base}\{VERB_KEY}"):
            removed += 1
        if delete_tree(rf"{base}\{FOLDER_VERB_KEY}"):
            removed += 1

    # ProgID-layer verbs (same layer install() writes).
    progids: set[str] = set()
    for extension in MEDIA_EXTENSIONS:
        progids.update(_progids_for_extension(winreg, extension))
    for progid in sorted(progids):
        if delete_tree(rf"Software\Classes\{progid}\shell\{VERB_KEY}"):
            removed += 1

    if delete_tree(_APPLICATION_KEY):
        removed += 1

    _refresh_explorer()
    return removed
