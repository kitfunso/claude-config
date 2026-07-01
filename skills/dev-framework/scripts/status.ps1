# Compact one-liner status: phase, types, sensitivity, next gate
# Usage: powershell -File status.ps1 [-Path <dir>]
param([string]$Path = (Get-Location).Path)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scanOutput = & "$scriptDir\scan-project.ps1" -Path $Path
$scan = $scanOutput | ConvertFrom-Json

$typesStr = if ($scan.types.PSObject.Properties) { ($scan.types.PSObject.Properties.Name -join ',') } else { 'none' }
$sensStr = if ($scan.sensitivity.Count -gt 0) { ($scan.sensitivity -join ',') } else { 'none' }
$branchStr = if ($scan.branch) { $scan.branch } else { '(no git)' }

$nextGate = switch ($scan.phase) {
    'DISCOVER' { '/office-hours -> /search-first -> /plan-ceo-review' }
    'SCAFFOLD' { '/project-scaffold (+ /design-consultation if UI)' }
    'PLAN'     { '/plan-eng-review (+ /plan-design-review if UI) -> /codex' }
    'EXECUTE'  { 'implement plan with TDD/EDD, framing pass on fix-its' }
    'VERIFY'   { '/verify | /qa | /smoke-test | /run  (RUNTIME EVIDENCE REQUIRED)' }
    'REVIEW'   { '/self-review -> /review -> /codex -> /cso (if sensitive) -> /design-review (if UI)' }
    'SHIP'     { '/ship-check -> /sinking-ship -> /commit or /publish-repo' }
    'DEPLOY'   { '/land-and-deploy -> /canary -> Lighthouse' }
    'LEARN'    { '/document-release -> /retro -> hippo outcome --good' }
    default    { 'unknown phase' }
}

# Artifact summary
$artPresent = @()
$artMissing = @()
foreach ($prop in $scan.artifacts.PSObject.Properties) {
    if ($prop.Value) { $artPresent += $prop.Name } else { $artMissing += $prop.Name }
}
$artStr = if ($artMissing.Count -eq 0) { 'all' } else { "$($artPresent.Count)/$($artPresent.Count + $artMissing.Count)" }

Write-Host ""
Write-Host "=== dev-framework status ===" -ForegroundColor Cyan
Write-Host "  path:        $($scan.path)"
Write-Host "  phase:       $($scan.phase)" -ForegroundColor Yellow
Write-Host "  types:       $typesStr"
Write-Host "  sensitive:   $sensStr"
Write-Host "  branch:      $branchStr"
Write-Host "  artifacts:   $artStr present"
if ($artMissing.Count -gt 0) {
    Write-Host "  missing:     $($artMissing -join ', ')" -ForegroundColor Red
}
Write-Host ""
Write-Host "  next:        $nextGate" -ForegroundColor Green
Write-Host ""
