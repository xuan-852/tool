import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import mss
from PIL import Image
import pyautogui

BASE_DIR = Path(__file__).resolve().parent.parent
import win32gui

from clipboard_util import focus_and_paste, find_window_by_title_hint, ensure_foreground, get_window_region, open_url_in_new_window


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


def resolve_source_window(cfg, cached_hwnd=None):
    source_title = cfg.get('source_window_title')
    if not source_title:
        return None, None

    if cached_hwnd and win32gui.IsWindow(cached_hwnd) and win32gui.IsWindowVisible(cached_hwnd):
        # Keep using the originally captured hwnd even if the title changes.
        return cached_hwnd, get_window_region(cached_hwnd)

    source_hwnd = find_window_by_title_hint(source_title)
    if not source_hwnd:
        raise RuntimeError(f'源窗口未找到: {source_title}')
    return source_hwnd, get_window_region(source_hwnd)


def emit(message: str):
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # 控制台是 GBK 编码，无法处理零宽空格等字符，用 ? 替换
        enc = sys.stdout.encoding or 'utf-8'
        safe = message.encode(enc, errors='replace').decode(enc)
        print(safe, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--count', type=int, default=0, help='循环执行次数；0 表示无限循环')
    parser.add_argument('--reuse-url', action='store_true', help='循环模式下只在开始时打开一次 URL 并复用该窗口')
    parser.add_argument('--dry-run', action='store_true', help='只执行到复制剪贴板并打印将要粘贴的目标（不实际粘贴）')
    parser.add_argument('--interval', type=int, default=10)
    parser.add_argument('--batch', action='store_true', help='批量模式：先全部截图+下一题，完成后一次性粘贴所有截图到目标窗口')
    args = parser.parse_args()

    if args.count < 0:
        raise ValueError('--count 必须是非负整数')

    cfg = json.loads((BASE_DIR / 'config.json').read_text(encoding='utf-8'))
    screenshots_dir = BASE_DIR / 'screenshots'
    ensure_dir(screenshots_dir)

    # If running in loop mode and reuse-url requested, we will open the configured URL once
    # but do it after the first screenshot is taken (so we don't steal focus before capture).
    opened_url = False
    cached_source_hwnd = None
    batch_images = []  # 批量模式收集截图路径

    def do_cycle():
        nonlocal opened_url
        nonlocal cached_source_hwnd
        nonlocal batch_images
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_path = screenshots_dir / f'shot_{ts}.png'
        ok = True
        msg = ''

        source_hwnd, capture_region = resolve_source_window(cfg, cached_source_hwnd)
        cached_source_hwnd = source_hwnd
        if source_hwnd:
            emit(f'使用源窗口 hwnd={source_hwnd}, title={win32gui.GetWindowText(source_hwnd)}')
            ok_source = ensure_foreground(source_hwnd)
            if not ok_source:
                emit('警告：未能将源界面带到前台，截图可能不正确')
            capture_region = get_window_region(source_hwnd)
            time.sleep(cfg.get('delay_after_return', 0.3))
        emit('开始截图...')
        capture_screenshot(str(img_path), capture_region)

        # 批量模式：只收集截图，不粘贴也不打开网页
        if args.batch:
            batch_images.append(str(img_path))
            emit(f'已收集截图 ({len(batch_images)}/{args.count})')
        else:
            # 非批量模式：原有粘贴逻辑
            cycle_open_url = cfg.get('url') if not (args.loop and args.reuse_url) else None
            if args.loop and args.reuse_url and cfg.get('url') and not args.dry_run and not opened_url:
                try:
                    emit('已完成截图，正在打开目标网页...')
                    open_url_in_new_window(cfg.get('url'))
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

        # 点击下一题（批量和非批量都执行）
        next_click = cfg.get('next_question_click')
        if source_hwnd and not args.batch:
            emit('粘贴完成，正在切回源界面...')
            ok_return = ensure_foreground(source_hwnd)
            if not ok_return:
                emit('警告：未能确认源界面已回到前台')
            time.sleep(cfg.get('delay_after_return', 0.3))
            source_title_hint = cfg.get('source_window_title', '')
            for _ in range(6):
                cur_title = win32gui.GetWindowText(source_hwnd)
                if source_title_hint in cur_title:
                    break
                emit(f'当前标签页不是"{source_title_hint}"（标题="{cur_title}"），正在切换标签页...')
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                time.sleep(0.5)
            else:
                emit(f'警告：未能切换到包含"{source_title_hint}"的标签页')
        if next_click:
            click_x = None
            click_y = None
            if next_click.get('x') is not None and next_click.get('y') is not None:
                click_x = int(next_click['x'])
                click_y = int(next_click['y'])
                emit(f'点击下一题（绝对坐标）: x={click_x}, y={click_y}')
            elif next_click.get('rel_x') is not None and next_click.get('rel_y') is not None and capture_region:
                try:
                    rel_x = float(next_click.get('rel_x'))
                    rel_y = float(next_click.get('rel_y'))
                    click_x = int(capture_region['left'] + rel_x * capture_region['width'])
                    click_y = int(capture_region['top'] + rel_y * capture_region['height'])
                    emit(f'点击下一题（相对坐标 rel=({rel_x}, {rel_y}) → 绝对=({click_x}, {click_y}), region={capture_region}')
                except Exception as exc:
                    emit(f'计算相对坐标失败: {exc}')
                    click_x = None
                    click_y = None
            if click_x is not None and click_y is not None:
                pyautogui.click(click_x, click_y)
                emit(f'已点击 ({click_x}, {click_y})')
            else:
                emit('跳过点击：坐标计算无效')
            time.sleep(cfg.get('delay_after_next_click', 0.3))
        else:
            emit('未配置下一题坐标，跳过点击下一题')
        # log
        log_path = BASE_DIR / 'paste_results.csv'
        if not log_path.exists():
            log_path.write_text('timestamp,image,ok,msg\n')
        with log_path.open('a', encoding='utf-8') as f:
            f.write(f"{ts},{img_path.name},{ok if not args.batch else 'batch'},{msg if not args.batch else 'collected'}\n")
        print('cycle:', ok if not args.batch else 'batch', msg if not args.batch else 'collected')

    if args.once:
        do_cycle()
    elif args.loop:
        if args.count > 0:
            for index in range(args.count):
                do_cycle()
                if index < args.count - 1:
                    time.sleep(args.interval)
            # 批量模式：全部截图完成后，一次性上传到目标窗口
            if args.batch and batch_images:
                emit(f'\n所有截图已收集完毕（共 {len(batch_images)} 张），正在上传到目标窗口...')
                if cfg.get('url') and not args.dry_run:
                    emit('正在打开目标网页...')
                    open_url_in_new_window(cfg.get('url'))
                    time.sleep(cfg.get('delay_after_open', 3.0))
                for i, img_path in enumerate(batch_images):
                    emit(f'上传第 {i+1}/{len(batch_images)} 张: {Path(img_path).name}')
                    ok, msg = focus_and_paste(
                        img_path,
                        title_hint=cfg.get('target_window_title'),
                        press_enter=False,  # 全部上传完再统一发送
                        open_url=None,  # 已经打开了，不再重复打开
                        delay_after_open=cfg.get('delay_after_open', 3.0),
                        dry_run=args.dry_run or False,
                    )
                    if not ok:
                        emit(f'上传失败: {msg}')
                    else:
                        emit(f'第 {i+1} 张上传成功')
                    time.sleep(1)  # 每张之间留一点间隔
                # 全部粘贴完后按回车发送给智谱处理
                if not args.dry_run:
                    emit('全部上传完成，按回车发送给智谱处理...')
                    pyautogui.press('enter')
                emit('批量上传完成！')
        else:
            while True:
                do_cycle()
                time.sleep(args.interval)
    else:
        print('请选择 --once 或 --loop 来运行')


if __name__ == '__main__':
    main()
