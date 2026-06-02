@echo off
setlocal enabledelayedexpansion

:: Configuration
set REPO_URL=https://github.com/Pasdemain/forex-backtest-app.git
set PROJECT_NAME=forex-backtest-app
set PYTHON_EXE=python

:: Colors for output
set GREEN=[32m
set RED=[31m
set YELLOW=[33m
set BLUE=[34m
set NC=[0m

echo %GREEN%=== Forex Backtest App Launcher (Enhanced) ===%NC%
echo %BLUE%This script will automatically install missing dependencies%NC%
echo.

:: Check if Python is installed, install if not
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Python not found. Installing Python...%NC%
   
    :: Download and install Python silently
    echo Downloading Python installer...
    powershell -Command "& {try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe' -OutFile 'python-installer.exe' } catch { exit 1 }}"
   
    if exist "python-installer.exe" (
        echo Installing Python...
        python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
       
        :: Wait for installation
        timeout /t 20 /nobreak >nul
       
        :: Refresh environment variables
        for /f "tokens=2*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set "sys_path=%%b"
        for /f "tokens=2*" %%a in ('reg query "HKEY_CURRENT_USER\Environment" /v PATH 2^>nul') do set "user_path=%%b"
       
        if defined user_path (
            set "PATH=%sys_path%;%user_path%"
        ) else (
            set "PATH=%sys_path%"
        )
       
        :: Clean up installer
        del python-installer.exe
       
        echo %GREEN%Python installed successfully%NC%
       
        :: Verify installation
        %PYTHON_EXE% --version >nul 2>&1
        if errorlevel 1 (
            echo %RED%Python installation may need a system restart%NC%
            echo Please restart your computer and run this script again
            pause
            exit /b 1
        )
    ) else (
        echo %RED%Failed to download Python installer%NC%
        echo Please install Python manually from https://python.org
        pause
        exit /b 1
    )
)

:: Check if Git is installed, install if not
git --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Git not found. Installing Git...%NC%
   
    :: Download and install Git silently
    echo Downloading Git installer...
    powershell -Command "& {try { Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe' -OutFile 'git-installer.exe' } catch { exit 1 }}"
   
    if exist "git-installer.exe" (
        echo Installing Git...
        git-installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
       
        :: Wait for installation to complete
        timeout /t 15 /nobreak >nul
       
        :: Refresh PATH for Git
        for /f "tokens=2*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set "sys_path=%%b"
        set "PATH=%sys_path%;C:\Program Files\Git\cmd"
       
        :: Clean up installer
        del git-installer.exe
       
        echo %GREEN%Git installed successfully%NC%
       
        :: Verify Git installation
        git --version >nul 2>&1
        if errorlevel 1 (
            echo %YELLOW%Git installed but not yet in PATH. Trying alternative location...%NC%
            set "PATH=%PATH%;C:\Program Files\Git\bin;C:\Program Files (x86)\Git\cmd;C:\Program Files (x86)\Git\bin"
            git --version >nul 2>&1
            if errorlevel 1 (
                echo %RED%Git installation requires a restart%NC%
                echo Please restart your computer and run this script again
                pause
                exit /b 1
            )
        )
    ) else (
        echo %RED%Failed to download Git installer%NC%
        echo Please install Git manually from https://git-scm.com/download/win
        pause
        exit /b 1
    )
)

:: Get current directory
set CURRENT_DIR=%cd%
echo Current directory: %CURRENT_DIR%

:: Check if repository already exists
if exist "%PROJECT_NAME%" (
    echo %YELLOW%Repository already exists. Updating...%NC%
    cd "%PROJECT_NAME%"
    git pull origin main
    if errorlevel 1 (
        echo %RED%Warning: Could not update repository. Continuing with existing version...%NC%
    )
) else (
    echo %YELLOW%Cloning repository...%NC%
    git clone %REPO_URL%
    if errorlevel 1 (
        echo %RED%Error: Failed to clone repository%NC%
        echo Please check your internet connection
        pause
        exit /b 1
    )
    cd "%PROJECT_NAME%"
)

:: Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo %YELLOW%Virtual environment found. Activating...%NC%
    call venv\Scripts\activate.bat
) else (
    echo %YELLOW%Creating virtual environment...%NC%
    %PYTHON_EXE% -m venv venv
    if errorlevel 1 (
        echo %RED%Error: Failed to create virtual environment%NC%
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
)

:: Upgrade pip first
echo %YELLOW%Upgrading pip...%NC%
python -m pip install --upgrade pip

:: Check if requirements are installed
python -c "import MetaTrader5, pandas, numpy, matplotlib" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Installing dependencies...%NC%
    echo This may take a few minutes...
   
    :: Install packages individually for better error handling
    pip install MetaTrader5>=5.0.45
    pip install pandas>=2.1.0
    pip install numpy>=1.25.0
    pip install pytz>=2023.3
    pip install tkcalendar>=1.6.1
    pip install matplotlib>=3.7.0
    pip install openpyxl>=3.1.2
   
    if errorlevel 1 (
        echo %RED%Error: Failed to install some dependencies%NC%
        echo Trying alternative installation method...
        pip install --only-binary=all MetaTrader5 pandas numpy pytz tkcalendar matplotlib openpyxl
        if errorlevel 1 (
            echo %RED%Installation failed. You may need to install Microsoft Visual C++ Build Tools%NC%
            echo Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
            pause
            exit /b 1
        )
    )
) else (
    echo %GREEN%Dependencies already installed%NC%
)

:: Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "config" mkdir config

:: Launch the application
echo %GREEN%Launching Forex Backtest Application...%NC%
echo.
python main.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo %RED%Application exited with an error%NC%
    pause
)

echo.
echo %GREEN%Application closed normally%NC%
pause