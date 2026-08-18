@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python virtual environment was not found.
    echo Expected: "%PYTHON_EXE%"
    pause
    exit /b 1
)

pushd "%PROJECT_DIR%"
"%PYTHON_EXE%" -m waterfall_viewer
set "APP_EXIT_CODE=%ERRORLEVEL%"
popd

if not "%APP_EXIT_CODE%"=="0" (
    echo.
    echo Application exited with code %APP_EXIT_CODE%.
    pause
)

exit /b %APP_EXIT_CODE%
