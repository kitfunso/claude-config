param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [string]$Mailbox = ".claude-realtime",
    [string]$Id = "",
    [string]$Cwd = "",
    [string]$System = ""
)

$ErrorActionPreference = "Stop"
$mailboxPath = Join-Path (Resolve-Path ".").Path $Mailbox
$inbox = Join-Path $mailboxPath "inbox.jsonl"
New-Item -ItemType Directory -Force -Path $mailboxPath | Out-Null
if (-not (Test-Path $inbox)) { New-Item -ItemType File -Path $inbox | Out-Null }

if ([string]::IsNullOrWhiteSpace($Id)) {
    $Id = [guid]::NewGuid().ToString()
}
if ([string]::IsNullOrWhiteSpace($Cwd)) {
    $Cwd = (Resolve-Path ".").Path
}

$payload = [ordered]@{
    id = $Id
    prompt = $Prompt
    cwd = $Cwd
}
if (-not [string]::IsNullOrWhiteSpace($System)) {
    $payload.system = $System
}

$line = $payload | ConvertTo-Json -Depth 6 -Compress
Add-Content -Path $inbox -Value $line -Encoding UTF8
[pscustomobject]@{ id = $Id; inbox = $inbox } | ConvertTo-Json -Depth 3
