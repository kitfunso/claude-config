#!/usr/bin/env bash
set -euo pipefail
mkdir -p good-skill
cat > good-skill/SKILL.md <<'EOF'
---
name: db-migration-check
description: Verify a DB migration is reversible and backward compatible before merging. Use when a PR touches a migrations/ file.
---

# DB Migration Check

1. Read the migration file. Confirm it has both `up` and `down` functions
   defined and non-empty.
2. Grep the codebase for the column or table the migration touches. Confirm
   no query assumes the new shape until the migration has actually run (no
   same-PR read of a column the migration adds).
3. Check the migration against the reversibility rules in
   [REVERSIBILITY.md](REVERSIBILITY.md).
4. State PASS or FAIL with the specific line that broke a rule, or PASS with
   nothing to report.
EOF
cat > good-skill/REVERSIBILITY.md <<'EOF'
# Reversibility rules

- A column drop must ship in a separate migration from the code that stops
  reading it, at least one deploy apart.
- A rename must add-then-backfill-then-drop across three migrations, never a
  single rename statement.
- `down` must restore the exact prior schema, not a best-effort
  approximation.
EOF
