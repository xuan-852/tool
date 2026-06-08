import json
from pathlib import Path
from clipboard_util import find_window_by_title_hint, get_window_region


def main():
    cfg = json.loads(Path('config.json').read_text(encoding='utf-8'))
    next_click = cfg.get('next_question_click')
    source_hwnd = None
    capture_region = None
    if cfg.get('source_window_title'):
        source_hwnd = find_window_by_title_hint(cfg.get('source_window_title'), timeout=2.0)
        if source_hwnd:
            capture_region = get_window_region(source_hwnd)

    print('source_hwnd=', source_hwnd)
    print('capture_region=', capture_region)

    if not next_click:
        print('next_question_click not set in config.json')
        return

    if next_click.get('x') is not None and next_click.get('y') is not None:
        print('Using absolute coords:', next_click.get('x'), next_click.get('y'))
    elif next_click.get('rel_x') is not None and next_click.get('rel_y') is not None and capture_region:
        rel_x = float(next_click.get('rel_x'))
        rel_y = float(next_click.get('rel_y'))
        click_x = int(capture_region['left'] + rel_x * capture_region['width'])
        click_y = int(capture_region['top'] + rel_y * capture_region['height'])
        print('Computed absolute coords from rel_x/rel_y:', click_x, click_y)
    else:
        print('Insufficient data to compute click coords')


if __name__ == '__main__':
    main()
