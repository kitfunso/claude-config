# Aggregate telemetry — show which gates caught real issues per project over time
# Usage: powershell -File telemetry-report.ps1 [-Project <substring>] [-Days <n>]
param(
    [string]$Project = '',
    [int]$Days = 30
)

$logFile = Join-Path $env:USERPROFILE '.claude\skills\dev-framework\logs\telemetry.jsonl'
if (-not (Test-Path $logFile)) {
    Write-Host "No telemetry yet. Log gate outcomes with: powershell -File log-gate.ps1 -Project ... -Gate ... -Phase ... -Outcome ..."
    exit 0
}

$cutoff = (Get-Date).AddDays(-$Days)
$entries = Get-Content $logFile | ForEach-Object {
    try { $_ | ConvertFrom-Json } catch {}
} | Where-Object { $_ -and ([datetime]$_.timestamp) -ge $cutoff }

if ($Project) {
    $entries = $entries | Where-Object { $_.project -like "*$Project*" }
}

if (-not $entries -or $entries.Count -eq 0) {
    Write-Host "No matching entries in last $Days days."
    exit 0
}

Write-Host ""
Write-Host "=== dev-framework telemetry (last $Days days$(if ($Project) { ", project=$Project" })) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Gate outcomes:" -ForegroundColor Yellow
Write-Host ("  {0,-30} {1,-7} {2,-7} {3,-7} {4,-7}" -f 'gate', 'total', 'caught', 'passed', 'skipped')
Write-Host ("  " + ('-' * 60))
$entries | Group-Object gate | Sort-Object Count -Descending | ForEach-Object {
    $g = $_.Name
    $total = $_.Count
    $caught = @($_.Group | Where-Object { $_.outcome -eq 'caught' }).Count
    $passed = @($_.Group | Where-Object { $_.outcome -eq 'passed' }).Count
    $skipped = @($_.Group | Where-Object { $_.outcome -eq 'skipped' }).Count
    Write-Host ("  {0,-30} {1,-7} {2,-7} {3,-7} {4,-7}" -f $g, $total, $caught, $passed, $skipped)
}

Write-Host ""
Write-Host "Gates that caught real issues (last 20):" -ForegroundColor Green
$caughtEntries = $entries | Where-Object outcome -eq 'caught' | Sort-Object timestamp -Descending | Select-Object -First 20
if ($caughtEntries) {
    foreach ($e in $caughtEntries) {
        $proj = Split-Path -Leaf $e.project
        Write-Host "  $($e.timestamp) | $proj | $($e.gate) | $($e.notes)"
    }
} else {
    Write-Host "  (none yet)"
}

Write-Host ""
Write-Host "Gates skipped (last 10):" -ForegroundColor Red
$skippedEntries = $entries | Where-Object outcome -eq 'skipped' | Sort-Object timestamp -Descending | Select-Object -First 10
if ($skippedEntries) {
    foreach ($e in $skippedEntries) {
        $proj = Split-Path -Leaf $e.project
        Write-Host "  $($e.timestamp) | $proj | $($e.gate) | $($e.notes)"
    }
} else {
    Write-Host "  (none)"
}
Write-Host ""

# Per-project surfacing insight
Write-Host "Per-project insights:" -ForegroundColor Cyan
$entries | Group-Object project | ForEach-Object {
    $p = Split-Path -Leaf $_.Name
    $skippedSet = @($_.Group | Where-Object { $_.outcome -eq 'skipped' } | Select-Object -ExpandProperty gate -Unique)
    $caughtSet = @($_.Group | Where-Object { $_.outcome -eq 'caught' } | Select-Object -ExpandProperty gate -Unique)
    if ($skippedSet.Count -gt 0) {
        Write-Host "  $p - skipped: $($skippedSet -join ', ')"
    }
    if ($caughtSet.Count -gt 0) {
        Write-Host "  $p - caught real issues via: $($caughtSet -join ', ')" -ForegroundColor Green
    }
}
Write-Host ""
