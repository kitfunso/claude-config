#!/usr/bin/env bash
set -euo pipefail
mkdir -p draft-skill
cat > draft-skill/SKILL.md <<'EOF'
---
name: run-tests
description: Run the test suite for this repo and report failures. Use when the user asks to run tests.
---

# Run Tests

Be careful and thorough. Think step by step before acting. Always double-check
your work.

## Steps

1. Run the test suite. The test command is `npm test` (as defined in
   package.json's "scripts" section, which currently reads
   `"test": "vitest run"`).
2. Read the output carefully.
3. Report the results to the user in a clear and well-organized way.
4. If tests fail, understanding is reached once you've looked at the failure.
EOF
cat > package.json <<'EOF'
{
  "name": "desk-app",
  "scripts": {
    "test": "vitest run"
  }
}
EOF
