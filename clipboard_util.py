import io
import time
import webbrowser
from PIL import Image
import win32clipboard
import win32con
import win32gui
import win32process
import psutil
import pyautogui


def copy_image_to_clipboard(image_path: str):
    """Copy an image file to Windows clipboard as DIB."""
    image = Image.open(image_path)
    output = io.BytesIO()
    # BMP with Windows header; we must strip the first 14 bytes
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    output.close()
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def _enum_windows():
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows.append(hwnd)
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def find_window_by_title_hint(title_hint: str = None, timeout: float = 5.0):
    """Find window handle matching title hint or msedge process. Returns hwnd or None."""
    end = time.time() + timeout
    while time.time() < end:
        for hwnd in _enum_windows():
            title = win32gui.GetWindowText(hwnd)
            if title_hint and title_hint in title:
                return hwnd
        # fallback: find msedge window
        for hwnd in _enum_windows():
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                p = psutil.Process(pid)
                name = p.name().lower()
                if 'msedge' in name or 'chrome' in name:
                    return hwnd
            except Exception:
                continue
        time.sleep(0.2)
    return None


def focus_window(hwnd: int):
    try:
        # restore and bring to foreground
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def get_window_region(hwnd: int):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return {
        'left': left,
        'top': top,
        'width': max(1, right - left),
        'height': max(1, bottom - top),
    }


def focus_and_paste(
    image_path: str,
    title_hint: str = None,
    press_enter: bool = False,
    open_url: str = None,
    delay_after_open: float = 3.0,
    delay_after_focus: float = 0.3,
):
    copy_image_to_clipboard(image_path)
    if open_url:
        webbrowser.open_new(open_url)
        time.sleep(delay_after_open)
    hwnd = find_window_by_title_hint(title_hint)
    if not hwnd:
        return False, 'target window not found'
    ok = focus_window(hwnd)
    if not ok:
        return False, 'cannot focus window'
    time.sleep(delay_after_focus)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    if press_enter:
        pyautogui.press('enter')
    return True, 'pasted'
