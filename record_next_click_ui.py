import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import win32gui

from clipboard_util import find_window_by_title_hint, get_window_region

CONFIG_PATH = 'config.json'


def load_config():
    p = Path(CONFIG_PATH)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding='utf-8'))


def save_config(cfg):
    Path(CONFIG_PATH).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')


def get_own_window_rect(root):
    # Get the active foreground window; assume it's this Tk window
    hwnd = win32gui.GetForegroundWindow()
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    return {'left': left, 'top': top, 'width': max(1, right - left), 'height': max(1, bottom - top)}


def save_absolute(root):
    cfg = load_config()
    rect = get_own_window_rect(root)
    # use top-left as click point
    cfg['next_question_click'] = {'x': int(rect['left']), 'y': int(rect['top'])}
    save_config(cfg)
    messagebox.showinfo('已保存', f"已保存绝对坐标 x={cfg['next_question_click']['x']}, y={cfg['next_question_click']['y']}")


def save_relative(root):
    cfg = load_config()
    src_title = cfg.get('source_window_title')
    if not src_title:
        messagebox.showwarning('错误', 'config.json 未设置 source_window_title，无法保存相对坐标')
        return
    hwnd_src = find_window_by_title_hint(src_title, timeout=1.0)
    if not hwnd_src:
        messagebox.showwarning('错误', f'未找到源窗口: {src_title}，无法保存相对坐标')
        return
    src_region = get_window_region(hwnd_src)
    own_rect = get_own_window_rect(root)
    # use center of this window as target point
    cx = own_rect['left'] + own_rect['width'] / 2.0
    cy = own_rect['top'] + own_rect['height'] / 2.0
    try:
        rel_x = (cx - src_region['left']) / src_region['width']
        rel_y = (cy - src_region['top']) / src_region['height']
    except Exception:
        messagebox.showwarning('错误', '计算相对坐标失败')
        return
    rel_x = max(0.0, min(1.0, rel_x))
    rel_y = max(0.0, min(1.0, rel_y))
    cfg['next_question_click'] = {'rel_x': round(rel_x, 3), 'rel_y': round(rel_y, 3)}
    save_config(cfg)
    messagebox.showinfo('已保存', f"已保存相对坐标 rel_x={cfg['next_question_click']['rel_x']}, rel_y={cfg['next_question_click']['rel_y']}")


def main():
    root = tk.Tk()
    root.title('记录下一题坐标 — 拖到目标位置后点击保存')
    frm = tk.Frame(root, padx=12, pady=12)
    frm.pack()

    tk.Label(frm, text='把此窗口拖到目标位置（覆盖“下一题”按钮位置），然后选择保存方式。').pack(pady=(0,8))

    btn_abs = tk.Button(frm, text='保存为绝对坐标 (窗口左上)', width=36, command=lambda: save_absolute(root))
    btn_abs.pack(pady=4)
    btn_rel = tk.Button(frm, text='保存为相对坐标 (窗口中心 相对于 source_window)', width=36, command=lambda: save_relative(root))
    btn_rel.pack(pady=4)

    tk.Button(frm, text='退出', width=36, command=root.destroy).pack(pady=(8,0))

    root.mainloop()


if __name__ == '__main__':
    main()
