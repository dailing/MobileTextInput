"""
List all visible application windows and activate one by id.
Used by Panel to switch between windows. macOS: AppleScript; Windows: user32.
"""

import subprocess
from typing import List

from os_detector import os_detector

from loguru import logger

# Id separator for macOS (app + title); avoid characters likely in window titles
_ID_SEP = "\x1f"

if os_detector.is_windows:
    try:
        import ctypes
        from ctypes import wintypes
        _user32 = ctypes.windll.user32
        _kernel32 = ctypes.windll.kernel32
        _PROCESS_QUERY = 0x0400
        _PROCESS_VM_READ = 0x0010
        _SW_RESTORE = 9
        _WINDOWS_AVAILABLE = True
    except Exception:
        _user32 = _kernel32 = None
        _WINDOWS_AVAILABLE = False
else:
    _user32 = _kernel32 = None
    _WINDOWS_AVAILABLE = False


def list_windows() -> List[dict]:
    """
    Return list of visible windows. Each item: { "id": str, "title": str, "app": str? }.
    id is used for activate_window(id). On Windows id is hwnd; on macOS id is "app\\x1ftitle".
    """
    if os_detector.is_macos:
        return _list_windows_macos()
    if os_detector.is_windows and _WINDOWS_AVAILABLE:
        return _list_windows_windows()
    return []


def _list_windows_macos() -> List[dict]:
    logger.info("Listing macOS windows")
    script = """
    tell application "System Events"
        set lineList to {}
        repeat with p in (every process whose background only is false)
            try
                set pname to name of p
                repeat with w in (every window of p)
                    try
                        set wname to name of w
                        if wname is not "" then
                            set end of lineList to pname & "	" & wname
                        end if
                    end try
                end repeat
            end try
        end repeat
        set resultText to ""
        repeat with ln in lineList
            set resultText to resultText & ln & (ASCII character 10)
        end repeat
        return resultText
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            logger.warning(f"list_windows macOS osascript failed (code={result.returncode}) stderr: {err or '(none)'}")
            return []
        if not out:
            logger.warning(f"list_windows macOS osascript returned no output. stderr: {err or '(none)'}")
            return []
        windows = []
        for line in out.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Tab separates app and title
            parts = line.split("\t", 1)
            app_name = parts[0].strip() if parts else ""
            title = parts[1].strip() if len(parts) > 1 else ""
            if not title or title == "missing value":
                continue
            wid = f"{app_name}{_ID_SEP}{title}"
            windows.append({"id": wid, "title": title, "app": app_name})
        return windows
    except Exception as e:
        logger.warning("list_windows macOS failed: %s", e)
        return []


def _list_windows_windows() -> List[dict]:
    found = []

    def callback(hwnd, _):
        try:
            if _user32.IsWindowVisible(hwnd):
                length = _user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    _user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        found.append({"hwnd": hwnd, "title": title})
        except Exception:
            pass
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.c_void_p)
    _user32.EnumWindows(WNDENUMPROC(callback), None)
    return [{"id": str(w["hwnd"]), "title": w["title"], "app": None} for w in found]


def activate_window(window_id: str) -> bool:
    """Bring the window identified by window_id to front. Returns True if successful."""
    if not window_id:
        return False
    if os_detector.is_macos:
        return _activate_macos(window_id)
    if os_detector.is_windows and _WINDOWS_AVAILABLE:
        return _activate_windows(window_id)
    return False


def _activate_macos(window_id: str) -> bool:
    if _ID_SEP not in window_id:
        return False
    app_name, title = window_id.split(_ID_SEP, 1)
    esc_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set frontmost to true
            try
                set targetWindow to first window whose name is "{esc_title}"
                set index of targetWindow to 1
                return "ok"
            on error
                try
                    perform action "AXRaise" of targetWindow
                end try
                return "ok"
            end try
        end tell
    end tell
    '''
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and "error" not in (r.stderr or "").lower()
    except Exception as e:
        logger.warning(f"activate_window macOS failed: {e}")
        return False


def _activate_windows(window_id: str) -> bool:
    try:
        hwnd = int(window_id)
    except ValueError:
        return False
    try:
        if _user32.IsIconic(hwnd):
            _user32.ShowWindow(hwnd, _SW_RESTORE)
        _user32.SetForegroundWindow(hwnd)
        _user32.BringWindowToTop(hwnd)
        return True
    except Exception as e:
        logger.warning(f"activate_window Windows failed: {e}")
        return False


if __name__ == "__main__":
    for w in list_windows():
        print(w.get("id", ""), w.get("title", ""), w.get("app") or "", sep='###')
