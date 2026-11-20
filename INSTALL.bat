@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title yt-dlp Desktop - Installation and updates
color 0F

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR_NO_SLASH=%~dp0"
if "%PROJECT_DIR_NO_SLASH:~-1%"=="\" set "PROJECT_DIR_NO_SLASH=%PROJECT_DIR_NO_SLASH:~0,-1%"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYW=%VENV_DIR%\Scripts\pythonw.exe"
set "VENV_YTDLP=%VENV_DIR%\Scripts\yt-dlp.exe"
set "LINKS_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "FFMPEG_EXE=%LINKS_DIR%\ffmpeg.exe"
set "DENO_EXE=%LINKS_DIR%\deno.exe"
set "PATH=%LINKS_DIR%;%PATH%"
set "CHECK_ONLY=0"
set "FROM_SETUP=0"
if /I "%~1"=="--check" set "CHECK_ONLY=1"
if /I "%~1"=="--setup" set "FROM_SETUP=1"

echo ================================================================
echo                   yt-dlp Desktop INSTALLER
echo ================================================================
echo Project folder: %PROJECT_DIR_NO_SLASH%
echo.

if not exist "%PROJECT_DIR%app.py" (
    call :fatal "app.py is missing from the project folder."
    exit /b 1
)
if not exist "%PROJECT_DIR%RUN.vbs" (
    call :fatal "RUN.vbs is missing from the project folder."
    exit /b 1
)
if not exist "%PROJECT_DIR%requirements.txt" (
    call :fatal "requirements.txt is missing from the project folder."
    exit /b 1
)
if not exist "%PROJECT_DIR%assets\desktop.png" (
    call :fatal "The application PNG icon is missing."
    exit /b 1
)
if not exist "%PROJECT_DIR%assets\desktop.ico" (
    call :fatal "The application Windows icon is missing."
    exit /b 1
)

call :find_python
call :check_venv
call :check_ffmpeg
call :check_deno

if "%CHECK_ONLY%"=="1" (
    call :print_status
    if "!PYTHON_OK!!VENV_OK!!YTDLP_OK!!FFMPEG_OK!!DENO_OK!"=="11111" exit /b 0
    exit /b 2
)

where winget.exe >nul 2>&1
if errorlevel 1 (
    call :fatal "WinGet is not available. Install App Installer from the Microsoft Store and try again."
    exit /b 1
)

echo [1/6] Checking Python...
if "!PYTHON_OK!"=="0" (
    echo [INSTALL] Python 3.13: no compatible Python version was found.
    set "PYTHON_INSTALL_MODE="
    if "%FROM_SETUP%"=="1" set "PYTHON_INSTALL_MODE=--silent"
    winget install --id "Python.Python.3.13" --exact --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity !PYTHON_INSTALL_MODE!
    if errorlevel 1 (
        call :fatal "Python 3.13 installation failed."
        exit /b 1
    )
    call :find_python
)
if "!PYTHON_OK!"=="0" (
    call :fatal "Python 3.11 or later was not found after installation."
    exit /b 1
)
echo [OK] Using !PYTHON_VERSION!: !PYTHON_EXE!
echo      The installer will reuse your system Python without upgrading it.

echo.
echo [2/6] Preparing the isolated .venv environment...
if exist "%VENV_DIR%" if "!VENV_OK!"=="0" (
    echo [REPAIR] The existing local environment is invalid and will be recreated.
    rmdir /s /q "%VENV_DIR%"
)
if not exist "%VENV_PY%" (
    "!PYTHON_EXE!" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        call :fatal "Could not create the .venv environment."
        exit /b 1
    )
) else (
    echo [OK] The .venv environment already exists.
)
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
if errorlevel 1 (
    call :fatal "Could not update the .venv packaging tools."
    exit /b 1
)

echo.
echo [3/6] Checking and updating yt-dlp in .venv...
set "YTDLP_BEFORE=not installed"
if exist "%VENV_YTDLP%" for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_BEFORE=%%V"
echo Installed version: !YTDLP_BEFORE!
echo Checking the latest official stable release...
"%VENV_PY%" -m pip install --disable-pip-version-check --upgrade -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (
    call :fatal "Could not install or update yt-dlp in .venv."
    exit /b 1
)
set "YTDLP_AFTER=not available"
for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_AFTER=%%V"
if "!YTDLP_BEFORE!"=="!YTDLP_AFTER!" (
    echo [OK] yt-dlp !YTDLP_AFTER! is already up to date.
) else (
    echo [UPDATED] yt-dlp !YTDLP_BEFORE! --^> !YTDLP_AFTER!
)

echo.
echo [4/6] Checking FFmpeg and Deno...
call :check_ffmpeg
if "!FFMPEG_OK!"=="0" (
    call :install_package "yt-dlp.FFmpeg" "FFmpeg for yt-dlp"
    if errorlevel 1 exit /b 1
) else (
    echo [OK] FFmpeg is already available.
    if "%FROM_SETUP%"=="0" call :upgrade_if_managed "yt-dlp.FFmpeg" "FFmpeg for yt-dlp"
    if errorlevel 1 exit /b 1
)
call :check_deno
if "!DENO_OK!"=="0" (
    call :install_package "DenoLand.Deno" "Deno"
    if errorlevel 1 exit /b 1
) else (
    echo [OK] Deno is already available.
    if "%FROM_SETUP%"=="0" call :upgrade_if_managed "DenoLand.Deno" "Deno"
    if errorlevel 1 exit /b 1
)
call :ensure_user_path "%LINKS_DIR%"
if errorlevel 1 (
    call :fatal "Could not update the user PATH for WinGet."
    exit /b 1
)
call :check_ffmpeg
call :check_deno
if exist "!FFMPEG_EXE!" for %%D in ("!FFMPEG_EXE!") do (
    call :ensure_user_path "%%~dpD"
    set "PATH=%%~dpD;!PATH!"
)
if exist "!DENO_EXE!" for %%D in ("!DENO_EXE!") do (
    call :ensure_user_path "%%~dpD"
    set "PATH=%%~dpD;!PATH!"
)

echo.
echo [5/6] Final verification...
call :find_python
call :check_venv
call :check_ffmpeg
call :check_deno
call :print_status
if not "!PYTHON_OK!!VENV_OK!!YTDLP_OK!!FFMPEG_OK!!DENO_OK!"=="11111" (
    call :fatal "Final verification failed. Check the messages above."
    exit /b 1
)
"%VENV_PY%" -m py_compile "%PROJECT_DIR%app.py"
if errorlevel 1 (
    call :fatal "app.py contains a syntax error."
    exit /b 1
)
"%VENV_YTDLP%" --ignore-config --plugin-dirs "%PROJECT_DIR%plugins" --use-postprocessor DesktopCompatible:when=post_process --list-extractors >nul 2>&1
if errorlevel 1 (
    call :fatal "The video compatibility postprocessor could not be loaded."
    exit /b 1
)

if "%FROM_SETUP%"=="1" exit /b 0

echo.
echo [6/6] Creating the desktop shortcut...
set "YT_DLP_PROJECT=%PROJECT_DIR_NO_SLASH%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$project=$env:YT_DLP_PROJECT; $desktop=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject WScript.Shell; $link=Join-Path $desktop 'yt-dlp Desktop.lnk'; $old=Join-Path $desktop 'YT-DLP.lnk'; if((Test-Path -LiteralPath $old) -and -not (Test-Path -LiteralPath $link)){ $previous=$shell.CreateShortcut($old); if($previous.WorkingDirectory.TrimEnd('\') -ieq $project.TrimEnd('\')){Move-Item -LiteralPath $old -Destination $link} }; $shortcut=$shell.CreateShortcut($link); $shortcut.TargetPath=(Join-Path $env:WINDIR 'System32\wscript.exe'); $shortcut.Arguments=([char]34)+(Join-Path $project 'RUN.vbs')+([char]34); $shortcut.WorkingDirectory=$project; $shortcut.Description='Launch yt-dlp Desktop'; $shortcut.IconLocation=(Join-Path $project 'assets\desktop.ico')+',0'; $shortcut.Save()"
if errorlevel 1 (
    call :fatal "Could not create the desktop shortcut."
    exit /b 1
)
echo [OK] yt-dlp Desktop shortcut created on the desktop.

echo.
echo ================================================================
echo INSTALLATION COMPLETED SUCCESSFULLY
echo ================================================================
echo.

choice /C YN /N /M "Launch yt-dlp Desktop now? [Y/N]: "
if errorlevel 2 goto :finish
start "" "%WINDIR%\System32\wscript.exe" "%PROJECT_DIR%RUN.vbs"

:finish
echo.
echo Press any key to close this window.
pause >nul
exit /b 0


:find_python
set "PYTHON_OK=0"
set "PYTHON_EXE="
set "PYTHON_VERSION=not available"
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" call :try_python "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
exit /b 0


:try_python
if defined PYTHON_EXE exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYTHON_EXE=%~1"
set "PYTHON_OK=1"
for /f "delims=" %%V in ('"%~1" --version 2^>^&1') do set "PYTHON_VERSION=%%V"
exit /b 0


:check_venv
set "VENV_OK=0"
set "YTDLP_OK=0"
set "YTDLP_VERSION=not available"
if exist "%VENV_PY%" if exist "%VENV_PYW%" (
    "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)
if "!VENV_OK!"=="1" if exist "%VENV_YTDLP%" (
    for /f "delims=" %%V in ('"%VENV_YTDLP%" --version 2^>nul') do set "YTDLP_VERSION=%%V"
    "%VENV_YTDLP%" --version >nul 2>&1
    if not errorlevel 1 set "YTDLP_OK=1"
)
exit /b 0


:check_ffmpeg
set "FFMPEG_OK=0"
call :try_ffmpeg "%FFMPEG_EXE%"
if "!FFMPEG_OK!"=="0" for /f "delims=" %%P in ('where ffmpeg.exe 2^>nul') do call :try_ffmpeg "%%P"
if "!FFMPEG_OK!"=="0" for /f "delims=" %%P in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" ffmpeg.exe 2^>nul') do call :try_ffmpeg "%%P"
exit /b 0


:try_ffmpeg
if "!FFMPEG_OK!"=="1" exit /b 0
if not exist "%~1" exit /b 0
if not exist "%~dp1ffprobe.exe" exit /b 0
"%~dp1ffprobe.exe" -version >nul 2>&1
if errorlevel 1 exit /b 0
"%~1" -hide_banner -encoders 2>nul | findstr.exe /C:" libx264 " >nul
if errorlevel 1 exit /b 0
set "FFMPEG_EXE=%~1"
set "FFMPEG_OK=1"
exit /b 0


:check_deno
set "DENO_OK=0"
if exist "%DENO_EXE%" (
    "%DENO_EXE%" --version >nul 2>&1
    if not errorlevel 1 set "DENO_OK=1"
) else (
    deno --version >nul 2>&1
    if not errorlevel 1 set "DENO_OK=1"
)
if "!DENO_OK!"=="0" for /f "delims=" %%P in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" deno.exe 2^>nul') do if "!DENO_OK!"=="0" (
    "%%P" --version >nul 2>&1
    if not errorlevel 1 (
        set "DENO_EXE=%%P"
        set "DENO_OK=1"
    )
)
exit /b 0


:print_status
if "!PYTHON_OK!"=="1" (echo   [OK] !PYTHON_VERSION! system installation) else (echo   [MISSING] Python 3.11 or later)
if "!VENV_OK!"=="1" (echo   [OK] Local .venv environment) else (echo   [MISSING] Local .venv environment)
if "!YTDLP_OK!"=="1" (echo   [OK] yt-dlp !YTDLP_VERSION! in .venv) else (echo   [MISSING] yt-dlp in .venv)
if "!FFMPEG_OK!"=="1" (echo   [OK] FFmpeg with H.264 encoding and FFprobe) else (echo   [MISSING] FFmpeg with H.264 encoding and FFprobe)
if "!DENO_OK!"=="1" (echo   [OK] Deno) else (echo   [MISSING] Deno)
exit /b 0


:install_package
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
echo.
echo ----------------------------------------------------------------
echo [INSTALL] !PACKAGE_NAME!
echo ----------------------------------------------------------------
winget install --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent
if errorlevel 1 (
    call :fatal "Could not install !PACKAGE_NAME!."
    exit /b 1
)
echo [OK] !PACKAGE_NAME! installed.
exit /b 0


:upgrade_if_managed
set "PACKAGE_ID=%~1"
set "PACKAGE_NAME=%~2"
winget list --id "!PACKAGE_ID!" --exact --accept-source-agreements --disable-interactivity >nul 2>&1
if errorlevel 1 exit /b 0
winget upgrade --id "!PACKAGE_ID!" --exact --accept-package-agreements --accept-source-agreements --disable-interactivity --silent >nul 2>&1
set "UPDATE_EXIT=!errorlevel!"
if "!UPDATE_EXIT!"=="0" exit /b 0
if "!UPDATE_EXIT!"=="-1978335189" exit /b 0
call :fatal "Could not check or update !PACKAGE_NAME!. Exit code !UPDATE_EXIT!."
exit /b 1


:ensure_user_path
set "PATH_TO_ADD=%~1"
set "YT_DLP_PATH_TO_ADD=%PATH_TO_ADD%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$dir=$env:YT_DLP_PATH_TO_ADD.TrimEnd('\'); $current=[Environment]::GetEnvironmentVariable('Path','User'); $entries=if($current){$current -split ';'}else{@()}; if(-not ($entries | Where-Object { $_.Trim().TrimEnd('\') -ieq $dir })){[Environment]::SetEnvironmentVariable('Path',(($dir+';'+$current).TrimEnd(';')),'User')}"
exit /b %errorlevel%


:fatal
echo.
echo ================================================================
echo [ERROR] %~1
echo ================================================================
if "%CHECK_ONLY%"=="1" exit /b 1
if "%FROM_SETUP%"=="1" exit /b 1
echo Press any key to close this window.
pause >nul
exit /b 1
