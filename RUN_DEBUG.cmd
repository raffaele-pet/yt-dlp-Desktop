@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Local environment not found: %PYTHON_EXE%
    echo Run INSTALL.bat first.
    pause
    exit /b 1
)

"%PYTHON_EXE%" app.py

if errorlevel 1 (
    echo.
    echo The application exited with an error.
    pause
)
