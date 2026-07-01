# Verifies required documentation artifacts are present
# Usage: powershell -File artifact-check.ps1 [-UI]
param([switch]$UI)

$required = @('PRD.md', 'ARCHITECTURE.md', 'CLAUDE.md', 'PLAN.md', 'README.md')
if ($UI) { $required += 'DESIGN.md' }

$missing = @()
$present = @()
foreach ($file in $required) {
    if (Test-Path $file) { $present += $file } else { $missing += $file }
}

Write-Host "PRESENT:" -ForegroundColor Green
foreach ($f in $present) { Write-Host "  + $f" }
Write-Host ""
Write-Host "MISSING:" -ForegroundColor Red
foreach ($f in $missing) { Write-Host "  - $f" }
Write-Host ""

if ($missing.Count -eq 0) {
    Write-Host "OK: all required artifacts present" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAIL: $($missing.Count) artifact(s) missing" -ForegroundColor Red
    exit 1
}
