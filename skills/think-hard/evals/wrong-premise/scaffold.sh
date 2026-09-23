#!/usr/bin/env bash
set -euo pipefail
cat > data.csv <<'EOF'
date,rate
2026-09-01,10.0
2026-09-02,10.5
2026-09-03,9.5
2026-09-04,10.0
2026-09-05,40.0
2026-09-05,40.0
2026-09-08,10.0
EOF
cat > stats.py <<'EOF'
import csv

with open("data.csv", newline="") as fh:
    vals = [float(r["rate"]) for r in csv.DictReader(fh)]
print(round(sum(vals) / len(vals), 2))
EOF
