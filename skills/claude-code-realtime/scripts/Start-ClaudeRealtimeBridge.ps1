param(
    [string]$Mailbox = ".claude-realtime",
    [string]$Claude = "claude",
    [int]$PollMs = 750,
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$mailboxPath = Join-Path (Resolve-Path ".").Path $Mailbox
$inbox = Join-Path $mailboxPath "inbox.jsonl"
$outbox = Join-Path $mailboxPath "outbox.jsonl"
$stateFile = Join-Path $mailboxPath "state.json"

New-Item -ItemType Directory -Force -Path $mailboxPath | Out-Null
foreach ($path in @($inbox, $outbox)) {
    if (-not (Test-Path $path)) { New-Item -ItemType File -Path $path | Out-Null }
}

$processed = @{}
if (Test-Path $stateFile) {
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        foreach ($id in $state.processed) { $processed[$id] = $true }
    } catch {}
}

function Save-State {
    @{ processed = @($processed.Keys) } | ConvertTo-Json -Depth 3 | Set-Content -Path $stateFile -Encoding UTF8
}

function Write-Outbox {
    param([object]$Payload)
    $line = $Payload | ConvertTo-Json -Depth 8 -Compress
    Add-Content -Path $outbox -Value $line -Encoding UTF8
}

function Invoke-ClaudeRequest {
    param([object]$Request)
    $id = if ($Request.id) { [string]$Request.id } else { [guid]::NewGuid().ToString() }
    $prompt = [string]$Request.prompt
    if ([string]::IsNullOrWhiteSpace($prompt)) {
        Write-Outbox ([pscustomobject]@{
            id = $id
            ok = $false
            timestamp = (Get-Date).ToString("o")
            error = "Missing prompt"
        })
        return
    }

    $cwd = if ($Request.cwd) { [string]$Request.cwd } else { (Resolve-Path ".").Path }
    $fullPrompt = $prompt
    if ($Request.system) {
        $fullPrompt = "System note:`n$($Request.system)`n`nUser request:`n$prompt"
    }

    $started = Get-Date
    try {
        Push-Location $cwd
        $output = & $Claude -p $fullPrompt --output-format json 2>&1
        $exitCode = $LASTEXITCODE
        Pop-Location
        Write-Outbox ([pscustomobject]@{
            id = $id
            ok = ($exitCode -eq 0)
            exit_code = $exitCode
            timestamp = (Get-Date).ToString("o")
            duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            cwd = $cwd
            output = ($output -join "`n")
        })
    } catch {
        try { Pop-Location } catch {}
        Write-Outbox ([pscustomobject]@{
            id = $id
            ok = $false
            timestamp = (Get-Date).ToString("o")
            duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            cwd = $cwd
            error = $_.Exception.Message
        })
    }
}

Write-Host "Claude realtime bridge watching $inbox"
do {
    $lines = @()
    try { $lines = Get-Content $inbox -ErrorAction Stop } catch {}
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $request = $line | ConvertFrom-Json
            $id = if ($request.id) { [string]$request.id } else { $line.GetHashCode().ToString() }
            if ($processed.ContainsKey($id)) { continue }
            $processed[$id] = $true
            Save-State
            Invoke-ClaudeRequest -Request $request
            Save-State
        } catch {
            Write-Outbox ([pscustomobject]@{
                id = [guid]::NewGuid().ToString()
                ok = $false
                timestamp = (Get-Date).ToString("o")
                error = "Invalid inbox line: $($_.Exception.Message)"
                raw = $line
            })
        }
    }
    if ($Once) { break }
    Start-Sleep -Milliseconds $PollMs
} while ($true)
