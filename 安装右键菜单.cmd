@echo off
chcp 65001 >nul
setlocal
set "SCRIPT="
if exist "%~dp0context_menu\install_context_menu.ps1" set "SCRIPT=%~dp0context_menu\install_context_menu.ps1"
if not defined SCRIPT if exist "%~dp0packaging\context_menu\install_context_menu.ps1" set "SCRIPT=%~dp0packaging\context_menu\install_context_menu.ps1"
if not defined SCRIPT (
    echo [ERROR] install_context_menu.ps1 not found.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
echo.
pause
