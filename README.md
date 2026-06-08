自动刷题助手（打开豆包后自动把截图粘贴进去）

说明
- 该原型用于：截屏 -> 保存图片 -> 将图片写入 Windows 剪贴板 -> 自动打开豆包网址 -> 切换到目标窗口并模拟 `Ctrl+V` 粘贴。
- 请先确认目标网页支持从剪贴板粘贴图片（很多聊天窗口支持 Ctrl+V 直接粘贴图片）。

安装与准备（Windows）
1. 安装 Python 3.9+。
2. 在项目目录创建并激活虚拟环境，然后安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
```

运行
- 单次截屏并粘贴到目标窗口：

```powershell
python paste_run.py --once
```

- 循环模式（每隔若干秒截屏并粘贴）：

```powershell
python paste_run.py --loop --interval 10
```

配置
- 编辑 `config.json` 来设置 `source_window_title`（要截屏的源界面标题片段）、`target_window_title`（豆包窗口标题片段）、`next_question_click`（下一题按钮坐标），以及是否使用 OCR 等。
- 如果你想截某个界面本身，优先填 `source_window_title`，脚本会直接按该窗口范围截屏，然后再切回豆包粘贴，最后切回源界面点下一题。

注意
- 本工具仅供自学用途。请勿用于考试作弊或违反服务条款的场景。
