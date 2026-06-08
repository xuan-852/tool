import json
from pathlib import Path
import pyautogui

from clipboard_util import find_window_by_title_hint, get_window_region

CONFIG_PATH = 'config.json'


def main():
    cfg_path = Path(CONFIG_PATH)
    if not cfg_path.exists():
        print('未找到 config.json')
        return
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))

    print('当前 source_window_title:', cfg.get('source_window_title'))
    choice = input('选择保存方式：1=绝对坐标 (x,y)  2=相对坐标 (rel_x,rel_y) [默认2]: ').strip()
    if choice not in ('1', '2', ''):
        choice = '2'
    print('请将鼠标移动到“下一题”按钮位置，然后按 Enter 保存坐标...')
    input()
    x, y = pyautogui.position()
    print(f'捕获到位置: x={x}, y={y}')

    if choice == '1':
        cfg['next_question_click'] = {'x': int(x), 'y': int(y)}
    else:
        src = cfg.get('source_window_title')
        if src:
            hwnd = find_window_by_title_hint(src, timeout=2.0)
            if hwnd:
                region = get_window_region(hwnd)
                try:
                    rel_x = (x - region['left']) / region['width']
                    rel_y = (y - region['top']) / region['height']
                    rel_x = max(0.0, min(1.0, rel_x))
                    rel_y = max(0.0, min(1.0, rel_y))
                    cfg['next_question_click'] = {'rel_x': round(rel_x, 3), 'rel_y': round(rel_y, 3)}
                    print(f'计算到相对坐标 rel_x={cfg["next_question_click"]["rel_x"]}, rel_y={cfg["next_question_click"]["rel_y"]}')
                except Exception:
                    print('计算相对坐标失败，保存为绝对坐标')
                    cfg['next_question_click'] = {'x': int(x), 'y': int(y)}
            else:
                print('未找到源窗口，保存为绝对坐标')
                cfg['next_question_click'] = {'x': int(x), 'y': int(y)}
        else:
            print('配置中未设置 source_window_title，保存为绝对坐标')
            cfg['next_question_click'] = {'x': int(x), 'y': int(y)}

    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    print('已将 next_question_click 写入', CONFIG_PATH)


if __name__ == '__main__':
    main()
