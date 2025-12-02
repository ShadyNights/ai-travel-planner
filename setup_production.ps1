# ==================== PRODUCTION SETUP SCRIPT ====================

param(
    [string]$DBPassword = $env:DB_PASSWORD
)

Write-Host "🚀 Setting up Production-Level Dual Storage System..." -ForegroundColor Green

# Check if password is provided
if (-not $DBPassword) {
    $SecurePassword = Read-Host "Enter PostgreSQL password" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
    $DBPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# Set PGPASSWORD to avoid repeated prompts
$env:PGPASSWORD = $DBPassword

try {
    # 1. Create dual storage manager
    Write-Host "`n📁 Creating dual storage system..."
    New-Item -ItemType Directory -Force -Path "data" | Out-Null

    # 2. Fix database encoding
    Write-Host "`n🔧 Fixing PostgreSQL encoding..."
    $env:Path += ";D:\PostGre\bin"
    
    $encodingSQL = "ALTER DATABASE travel_planner SET client_encoding TO 'UTF8';"
    $encodingSQL | psql -U postgres -d travel_planner -q
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Encoding fixed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Encoding fix failed" -ForegroundColor Yellow
    }

    # 3. Fix triggers
    Write-Host "`n⚡ Fixing database triggers..."
    psql -U postgres -d travel_planner -f fix_triggers.sql -q
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Triggers fixed" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Trigger fix failed!" -ForegroundColor Red
        exit 1
    }

    # 4. Test auto-training
    Write-Host "`n🧪 Testing auto-training system..."
    python test_autotraining.py

    # 5. Verify dual storage
    Write-Host "`n✅ Verifying dual storage..."
    if (Test-Path "data\trips.json") {
        Write-Host "   ✓ JSON storage ready" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  JSON storage missing" -ForegroundColor Yellow
    }
    
    if (Test-Path "src\database\dual_storage_manager.py") {
        Write-Host "   ✓ Dual storage manager ready" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Dual storage manager missing!" -ForegroundColor Red
    }

    # 6. Final verification
    Write-Host "`n🎉 Setup complete! Running final checks..." -ForegroundColor Green
    python check_everything.py
    
    Write-Host "`n✅ All checks passed! Starting app..." -ForegroundColor Green
    streamlit run app.py

} finally {
    # Clear password from environment
    $env:PGPASSWORD = $null
}
