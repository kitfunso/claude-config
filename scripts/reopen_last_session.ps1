param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$claudeDir = Join-Path $env:USERPROFILE '.claude'

$live = @(Get-ChildItem (Join-Path $claudeDir 'sessions\*.json') | ForEach-Object {
    $s = Get-Content $_.FullName -Raw | ConvertFrom-Json
    $p = Get-Process -Id $s.pid -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -eq 'claude') { $s.sessionId }
})

# entrypoint "cli" keeps out `claude -p` and SDK runs, which also write transcripts.
$closed = Get-ChildItem (Join-Path $claudeDir 'projects\*\*.jsonl') |
    Sort-Object LastWriteTime -Descending |
    Where-Object { $live -notcontains $_.BaseName } |
    Where-Object { (Get-Content $_.FullName -TotalCount 200) -match '"entrypoint":"cli"' } |
    Select-Object -First 1

if (-not $closed) {
    Write-Host 'No closed Claude Code session found.'
    exit 1
}

$cwdLine = (Get-Content $closed.FullName -TotalCount 200) -match '"cwd":"' | Select-Object -First 1
$cwd = ($cwdLine | ConvertFrom-Json).cwd
Write-Host "Reopening $($closed.BaseName) in $cwd (last active $($closed.LastWriteTime))"
if ($DryRun) { exit 0 }

Set-Location -LiteralPath $cwd
claude --resume $closed.BaseName
