# Captures hippo memory on phase boundary changes
# Designed to run on Stop hook — silent on no-change, captures on phase transitions
# Usage: powershell -File phase-capture.ps1 [-Path <dir>]
param([string]$Path = (Get-Location).Path)

$ErrorActionPreference = 'SilentlyContinue'

$stateDir = Join-Path $env:USERPROFILE '.claude'
$stateFile = Join-Path $stateDir 'dev-framework-state.txt'
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scanOutput = & "$scriptDir\scan-project.ps1" -Path $Path 2>$null
if (-not $scanOutput) { exit 0 }

try {
    $scan = $scanOutput | ConvertFrom-Json
} catch {
    exit 0
}

$currentPhase = $scan.phase
$projectKey = ($scan.path -replace '[\/\\:]', '_')

# Load state (simple pipe-delimited format to avoid PS5.1 JSON hash limitations)
$state = @{}
if (Test-Path $stateFile) {
    Get-Content $stateFile -ErrorAction SilentlyContinue | ForEach-Object {
        $parts = $_ -split '\|', 3
        if ($parts.Count -eq 3) {
            $state[$parts[0]] = @{ phase = $parts[1]; timestamp = $parts[2] }
        }
    }
}

# Detect phase transition
$prevPhase = $null
if ($state.ContainsKey($projectKey)) { $prevPhase = $state[$projectKey].phase }

if ($prevPhase -and ($prevPhase -ne $currentPhase)) {
    $msg = "dev-framework phase transition: $prevPhase -> $currentPhase in $($scan.path)"

    # Try to capture via hippo CLI
    $hippoOk = $false
    try {
        $msg | hippo capture --stdin 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $hippoOk = $true }
    } catch {}

    if ($hippoOk) {
        Write-Host "[dev-framework] hippo capture: $prevPhase -> $currentPhase"
    } else {
        Write-Host "[dev-framework] phase transition (hippo unavailable): $prevPhase -> $currentPhase in $($scan.path)"
    }
}
# else: phase stable — silent

# Save state
$ts = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'
$state[$projectKey] = @{ phase = $currentPhase; timestamp = $ts }

$lines = $state.Keys | ForEach-Object {
    "$_|$($state[$_].phase)|$($state[$_].timestamp)"
}
$lines | Set-Content $stateFile -Encoding utf8
