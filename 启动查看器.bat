@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo 未找到项目虚拟环境，请先按照 README 安装依赖。
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m waterfall_viewer
