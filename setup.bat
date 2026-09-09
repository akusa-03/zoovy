@echo off
setlocal
echo ============================================
echo   Setting up Zoovy Environment (Windows)
echo ============================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment (.venv) already exists.
)

echo [2/3] Installing Zoovy and zero-browser MCP dependencies...
call .venv\Scripts\activate.bat
pip install -e .

echo [3/3] Adding Zoovy to PATH...
set "VENV_SCRIPTS=%CD%\.venv\Scripts"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"
if defined USER_PATH (
    echo "%USER_PATH%" | findstr /i /c:"%VENV_SCRIPTS%" >nul
    if errorlevel 1 (
        setx PATH "%USER_PATH%;%VENV_SCRIPTS%" >nul
        echo Added %VENV_SCRIPTS% to User PATH.
    ) else (
        echo Zoovy is already in your User PATH.
    )
) else (
    setx PATH "%VENV_SCRIPTS%" >nul
    echo Added %VENV_SCRIPTS% to User PATH.
)

echo.
echo ============================================
echo   Zoovy Setup Completed Successfully! (MCP Mode)
echo ============================================
echo Next steps:
echo   1. Start Ollama:   ollama serve
echo   2. Run diagnosis:  zoovy doctor
echo   3. Setup model:    zoovy setup
echo   4. Order via MCP:  zoovy order "Get 4 cans of diet coke"
echo.
pause
