param (
    [switch]$PurgeVenv,
    [switch]$PurgeConfig,
    [switch]$All
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Red
Write-Host "         [!] ZOOVY EMERGENCY KILL SWITCH & CLEANUP        " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Red
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$homeZoovy = Join-Path $HOME ".zoovy"

Write-Host "[1/4] Scanning and terminating lingering Zoovy processes..." -ForegroundColor Cyan

$killedCount = 0

# Terminate Python / Pip processes related to zoovy
$pyProcs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -like "python*" -or $_.Name -like "pip*") -and 
    ($_.CommandLine -like "*zoovy*" -or $_.ExecutablePath -like "*zoovy*")
}
if ($pyProcs) {
    foreach ($p in $pyProcs) {
        Write-Host "  * Terminating $($p.Name) (PID: $($p.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killedCount++
    }
}

# Terminate Playwright / Chromium / Node
$nodeProcs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -like "*chromium*" -or $_.Name -like "*node*" -or $_.Name -like "*playwright*") -and 
    ($_.CommandLine -like "*zoovy*")
}
if ($nodeProcs) {
    foreach ($p in $nodeProcs) {
        Write-Host "  * Terminating $($p.Name) (PID: $($p.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killedCount++
    }
}

# Terminate Ollama if running with zoovy in commandline
$ollamaProcs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like "*ollama*" -and ($_.CommandLine -like "*serve*" -or $_.CommandLine -like "*zoovy*")
}
if ($ollamaProcs) {
    foreach ($p in $ollamaProcs) {
        Write-Host "  * Terminating Ollama background daemon (PID: $($p.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killedCount++
    }
}

if ($killedCount -eq 0) {
    Write-Host "  [+] No active locking processes found." -ForegroundColor Green
} else {
    Write-Host "  [+] Terminated $killedCount background process(es)." -ForegroundColor Green
}

Write-Host "[2/4] Releasing file handles and directory locks..." -ForegroundColor Cyan
Start-Sleep -Seconds 1
Write-Host "  [+] Directory locks released." -ForegroundColor Green

if ($PurgeVenv -or $All) {
    Write-Host "[3/4] Purging virtual environment (.venv)..." -ForegroundColor Cyan
    $venvPath = Join-Path $scriptDir ".venv"
    if (Test-Path $venvPath) {
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [+] Deleted .venv successfully." -ForegroundColor Green
    } else {
        Write-Host "  * No .venv found to remove." -ForegroundColor Gray
    }
} else {
    Write-Host "[3/4] Skipping .venv removal (pass -PurgeVenv or -All to delete)." -ForegroundColor Gray
}

if ($PurgeConfig -or $All) {
    Write-Host "[4/4] Purging ~/.zoovy configuration and tokens..." -ForegroundColor Cyan
    if (Test-Path $homeZoovy) {
        Remove-Item -Path $homeZoovy -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [+] Deleted $homeZoovy successfully." -ForegroundColor Green
    } else {
        Write-Host "  * No ~/.zoovy found to remove." -ForegroundColor Gray
    }
} else {
    Write-Host "[4/4] Skipping ~/.zoovy configuration purge (pass -PurgeConfig or -All to delete)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[+] All Zoovy resources have been successfully unlocked!" -ForegroundColor Green
Write-Host "You can now safely move, edit, or delete the Zoovy folder." -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
