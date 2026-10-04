#!/usr/bin/env bash
# Who is already working in a repo: run before naming or starting "next" work.
# Usage: inflight.sh <repo-path> [hours]   (default 24)
set -u
repo="${1:-.}"
hours="${2:-24}"
cutoff=$(( $(date +%s) - hours * 3600 ))
map="${TMPDIR:-/tmp}/inflight.$$"
trap 'rm -f "$map"' EXIT

echo "== open PRs"
(cd "$repo" && gh pr list --state open --limit 40 \
  --json number,updatedAt,headRefName,title \
  --jq '.[] | "#\(.number) \(.updatedAt[0:16]) \(.headRefName) | \(.title)"')

echo "== worktrees with a commit in the last ${hours}h, newest first"
# One git log for every worktree HEAD and parallel status checks: hippo has 130+ worktrees.
git -C "$repo" worktree list --porcelain \
  | awk '/^worktree /{wt=substr($0,10)} /^HEAD /{print $2 "\t" wt}' > "$map"
cut -f1 "$map" | sort -u | xargs git -C "$repo" log --no-walk --format='%H %ct %cr|%s' 2>/dev/null \
  | awk -v cutoff="$cutoff" '$2 >= cutoff' | sort -k2,2nr \
  | while read -r sha ts rest; do
      awk -F'\t' -v s="$sha" -v r="$rest" '$1 == s {print $2 "\t" r}' "$map"
    done \
  | xargs -d '\n' -P 8 -I{} bash -c '
      wt=$(printf "%s" "$1" | cut -f1); msg=$(printf "%s" "$1" | cut -f2 | cut -c1-80)
      printf "%s [%s] %s | dirty %s\n" "$wt" "$(git -C "$wt" branch --show-current)" "$msg" \
        "$(git -C "$wt" status --porcelain -uno 2>/dev/null | wc -l)"' _ {}
echo "== also run ListAgents for live sessions"
