# ==================== COMPLETE PRODUCTION VERIFICATION ====================
# Run this to verify EVERYTHING is working perfectly

Write-Host "`n🚀 STARTING COMPLETE PRODUCTION VERIFICATION..." -ForegroundColor Green
Write-Host "=" * 70

# Set PostgreSQL path
$env:Path += ";D:\PostGre\bin"

# 1. Test PostgreSQL connection
Write-Host "`n📋 TEST 1: PostgreSQL Connection..." -ForegroundColor Cyan
psql -U postgres -d travel_planner -c "SELECT version();" | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ PostgreSQL connected successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ PostgreSQL connection failed!" -ForegroundColor Red
    exit 1
}

# 2. Check dual storage counts
Write-Host "`n📋 TEST 2: Dual Storage Verification..." -ForegroundColor Cyan

$pg_trips = psql -U postgres -d travel_planner -t -c "SELECT COUNT(*) FROM trips;"
$pg_itins = psql -U postgres -d travel_planner -t -c "SELECT COUNT(*) FROM itineraries;"

Write-Host "   PostgreSQL: $($pg_trips.Trim()) trips, $($pg_itins.Trim()) itineraries" -ForegroundColor White

if (Test-Path "data\trips.json") {
    $json_trips = (Get-Content "data\trips.json" | ConvertFrom-Json).Count
    $json_itins = (Get-Content "data\itineraries.json" | ConvertFrom-Json).Count
    Write-Host "   JSON Backup: $json_trips trips, $json_itins itineraries" -ForegroundColor White
    
    if ($pg_trips.Trim() -eq $json_trips -and $pg_itins.Trim() -eq $json_itins) {
        Write-Host "   ✅ Dual storage SYNCHRONIZED!" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Storage counts don't match" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  JSON files not found" -ForegroundColor Yellow
}

# 3. Run auto-training tests
Write-Host "`n📋 TEST 3: Auto-Training System..." -ForegroundColor Cyan
python test_autotraining.py

# 4. View database data
Write-Host "`n📋 TEST 4: Viewing Database Data..." -ForegroundColor Cyan
chcp 65001 > $null
psql -U postgres -d travel_planner -f view_database.sql

# 5. Check triggers
Write-Host "`n📋 TEST 5: Database Triggers Check..." -ForegroundColor Cyan
$trigger_count = psql -U postgres -d travel_planner -t -c "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = 'public';"
Write-Host "   Found $($trigger_count.Trim()) triggers" -ForegroundColor White

if ($trigger_count.Trim() -gt 0) {
    Write-Host "   ✅ Triggers active!" -ForegroundColor Green
} else {
    Write-Host "   ❌ NO TRIGGERS! Run: psql -U postgres -d travel_planner -f fix_triggers.sql" -ForegroundColor Red
}

# Final summary
Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "🎉 VERIFICATION COMPLETE!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`n✅ All checks completed. Review results above." -ForegroundColor Cyan
Write-Host "`nℹ️  To monitor in real-time, run:" -ForegroundColor Yellow
Write-Host "   psql -U postgres -d travel_planner -c 'SELECT * FROM system_metrics;'" -ForegroundColor White
