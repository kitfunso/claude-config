#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/specs
cat > docs/specs/csv-export.md <<'EOF'
# Feature: CSV export

1. Export trades to CSV with columns: date, qty, price.
2. Log the export file path to the audit log (audit.log_export(path)).
EOF
cat > CODING_STANDARDS.md <<'EOF'
# Coding standards

## Logging
Use the `logging` module. No bare `print()` calls in library code.
EOF
cat > exporter.py <<'EOF'
import csv
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init, add spec and standards"
git tag v1
cat > exporter.py <<'EOF'
import csv


def export_trades(trades, path):
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "qty", "price"])
        for t in trades:
            writer.writerow([t.date, t.qty, t.price])
    print(f"exported {len(trades)} rows to {path}")
EOF
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "feat: add CSV export"
