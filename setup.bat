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
    echo [1/2] Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo [1/2] Virtual environment (.venv) already exists.
)

echo [2/2] Installing Zoovy and zero-browser MCP dependencies...
call .venv\Scripts\activate.bat
pip install -e .

echo.
echo ============================================
echo   Zoovy Setup Completed Successfully! (MCP Mode)
echo ============================================
echo Next steps:
echo   1. Start Ollama:   ollama serve
echo   2. Run diagnosis:  .venv\Scripts\zoovy doctor
echo   3. Setup model:    .venv\Scripts\zoovy setup
echo   4. Order via MCP:  .venv\Scripts\zoovy order "Get 4 cans of diet coke"
echo.
pause
