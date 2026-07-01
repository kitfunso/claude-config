# Project Scanner — emits JSON describing project type, phase, sensitivity, artifacts
# Usage: powershell -File scan-project.ps1 [-Path <dir>]
param([string]$Path = (Get-Location).Path)

$ErrorActionPreference = 'SilentlyContinue'
if (-not (Test-Path $Path)) { Write-Error "Path not found: $Path"; exit 1 }

Push-Location $Path
try {

function Has-File { param([string]$F) Test-Path $F }

function Get-PackageDeps {
    if (-not (Has-File 'package.json')) { return @() }
    try {
        $pkg = Get-Content 'package.json' -Raw | ConvertFrom-Json
        $deps = @()
        if ($pkg.dependencies) { $deps += $pkg.dependencies.PSObject.Properties.Name }
        if ($pkg.devDependencies) { $deps += $pkg.devDependencies.PSObject.Properties.Name }
        if ($pkg.peerDependencies) { $deps += $pkg.peerDependencies.PSObject.Properties.Name }
        if ($pkg.optionalDependencies) { $deps += $pkg.optionalDependencies.PSObject.Properties.Name }
        return $deps
    } catch { return @() }
}

function Has-NodeDep {
    param([string[]]$Candidates)
    $deps = Get-PackageDeps
    foreach ($c in $Candidates) {
        if ($deps -contains $c) { return $true }
    }
    return $false
}

function Has-PyDep {
    param([string[]]$Candidates)
    foreach ($f in @('requirements.txt', 'pyproject.toml')) {
        if (Has-File $f) {
            $content = Get-Content $f -Raw -ErrorAction SilentlyContinue
            if (-not $content) { continue }
            foreach ($c in $Candidates) {
                $esc = [regex]::Escape($c)
                if ($content -match "(?m)^\s*${esc}[\s=<>~,!\[]" -or $content -match "['""]${esc}['""]") {
                    return $true
                }
            }
        }
    }
    return $false
}

# --- Project type detection — deps-based, no text matching ---
$types = [ordered]@{}

# UI
$ui = 0.0
if (Has-NodeDep @('react', 'next', 'vue', 'svelte', 'solid', 'astro', 'nuxt', 'remix', '@remix-run/react', 'preact', '@sveltejs/kit')) { $ui = 0.9 }
if ((Has-File 'next.config.js') -or (Has-File 'next.config.ts') -or (Has-File 'next.config.mjs')) { $ui = 1.0 }
if ((Has-File 'vite.config.js') -or (Has-File 'vite.config.ts') -or (Has-File 'tailwind.config.js') -or (Has-File 'tailwind.config.ts')) {
    if ($ui -lt 0.8) { $ui = 0.8 }
}
$tsxFiles = Get-ChildItem -Recurse -Depth 4 -File -Include *.tsx,*.jsx,*.svelte,*.vue -ErrorAction SilentlyContinue | Select-Object -First 1
if ($tsxFiles -and $ui -lt 0.7) { $ui = 0.7 }
if ($ui -ge 0.4) { $types['ui'] = $ui }

# AI / agent
$ai = 0.0
if (Has-NodeDep @('@anthropic-ai/sdk', 'anthropic', 'openai', 'langchain', '@langchain/core', 'llamaindex', '@llamaindex/core', 'litellm', '@modelcontextprotocol/sdk')) { $ai = 0.9 }
elseif (Has-PyDep @('anthropic', 'openai', 'langchain', 'llamaindex', 'transformers', 'litellm', 'mcp')) { $ai = 0.9 }
if ((Has-File 'agents') -or (Has-File 'prompts') -or (Has-File 'evals') -or (Has-File 'SKILL.md')) {
    if ($ai -lt 0.8) { $ai = 0.8 }
}
if ($ai -ge 0.4) { $types['ai-agent'] = $ai }

# Backend
$be = 0.0
if (Has-NodeDep @('express', 'fastify', 'koa', '@koa/router', 'hono', '@nestjs/core')) { $be = 0.9 }
elseif (Has-PyDep @('fastapi', 'django', 'flask', 'sqlalchemy', 'starlette')) { $be = 0.9 }
if ((Has-File 'routes') -or (Has-File 'api') -or (Has-File 'migrations')) {
    if ($be -lt 0.7) { $be = 0.7 }
}
if ($be -ge 0.4) { $types['backend'] = $be }

# Quant
$quant = 0.0
if ($Path -match 'Quantamental') { $quant = 1.0 }
elseif ((Has-File 'signals') -or (Has-File 'live_signal.json') -or (Has-File 'rolls.csv')) { $quant = 0.9 }
elseif (Has-PyDep @('pandas', 'numpy', 'scipy', 'yfinance', 'QuantLib')) { $quant = 0.5 }
if ($quant -ge 0.4) { $types['quant'] = $quant }

# CLI
$cli = 0.0
if (Has-File 'package.json') {
    try {
        $pkg = Get-Content 'package.json' -Raw | ConvertFrom-Json
        if ($pkg.bin) { $cli = 1.0 }
    } catch {}
}
if (Has-File 'pyproject.toml') {
    $pyContent = Get-Content 'pyproject.toml' -Raw -ErrorAction SilentlyContinue
    if ($pyContent -and ($pyContent -match '(?m)^\s*\[project\.scripts\]')) {
        if ($cli -lt 0.9) { $cli = 0.9 }
    }
}
if ((Has-File 'bin') -or (Has-File 'cmd')) {
    if ($cli -lt 0.7) { $cli = 0.7 }
}
if ($cli -ge 0.4) { $types['cli'] = $cli }

# Library
$lib = 0.0
if (Has-File 'package.json') {
    try {
        $pkg = Get-Content 'package.json' -Raw | ConvertFrom-Json
        $hasEntry = ($pkg.main -ne $null) -or ($pkg.module -ne $null) -or ($pkg.exports -ne $null)
        $hasBin = ($pkg.bin -ne $null)
        if ($hasEntry -and (-not $hasBin)) { $lib = 0.9 }
    } catch {}
}
if ((Has-File 'CHANGELOG.md') -and (-not (Has-File 'app'))) {
    if ($lib -lt 0.5) { $lib = 0.5 }
}
if ($lib -ge 0.4) { $types['library'] = $lib }

# Mobile — explicit deps OR config files OR both native dirs (no more text-matching "expo")
$mobile = 0.0
if ((Has-File 'capacitor.config.json') -or (Has-File 'capacitor.config.ts') -or (Has-File 'capacitor.config.js')) { $mobile = 1.0 }
if ((Has-File 'android') -and (Has-File 'ios')) {
    if ($mobile -lt 0.9) { $mobile = 0.9 }
}
if (Has-NodeDep @('@capacitor/core', 'react-native', 'expo', '@react-native/core', '@expo/cli')) {
    if ($mobile -lt 0.8) { $mobile = 0.8 }
}
if ($mobile -ge 0.4) { $types['mobile'] = $mobile }

# --- Artifact detection ---
$artifacts = [ordered]@{
    PRD = (Has-File 'PRD.md')
    ARCHITECTURE = (Has-File 'ARCHITECTURE.md')
    CLAUDE = (Has-File 'CLAUDE.md')
    PLAN = (Has-File 'PLAN.md')
    DESIGN = (Has-File 'DESIGN.md')
    README = (Has-File 'README.md')
    CHANGELOG = (Has-File 'CHANGELOG.md')
}

# --- Phase detection ---
$phase = 'DISCOVER'
if ($artifacts.PRD -or $artifacts.PLAN) { $phase = 'SCAFFOLD' }
if ($artifacts.PRD -and $artifacts.ARCHITECTURE -and $artifacts.PLAN) { $phase = 'PLAN' }

$branch = ''
try { $branch = (git branch --show-current 2>$null) } catch {}

$hasCommits = $false
try {
    $log = git log --oneline -1 2>$null
    if ($log) { $hasCommits = $true }
} catch {}

$prOpen = $false
try {
    $prJson = gh pr view --json state 2>$null
    if ($prJson) {
        $prState = $prJson | ConvertFrom-Json
        if ($prState.state -eq 'OPEN') { $prOpen = $true }
    }
} catch {}

if ($hasCommits -and $artifacts.PLAN) { $phase = 'EXECUTE' }
if ($prOpen) { $phase = 'REVIEW' }

# --- Sensitivity detection — deps-first, then import-style patterns. No bare-word matching. ---
$sensitivity = New-Object System.Collections.Generic.List[string]
$codeFiles = Get-ChildItem -Recurse -Depth 4 -File -Include *.py,*.ts,*.tsx,*.js,*.jsx -ErrorAction SilentlyContinue | Select-Object -First 200
$codeBlob = ($codeFiles | Get-Content -Raw -ErrorAction SilentlyContinue) -join "`n"

# Auth — auth library deps OR auth-specific usage patterns
$authNodeDeps = @('passport', 'jsonwebtoken', 'next-auth', '@clerk/nextjs', '@clerk/clerk-sdk-node', '@auth0/auth0-react', '@auth0/nextjs-auth0', 'lucia', '@supabase/auth-helpers-nextjs', 'better-auth', 'iron-session')
$authPyDeps = @('python-jose', 'authlib', 'pyjwt', 'fastapi-users', 'flask-login', 'django-allauth')
if ((Has-NodeDep $authNodeDeps) -or (Has-PyDep $authPyDeps)) {
    $sensitivity.Add('auth')
} else {
    $authPatterns = @(
        'from\s+passport',
        'jwt\.(sign|verify|decode)\b',
        '\bNextAuth\b',
        'getServerSession\(',
        '@clerk/',
        'supabase\.auth\.',
        'auth0Client',
        'OAuth2Client'
    )
    foreach ($p in $authPatterns) {
        if ($codeBlob -match $p) { $sensitivity.Add('auth'); break }
    }
}

# Payments — explicit deps OR specific API calls (dropped "square" — too generic)
$paymentNodeDeps = @('stripe', '@stripe/stripe-js', '@stripe/react-stripe-js', '@paypal/react-paypal-js', '@lemonsqueezy/lemonsqueezy.js', 'square')
$paymentPyDeps = @('stripe', 'paypalrestsdk', 'squareup')
if ((Has-NodeDep $paymentNodeDeps) -or (Has-PyDep $paymentPyDeps)) {
    $sensitivity.Add('payments')
} else {
    $paymentPatterns = @(
        'stripe\.(charges|customers|paymentIntents|subscriptions|checkout)',
        'from\s+stripe\b',
        'import\s+stripe\b',
        'paypal\.payment',
        'lemonsqueezy\.com/v1'
    )
    foreach ($p in $paymentPatterns) {
        if ($codeBlob -match $p) { $sensitivity.Add('payments'); break }
    }
}

# PII — schema/model with PII fields (decorators or typed fields)
$piiPatterns = @(
    '(@Column|@Field|@Property|@PrimaryColumn).*\b(email|phone|address|ssn|dob)\b',
    'String\s+(email|phone|address|firstName|lastName)\b',
    '(email|phone|firstName|lastName)\s*=\s*models\.(EmailField|CharField|String)',
    'class\s+\w*(User|Customer|Patient|Member)\b.*\n[\s\S]{0,500}(email|phone)\b'
)
foreach ($p in $piiPatterns) {
    if ($codeBlob -match $p) { $sensitivity.Add('pii'); break }
}

# Secrets — real .env files (not .env.example) OR explicit secret-access patterns
$envFiles = Get-ChildItem .env* -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '\.(example|template|sample|dist)$' }
if ($envFiles -and ($envFiles.Count -gt 0)) {
    $sensitivity.Add('secrets')
} else {
    $secretPatterns = @(
        'process\.env\.[A-Z_]+_(KEY|SECRET|TOKEN|PASSWORD)',
        'os\.environ\.get\([''"][A-Z_]+_(KEY|SECRET|TOKEN)',
        'AWS_SECRET_ACCESS_KEY',
        'KMS_KEY_ID',
        'HashiCorpVault',
        'getSecret\('
    )
    foreach ($p in $secretPatterns) {
        if ($codeBlob -match $p) { $sensitivity.Add('secrets'); break }
    }
}

# --- Output ---
$result = [ordered]@{
    path = $Path
    types = $types
    phase = $phase
    sensitivity = $sensitivity.ToArray()
    artifacts = $artifacts
    branch = $branch
    has_pr_open = $prOpen
    timestamp = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
}

$result | ConvertTo-Json -Depth 5

} finally { Pop-Location }
