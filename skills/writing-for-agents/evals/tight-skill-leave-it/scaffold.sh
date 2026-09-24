#!/usr/bin/env bash
set -euo pipefail
mkdir -p good-skill
cat > good-skill/SKILL.md <<'EOF'
---
name: db-migration-check
description: DB migration reversibility and backward compatibility. Use when a PR touches a migrations/ file.
---

1. For each migration in the PR, confirm `down` reverses every schema change
   in `up`.
2. If a migration drops or renames a column or table, apply every rule in
   [DROPS-AND-RENAMES.md](DROPS-AND-RENAMES.md).
3. Grep the base branch and the PR branch for every column and table the
   PR's migrations touch, except dropped ones. Confirm each reference to them
   works against both the old and the new schema.
4. State PASS, or FAIL with the specific file and line behind each failure.
EOF
cat > good-skill/DROPS-AND-RENAMES.md <<'EOF'
# Drop and rename rules

- A drop ships only once the code on both the base branch and the PR branch
  has stopped using the column or table.
- A drop is the only operation in its migration.
- A rename follows expand-contract, and this PR carries exactly one of its
  phases.
EOF
