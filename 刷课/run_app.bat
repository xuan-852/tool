@echo off
REM 一键运行 GUI（刷课工具），优先使用项目内 .venv，避免串到系统 Python
set "SCRIPT_DIR=%~dp0"
set "VENV_PYW=%SCRIPT_DIR%..\.venv\Scripts\pythonw.exe"
set "VENV_PY=%SCRIPT_DIR%..\.venv\Scripts\python.exe"
set "APP_PATH=%SCRIPT_DIR%code\app.py"

if exist "%VENV_PYW%" (
	start "" "%VENV_PYW%" "%APP_PATH%"
	exit /b 0
)

if exist "%VENV_PY%" (
	start "" "%VENV_PY%" "%APP_PATH%"
	exit /b 0
)

pythonw "%APP_PATH%"