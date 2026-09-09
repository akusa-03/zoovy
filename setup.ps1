# Zoovy PowerShell Setup Script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Setting up Zoovy Environment (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check execution policy
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted" -or $policy -eq "Undefined") {
    Write-Host "Configuring PowerShell script permissions (CurrentUser -> RemoteSigned)..." -ForegroundColor Yellow
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
}

# Verify Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python was not found in your PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "[1/2] Creating virtual environment (.venv)..." -ForegroundColor Green
    python -m venv .venv
} else {
    Write-Host "[1/2] Virtual environment (.venv) already exists." -ForegroundColor Green
}

# Activate & Install MCP dependencies
Write-Host "[2/2] Installing Zoovy and zero-browser MCP dependencies..." -ForegroundColor Green
& .\.venv\Scripts\pip.exe install -e .

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   Zoovy Setup Completed Successfully! (Zero-Browser MCP Mode)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Activate venv:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  2. Run diagnosis:  zoovy doctor" -ForegroundColor Yellow
Write-Host "  3. Download model: zoovy setup" -ForegroundColor Yellow
Write-Host "  4. Place an order: zoovy order 'Get 4 cans of diet coke'" -ForegroundColor Yellow
