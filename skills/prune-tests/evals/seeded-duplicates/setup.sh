#!/usr/bin/env bash
set -euo pipefail
src="$(cd "$(dirname "$0")/fixture" && pwd)"
mkdir -p "$1" && cp -r "$src"/. "$1"/
sed -i 's/if x < 10:/if x <= 10:/' "$1/pricing.py"
git -C "$1" init -q
git -C "$1" add -A
git -C "$1" -c user.name=eval -c user.email=eval@local commit -qm "feat: desk helpers"
cp "$src/pricing.py" "$1/pricing.py"
git -C "$1" -c user.name=eval -c user.email=eval@local commit -qam "fix: band puts 10 in mid"
