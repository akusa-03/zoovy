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
    Write-Host "[1/3] Creating virtual environment (.venv)..." -ForegroundColor Green
    python -m venv .venv
} else {
    Write-Host "[1/3] Virtual environment (.venv) already exists." -ForegroundColor Green
}

# Activate & Install MCP dependencies
Write-Host "[2/3] Installing Zoovy and zero-browser MCP dependencies..." -ForegroundColor Green
& .\.venv\Scripts\pip.exe install -e .

# Add to PATH
Write-Host "[3/3] Adding Zoovy to User PATH..." -ForegroundColor Green
$venvScripts = Join-Path (Get-Location) ".venv\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if (-not $userPath) {
    [Environment]::SetEnvironmentVariable("Path", $venvScripts, [EnvironmentVariableTarget]::User)
    $env:Path = "$env:Path;$venvScripts"
    Write-Host "Added $venvScripts to User PATH." -ForegroundColor Green
} elseif ($userPath -split ';' -notcontains $venvScripts) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$venvScripts", [EnvironmentVariableTarget]::User)
    $env:Path = "$env:Path;$venvScripts"
    Write-Host "Added $venvScripts to User PATH." -ForegroundColor Green
} else {
    Write-Host "Zoovy is already in User PATH." -ForegroundColor Green
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   Zoovy Setup Completed Successfully! (Zero-Browser MCP Mode)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Run diagnosis:  zoovy doctor" -ForegroundColor Yellow
Write-Host "  2. Download model: zoovy setup" -ForegroundColor Yellow
Write-Host "  3. Place an order: zoovy order 'Get 4 cans of diet coke'" -ForegroundColor Yellow
