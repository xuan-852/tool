import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import mss
from PIL import Image
import pyautogui

from clipboard_util import focus_and_paste, find_window_by_title_hint, focus_window, get_window_region


def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)


def capture_screenshot(path, region=None):
    with mss.mss() as sct:
        if region:
            monitor = region
        else:
            monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        img.save(path)


def resolve_capture_region(cfg):
    source_title = cfg.get('source_window_title')
    if source_title:
        source_hwnd = find_window_by_title_hint(source_title)
        if not source_hwnd:
            raise RuntimeError(f'源窗口未找到: {source_title}')
        return source_hwnd, get_window_region(source_hwnd)

    region = cfg.get('screenshot_region')
    return None, region


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--interval', type=int, default=10)
    args = parser.parse_args()

    cfg = json.loads(Path('config.json').read_text())
    screenshots_dir = Path('screenshots')
    ensure_dir(screenshots_dir)

    def do_cycle():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_path = screenshots_dir / f'shot_{ts}.png'

        source_hwnd, capture_region = resolve_capture_region(cfg)
        capture_screenshot(str(img_path), capture_region)
        ok, msg = focus_and_paste(
            str(img_path),
            title_hint=cfg.get('target_window_title'),
            press_enter=cfg.get('press_enter_after_paste', False),
            open_url=cfg.get('url'),
            delay_after_open=cfg.get('delay_after_open', 3.0),
        )
        if not ok:
            raise RuntimeError(msg)

        next_click = cfg.get('next_question_click')
        if source_hwnd:
            focus_window(source_hwnd)
            time.sleep(cfg.get('delay_after_return', 0.3))
        if next_click and next_click.get('x') is not None and next_click.get('y') is not None:
            pyautogui.click(int(next_click['x']), int(next_click['y']))
            time.sleep(cfg.get('delay_after_next_click', 0.3))
        # log
        log_path = Path('paste_results.csv')
        if not log_path.exists():
            log_path.write_text('timestamp,image,ok,msg\n')
        with log_path.open('a', encoding='utf-8') as f:
            f.write(f"{ts},{img_path.name},{ok},{msg}\n")
        print('cycle:', ok, msg)

    if args.once:
        do_cycle()
    elif args.loop:
        while True:
            do_cycle()
            time.sleep(args.interval)
    else:
        print('请选择 --once 或 --loop 来运行')


if __name__ == '__main__':
    main()
