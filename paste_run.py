import argparse
import json
import time
import webbrowser
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
    parser.add_argument('--reuse-url', action='store_true', help='循环模式下只在开始时打开一次 URL 并复用该窗口')
    parser.add_argument('--dry-run', action='store_true', help='只执行到复制剪贴板并打印将要粘贴的目标（不实际粘贴）')
    parser.add_argument('--interval', type=int, default=10)
    args = parser.parse_args()

    cfg = json.loads(Path('config.json').read_text(encoding='utf-8'))
    screenshots_dir = Path('screenshots')
    ensure_dir(screenshots_dir)

    # If running in loop mode and reuse-url requested, we will open the configured URL once
    # but do it after the first screenshot is taken (so we don't steal focus before capture).
    opened_url = False

    def do_cycle():
        nonlocal opened_url
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_path = screenshots_dir / f'shot_{ts}.png'

        source_hwnd, capture_region = resolve_capture_region(cfg)
        capture_screenshot(str(img_path), capture_region)
        # Determine whether to open URL for this cycle. If loop+reuse-url, open once after first capture.
        cycle_open_url = cfg.get('url') if not (args.loop and args.reuse_url) else None
        # handle opening once-after-capture for reuse-url mode
        if args.loop and args.reuse_url and cfg.get('url') and not args.dry_run and not opened_url:
            # we will open the URL now, right after capturing the screenshot, so it won't affect the capture
            try:
                webbrowser.open_new(cfg.get('url'))
                time.sleep(cfg.get('delay_after_open', 3.0))
            except Exception:
                pass
            opened_url = True

        ok, msg = focus_and_paste(
            str(img_path),
            title_hint=cfg.get('target_window_title'),
            press_enter=cfg.get('press_enter_after_paste', False),
            open_url=cycle_open_url,
            delay_after_open=cfg.get('delay_after_open', 3.0),
            dry_run=args.dry_run,
        )
        if not ok:
            raise RuntimeError(msg)

        next_click = cfg.get('next_question_click')
        if source_hwnd:
            # try to refocus source window, with retries to make it more reliable
            ok_return = focus_window(source_hwnd)
            if not ok_return:
                for _ in range(6):
                    time.sleep(0.25)
                    ok_return = focus_window(source_hwnd)
                    if ok_return:
                        break
            time.sleep(cfg.get('delay_after_return', 0.3))
        # 支持绝对坐标 (x,y) 或 相对坐标 (rel_x, rel_y) 相对于 source 窗口
        if next_click:
            click_x = None
            click_y = None
            if next_click.get('x') is not None and next_click.get('y') is not None:
                click_x = int(next_click['x'])
                click_y = int(next_click['y'])
            elif next_click.get('rel_x') is not None and next_click.get('rel_y') is not None and capture_region:
                try:
                    rel_x = float(next_click.get('rel_x'))
                    rel_y = float(next_click.get('rel_y'))
                    click_x = int(capture_region['left'] + rel_x * capture_region['width'])
                    click_y = int(capture_region['top'] + rel_y * capture_region['height'])
                except Exception:
                    click_x = None
                    click_y = None
            if click_x is not None and click_y is not None:
                pyautogui.click(click_x, click_y)
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
