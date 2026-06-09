import io
import shutil
import subprocess
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


def open_url_in_new_window(url: str):
    browser_candidates = [
        shutil.which('msedge'),
        shutil.which('msedge.exe'),
        shutil.which('chrome'),
        shutil.which('chrome.exe'),
    ]
    for browser in browser_candidates:
        if browser:
            try:
                subprocess.Popen([browser, '--new-window', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                continue
    webbrowser.open_new(url)
    return True


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
        # Only restore when minimized; otherwise keep the current size/state.
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def ensure_foreground(hwnd: int, retries: int = 8, delay: float = 0.25):
    for _ in range(retries):
        if not win32gui.IsWindow(hwnd):
            return False
        if focus_window(hwnd):
            try:
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
            except Exception:
                pass
        time.sleep(delay)
    return False


def get_window_region(hwnd: int):
    # 使用客户区（Client Area），去掉标题栏和阴影边框，只截取网页实际内容
    client_rect = win32gui.GetClientRect(hwnd)  # (left=0, top=0, right=width, bottom=height)
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))
    return {
        'left': left,
        'top': top,
        'width': max(1, client_rect[2]),
        'height': max(1, client_rect[3]),
    }


def focus_and_paste(
    image_path: str,
    title_hint: str = None,
    press_enter: bool = False,
    open_url: str = None,
    delay_after_open: float = 3.0,
    delay_after_focus: float = 0.3,
    dry_run: bool = False,
):
    copy_image_to_clipboard(image_path)
    if dry_run:
        # 在干跑模式下仅复制到剪贴板并返回将要粘贴的目标信息，便于调试
        hwnd = find_window_by_title_hint(title_hint)
        if hwnd:
            return True, f'dry-run: copied to clipboard, target hwnd={hwnd}'
        else:
            return True, f'dry-run: copied to clipboard, target hint="{title_hint or ''}" (not found; would fallback to browser)'

    if open_url:
        open_url_in_new_window(open_url)
        time.sleep(delay_after_open)
    hwnd = find_window_by_title_hint(title_hint)
    if not hwnd:
        return False, 'target window not found'
    ok = focus_window(hwnd)
    if not ok:
        # retry a few times: re-find the window and try again
        for _ in range(5):
            time.sleep(0.3)
            hwnd = find_window_by_title_hint(title_hint, timeout=0.5)
            if hwnd and focus_window(hwnd):
                ok = True
                break
        if not ok:
            return False, 'cannot focus window'
    time.sleep(delay_after_focus)
    # 如果目标窗口的当前标签页不匹配标题，用 Ctrl+Tab 向前翻找到正确标签页
    if title_hint:
        for _ in range(8):
            cur_title = win32gui.GetWindowText(hwnd)
            if title_hint in cur_title:
                break
            pyautogui.hotkey('ctrl', 'tab')
            time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    if press_enter:
        pyautogui.press('enter')
    return True, 'pasted'
