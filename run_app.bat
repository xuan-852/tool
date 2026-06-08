@echo off
REM 一键运行 GUI，优先使用项目内 .venv，避免串到系统 Python
set "SCRIPT_DIR=%~dp0"
set "VENV_PYW=%SCRIPT_DIR%.venv\Scripts\pythonw.exe"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

if exist "%VENV_PYW%" (
	start "" "%VENV_PYW%" "%SCRIPT_DIR%app.py"
	exit /b 0
)

if exist "%VENV_PY%" (
	start "" "%VENV_PY%" "%SCRIPT_DIR%app.py"
	exit /b 0
)

pythonw "%SCRIPT_DIR%app.py"