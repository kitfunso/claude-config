# Append-only telemetry log for gate invocations
# Usage: powershell -File log-gate.ps1 -Project <path> -Gate <name> -Phase <phase> -Outcome <passed|failed|skipped|caught> [-Notes <text>]
#
# Outcomes:
#   passed  — gate ran and accepted (no issues found)
#   caught  — gate ran and FOUND a real issue (the gate earned its keep)
#   failed  — gate ran but blocked progression
#   skipped — gate not run when it should have been
param(
    [Parameter(Mandatory)][string]$Project,
    [Parameter(Mandatory)][string]$Gate,
    [Parameter(Mandatory)][string]$Phase,
    [Parameter(Mandatory)][ValidateSet('passed','failed','skipped','caught')][string]$Outcome,
    [string]$Notes = ''
)

$logDir = Join-Path $env:USERPROFILE '.claude\skills\dev-framework\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir 'telemetry.jsonl'

$entry = [ordered]@{
    timestamp = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
    project = $Project
    gate = $Gate
    phase = $Phase
    outcome = $Outcome
    notes = $Notes
}

$json = $entry | ConvertTo-Json -Compress
Add-Content -Path $logFile -Value $json -Encoding utf8
Write-Host "[dev-framework] logged: $Gate=$Outcome ($Project)"
