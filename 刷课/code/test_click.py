"""测试点击坐标：截图并标记当前配置的点击位置。"""
import json
import sys
from pathlib import Path

import mss
from PIL import Image, ImageDraw
import win32gui
import pyautogui

from clipboard_util import find_window_by_title_hint, get_window_region

BASE_DIR = Path(__file__).resolve().parent.parent
cfg = json.loads((BASE_DIR / 'config.json').read_text(encoding='utf-8'))

src_title = cfg.get('source_window_title', '智慧树')
hwnd = find_window_by_title_hint(src_title, timeout=3.0)
if not hwnd:
    print(f'未找到源窗口: {src_title}')
    sys.exit(1)

title = win32gui.GetWindowText(hwnd)
print(f'源窗口: hwnd={hwnd}, title="{title}"')

region = get_window_region(hwnd)
print(f'客户区: left={region["left"]}, top={region["top"]}, '
      f'width={region["width"]}, height={region["height"]}')

next_click = cfg.get('next_question_click', {})
rel_x = next_click.get('rel_x') or 0
rel_y = next_click.get('rel_y') or 0
abs_x = int(region['left'] + rel_x * region['width'])
abs_y = int(region['top'] + rel_y * region['height'])
print(f'相对坐标 ({rel_x}, {rel_y}) → 绝对坐标 ({abs_x}, {abs_y})')

# 截图全屏并标记
with mss.mss() as sct:
    full = sct.grab(sct.monitors[0])
    img = Image.frombytes('RGB', full.size, full.rgb)
    draw = ImageDraw.Draw(img)

    # 客户区边框（绿色）
    draw.rectangle(
        [region['left'], region['top'],
         region['left']+region['width'], region['top']+region['height']],
        outline='lime', width=3
    )
    # 点击点（红色大圈）
    r = 40
    draw.ellipse([abs_x-r, abs_y-r, abs_x+r, abs_y+r], outline='red', width=4)
    draw.text((abs_x+10, abs_y+10), f'点击坐标\n({abs_x},{abs_y})', fill='red')

    out = BASE_DIR / 'screenshots' / 'click_test.png'
    img.save(str(out))
    print(f'\n已保存截图: {out}（绿框=客户区，红圈=点击位置）')

print('即将移动鼠标到点击位置...')
input('按 Enter 移动鼠标...')
pyautogui.moveTo(abs_x, abs_y, duration=0.5)
print(f'鼠标在 ({abs_x}, {abs_y}) — 看是否对准了"下一题"按钮')
