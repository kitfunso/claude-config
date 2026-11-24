#!/usr/bin/env bash

set -eo pipefail
PROJECT_PATH="${1:-$(pwd)}"
cd "$PROJECT_PATH"

has_file() { [ -e "$1" ]; }

has_node_dep() {
    [ ! -f package.json ] && return 1
    local dep
    for dep in "$@"; do
        if grep -qF "\"$dep\":" package.json; then
            return 0
        fi
    done
    return 1
}

has_py_dep() {
    local dep f
    for f in requirements.txt pyproject.toml; do
        [ -f "$f" ] || continue
        for dep in "$@"; do
            local esc=$(printf '%s' "$dep" | sed 's/[][\.*^$(){}?+|/]/\\&/g')
            if grep -qE "^\s*${esc}[[:space:]=<>~,!\[]" "$f" || grep -qE "['\"]${esc}['\"]" "$f"; then
                return 0
            fi
        done
    done
    return 1
}

declare -A types

ui=0
has_node_dep react next vue svelte solid astro nuxt remix @remix-run/react preact @sveltejs/kit && ui=90
{ has_file next.config.js || has_file next.config.ts || has_file next.config.mjs; } && ui=100
{ has_file vite.config.js || has_file vite.config.ts || has_file tailwind.config.js || has_file tailwind.config.ts; } && [ $ui -lt 80 ] && ui=80
if find . -maxdepth 4 -type f \( -name "*.tsx" -o -name "*.jsx" -o -name "*.svelte" -o -name "*.vue" \) 2>/dev/null | head -1 | grep -q .; then
    [ $ui -lt 70 ] && ui=70
fi
[ $ui -ge 40 ] && types[ui]=$ui

ai=0
has_node_dep '@anthropic-ai/sdk' anthropic openai langchain '@langchain/core' llamaindex '@llamaindex/core' litellm '@modelcontextprotocol/sdk' && ai=90
[ $ai -eq 0 ] && has_py_dep anthropic openai langchain llamaindex transformers litellm mcp && ai=90
{ has_file agents || has_file prompts || has_file evals || has_file SKILL.md; } && [ $ai -lt 80 ] && ai=80
[ $ai -ge 40 ] && types[ai-agent]=$ai

be=0
has_node_dep express fastify koa '@koa/router' hono '@nestjs/core' && be=90
[ $be -eq 0 ] && has_py_dep fastapi django flask sqlalchemy starlette && be=90
{ has_file routes || has_file api || has_file migrations; } && [ $be -lt 70 ] && be=70
[ $be -ge 40 ] && types[backend]=$be

quant=0
case "$PROJECT_PATH" in
    *Quantamental*) quant=100 ;;
esac
if [ $quant -eq 0 ]; then
    { has_file signals || has_file live_signal.json || has_file rolls.csv; } && quant=90
fi
if [ $quant -eq 0 ]; then
    has_py_dep pandas numpy scipy yfinance QuantLib && quant=50
fi
[ $quant -ge 40 ] && types[quant]=$quant

cli=0
[ -f package.json ] && grep -q '"bin"' package.json && cli=100
[ -f pyproject.toml ] && grep -qE '^\s*\[project\.scripts\]' pyproject.toml && [ $cli -lt 90 ] && cli=90
{ has_file bin || has_file cmd; } && [ $cli -lt 70 ] && cli=70
[ $cli -ge 40 ] && types[cli]=$cli

lib=0
if [ -f package.json ]; then
    if grep -qE '"(main|module|exports)"' package.json && ! grep -q '"bin"' package.json; then
        lib=90
    fi
fi
{ has_file CHANGELOG.md && ! has_file app; } && [ $lib -lt 50 ] && lib=50
[ $lib -ge 40 ] && types[library]=$lib

mobile=0
{ has_file capacitor.config.json || has_file capacitor.config.ts || has_file capacitor.config.js; } && mobile=100
{ has_file android && has_file ios; } && [ $mobile -lt 90 ] && mobile=90
has_node_dep '@capacitor/core' react-native expo '@react-native/core' '@expo/cli' && [ $mobile -lt 80 ] && mobile=80
[ $mobile -ge 40 ] && types[mobile]=$mobile

types_json="{"
first=1
for k in "${!types[@]}"; do
    [ $first -eq 0 ] && types_json="$types_json,"
    types_json="$types_json\"$k\":0.${types[$k]}"
    first=0
done
types_json="$types_json}"

get_bool() { has_file "$1" && echo "true" || echo "false"; }
artifacts="{\"PRD\":$(get_bool PRD.md),\"ARCHITECTURE\":$(get_bool ARCHITECTURE.md),\"CLAUDE\":$(get_bool CLAUDE.md),\"PLAN\":$(get_bool PLAN.md),\"DESIGN\":$(get_bool DESIGN.md),\"README\":$(get_bool README.md),\"CHANGELOG\":$(get_bool CHANGELOG.md)}"

phase="DISCOVER"
{ has_file PRD.md || has_file PLAN.md; } && phase="SCAFFOLD"
{ has_file PRD.md && has_file ARCHITECTURE.md && has_file PLAN.md; } && phase="PLAN"
has_commits="false"
git log --oneline -1 2>/dev/null | head -c 1 | grep -q . && has_commits="true"
branch=$(git branch --show-current 2>/dev/null || echo "")
pr_open="false"
if command -v gh >/dev/null 2>&1; then
    gh pr view --json state 2>/dev/null | grep -q '"OPEN"' && pr_open="true"
fi
[ "$has_commits" = "true" ] && has_file PLAN.md && phase="EXECUTE"
[ "$pr_open" = "true" ] && phase="REVIEW"

code_blob=$(find . -maxdepth 4 -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) 2>/dev/null | head -200 | xargs -I {} cat {} 2>/dev/null || true)

sens_arr=""

if has_node_dep passport jsonwebtoken next-auth '@clerk/nextjs' '@auth0/auth0-react' '@auth0/nextjs-auth0' lucia '@supabase/auth-helpers-nextjs' better-auth iron-session \
   || has_py_dep python-jose authlib pyjwt fastapi-users flask-login django-allauth; then
    sens_arr="$sens_arr\"auth\","
elif echo "$code_blob" | grep -qE 'from\s+passport|jwt\.(sign|verify|decode)\b|\bNextAuth\b|getServerSession\(|@clerk/|supabase\.auth\.|auth0Client|OAuth2Client'; then
    sens_arr="$sens_arr\"auth\","
fi

if has_node_dep stripe '@stripe/stripe-js' '@stripe/react-stripe-js' '@paypal/react-paypal-js' '@lemonsqueezy/lemonsqueezy.js' \
   || has_py_dep stripe paypalrestsdk squareup; then
    sens_arr="$sens_arr\"payments\","
elif echo "$code_blob" | grep -qE 'stripe\.(charges|customers|paymentIntents|subscriptions|checkout)|from\s+stripe\b|import\s+stripe\b|paypal\.payment|lemonsqueezy\.com/v1'; then
    sens_arr="$sens_arr\"payments\","
fi

if echo "$code_blob" | grep -qE '(@Column|@Field|@Property|@PrimaryColumn).*\b(email|phone|address|ssn|dob)\b|String\s+(email|phone|address|firstName|lastName)\b|(email|phone|firstName|lastName)\s*=\s*models\.(EmailField|CharField|String)'; then
    sens_arr="$sens_arr\"pii\","
fi

real_envs=$(ls .env* 2>/dev/null | grep -vE '\.(example|template|sample|dist)$' | head -1)
if [ -n "$real_envs" ]; then
    sens_arr="$sens_arr\"secrets\","
elif echo "$code_blob" | grep -qE 'process\.env\.[A-Z_]+_(KEY|SECRET|TOKEN|PASSWORD)|os\.environ\.get\(['\''"][A-Z_]+_(KEY|SECRET|TOKEN)|AWS_SECRET_ACCESS_KEY|KMS_KEY_ID|HashiCorpVault|getSecret\('; then
    sens_arr="$sens_arr\"secrets\","
fi

sensitivity="[${sens_arr%,}]"

cat <<EOF
{
  "path": "$PROJECT_PATH",
  "types": $types_json,
  "phase": "$phase",
  "sensitivity": $sensitivity,
  "artifacts": $artifacts,
  "branch": "$branch",
  "has_pr_open": $pr_open,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
