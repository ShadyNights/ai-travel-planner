# ==================== CHECK CLOUD STATS ====================
# Auto-activates venv and runs stats

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Activate venv
& ".\venv\Scripts\Activate.ps1"

# Run stats
python check_cloud_stats.py

# Keep window open
Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
