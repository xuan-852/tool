import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox


CONFIG_PATH = 'config.json'
SCRIPT = 'paste_run.py'


class PasteApp:
    def __init__(self, root):
        self.root = root
        root.title('Paste Run — 小应用')
        self.proc = None

        frm = tk.Frame(root, padx=8, pady=8)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(frm, text='目标窗口标题片段：').grid(row=0, column=0, sticky=tk.W)
        self.entry_title = tk.Entry(frm, width=36)
        self.entry_title.grid(row=0, column=1, sticky=tk.W)

        tk.Label(frm, text='自动打开网址：').grid(row=1, column=0, sticky=tk.W)
        self.entry_url = tk.Entry(frm, width=36)
        self.entry_url.grid(row=1, column=1, sticky=tk.W)

        tk.Label(frm, text='源界面标题片段：').grid(row=2, column=0, sticky=tk.W)
        self.entry_source_title = tk.Entry(frm, width=36)
        self.entry_source_title.grid(row=2, column=1, sticky=tk.W)

        self.use_region_var = tk.BooleanVar()
        tk.Checkbutton(frm, text='使用自定义截图区域', variable=self.use_region_var, command=self._toggle_region_fields).grid(row=3, column=1, sticky=tk.W)

        region_frm = tk.Frame(frm)
        region_frm.grid(row=4, column=1, sticky=tk.W)
        tk.Label(region_frm, text='左').grid(row=0, column=0, padx=(0, 4))
        self.entry_left = tk.Entry(region_frm, width=6)
        self.entry_left.grid(row=0, column=1, padx=(0, 8))
        tk.Label(region_frm, text='上').grid(row=0, column=2, padx=(0, 4))
        self.entry_top = tk.Entry(region_frm, width=6)
        self.entry_top.grid(row=0, column=3, padx=(0, 8))
        tk.Label(region_frm, text='宽').grid(row=0, column=4, padx=(0, 4))
        self.entry_width = tk.Entry(region_frm, width=6)
        self.entry_width.grid(row=0, column=5, padx=(0, 8))
        tk.Label(region_frm, text='高').grid(row=0, column=6, padx=(0, 4))
        self.entry_height = tk.Entry(region_frm, width=6)
        self.entry_height.grid(row=0, column=7)

        tk.Label(frm, text='下一题坐标（x, y）：').grid(row=5, column=0, sticky=tk.W)
        next_frm = tk.Frame(frm)
        next_frm.grid(row=5, column=1, sticky=tk.W)
        self.entry_next_x = tk.Entry(next_frm, width=8)
        self.entry_next_x.grid(row=0, column=0, padx=(0, 8))
        self.entry_next_y = tk.Entry(next_frm, width=8)
        self.entry_next_y.grid(row=0, column=1)

        self.press_enter_var = tk.BooleanVar()
        tk.Checkbutton(frm, text='粘贴后按 Enter', variable=self.press_enter_var).grid(row=6, column=1, sticky=tk.W)

        tk.Label(frm, text='模式：').grid(row=7, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value='once')
        tk.Radiobutton(frm, text='单次 (--once)', variable=self.mode_var, value='once').grid(row=7, column=1, sticky=tk.W)
        tk.Radiobutton(frm, text='循环 (--loop)', variable=self.mode_var, value='loop').grid(row=7, column=1, sticky=tk.E)

        tk.Label(frm, text='循环间隔（秒）：').grid(row=8, column=0, sticky=tk.W)
        self.entry_interval = tk.Entry(frm, width=10)
        self.entry_interval.insert(0, '10')
        self.entry_interval.grid(row=8, column=1, sticky=tk.W)

        btn_frm = tk.Frame(frm)
        btn_frm.grid(row=9, column=0, columnspan=2, pady=(8, 0))
        self.start_btn = tk.Button(btn_frm, text='Start', width=12, command=self.start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = tk.Button(btn_frm, text='Stop', width=12, command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        tk.Label(frm, text='日志：').grid(row=10, column=0, sticky=tk.W, pady=(8, 0))
        self.log = tk.Text(frm, height=12, width=72, state=tk.DISABLED)
        self.log.grid(row=11, column=0, columnspan=2, pady=(0, 8))

        # load defaults from config
        self.load_config()
        self._toggle_region_fields()

        root.protocol('WM_DELETE_WINDOW', self.on_close)

    def append_log(self, text: str):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + '\n')
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                cfg = json.load(open(CONFIG_PATH, 'r', encoding='utf-8'))
                self.entry_title.delete(0, tk.END)
                if cfg.get('target_window_title'):
                    self.entry_title.insert(0, cfg.get('target_window_title'))
                self.entry_url.delete(0, tk.END)
                if cfg.get('url'):
                    self.entry_url.insert(0, cfg.get('url'))
                self.entry_source_title.delete(0, tk.END)
                if cfg.get('source_window_title'):
                    self.entry_source_title.insert(0, cfg.get('source_window_title'))
                next_click = cfg.get('next_question_click') or {}
                self.entry_next_x.delete(0, tk.END)
                self.entry_next_y.delete(0, tk.END)
                if next_click.get('x') is not None:
                    self.entry_next_x.insert(0, str(next_click.get('x')))
                if next_click.get('y') is not None:
                    self.entry_next_y.insert(0, str(next_click.get('y')))
                region = cfg.get('screenshot_region')
                if region:
                    self.use_region_var.set(True)
                    self.entry_left.delete(0, tk.END)
                    self.entry_left.insert(0, str(region.get('left', '')))
                    self.entry_top.delete(0, tk.END)
                    self.entry_top.insert(0, str(region.get('top', '')))
                    self.entry_width.delete(0, tk.END)
                    self.entry_width.insert(0, str(region.get('width', '')))
                    self.entry_height.delete(0, tk.END)
                    self.entry_height.insert(0, str(region.get('height', '')))
                else:
                    self.use_region_var.set(False)
                self.press_enter_var.set(cfg.get('press_enter_after_paste', False))
            except Exception:
                pass

    def _toggle_region_fields(self):
        state = tk.NORMAL if self.use_region_var.get() else tk.DISABLED
        for entry in (self.entry_left, self.entry_top, self.entry_width, self.entry_height):
            entry.config(state=state)

    def _read_region(self):
        if not self.use_region_var.get():
            return None
        try:
            left = int(self.entry_left.get().strip())
            top = int(self.entry_top.get().strip())
            width = int(self.entry_width.get().strip())
            height = int(self.entry_height.get().strip())
            if width <= 0 or height <= 0:
                raise ValueError
        except Exception:
            raise ValueError('截图区域必须填写整数，且宽和高必须大于 0')
        return {'left': left, 'top': top, 'width': width, 'height': height}

    def save_config(self):
        cfg = {}
        if os.path.exists(CONFIG_PATH):
            try:
                cfg = json.load(open(CONFIG_PATH, 'r', encoding='utf-8'))
            except Exception:
                cfg = {}
        cfg['target_window_title'] = self.entry_title.get() or cfg.get('target_window_title')
        cfg['url'] = self.entry_url.get() or cfg.get('url')
        cfg['source_window_title'] = self.entry_source_title.get() or cfg.get('source_window_title')
        next_x = self.entry_next_x.get().strip()
        next_y = self.entry_next_y.get().strip()
        if next_x and next_y:
            try:
                cfg['next_question_click'] = {'x': int(next_x), 'y': int(next_y)}
            except Exception as exc:
                raise ValueError('下一题坐标必须填写整数') from exc
        else:
            cfg['next_question_click'] = None
        cfg['press_enter_after_paste'] = bool(self.press_enter_var.get())
        cfg['screenshot_region'] = self._read_region()
        cfg['paste_mode'] = True
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def start(self):
        if self.proc:
            messagebox.showinfo('提示', '任务已在运行中')
            return
        mode = self.mode_var.get()
        interval = self.entry_interval.get().strip()
        try:
            ival = int(interval)
            if ival <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror('错误', '间隔必须为正整数')
            return

        try:
            # save config
            self.save_config()
        except Exception as e:
            messagebox.showerror('错误', str(e))
            return

        args = [sys.executable, SCRIPT]
        if mode == 'once':
            args.append('--once')
        else:
            args.extend(['--loop', '--interval', str(ival)])

        try:
            self.append_log('启动: ' + ' '.join(args))
            # start subprocess and capture stdout/stderr
            self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            messagebox.showerror('错误', f'启动失败: {e}')
            self.proc = None
            return

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

        if mode == 'once':
            # for --once, wait and re-enable when done
            threading.Thread(target=self._wait_finish, daemon=True).start()

    def _read_stdout(self):
        if not self.proc or not self.proc.stdout:
            return
        for line in iter(self.proc.stdout.readline, ''):
            if not line:
                break
            self.append_log(line.rstrip())

    def _read_stderr(self):
        if not self.proc or not self.proc.stderr:
            return
        for line in iter(self.proc.stderr.readline, ''):
            if not line:
                break
            self.append_log('[ERR] ' + line.rstrip())

    def _wait_finish(self):
        if not self.proc:
            return
        self.proc.wait()
        self.append_log('进程已结束，退出码: ' + str(self.proc.returncode))
        self.proc = None
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def stop(self):
        if not self.proc:
            return
        try:
            self.append_log('正在停止...')
            self.proc.terminate()
            # wait a short while
            t0 = time.time()
            while self.proc.poll() is None and time.time() - t0 < 3:
                time.sleep(0.1)
            if self.proc.poll() is None:
                self.proc.kill()
        except Exception as e:
            self.append_log('停止时出错: ' + str(e))
        finally:
            self.proc = None
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.append_log('已停止')

    def on_close(self):
        if self.proc:
            if not messagebox.askyesno('确认', '有任务在运行，确定退出并停止它吗？'):
                return
            self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PasteApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
