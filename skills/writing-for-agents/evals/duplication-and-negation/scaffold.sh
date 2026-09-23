#!/usr/bin/env bash
set -euo pipefail
mkdir -p rules
cat > AGENTS.md <<'EOF'
# Agent Rules

These apply to every agent run in this repo, not just this one PR.

## Comments
Comments should explain why, not what. Keep them short. A comment that
restates the line below it wastes the reader's time twice.

## Code quality
Don't write vague code. Don't use bad variable names. Don't skip error
handling. Don't forget edge cases. Review your own diff before opening a PR.

See rules/style.md for the full style guide.
EOF
cat > rules/style.md <<'EOF'
# Style Guide

This file is the detailed version; AGENTS.md carries only the summary.

## Comments
Write comments that explain the reasoning behind a non-obvious choice, not a
restatement of the code. One or two lines. A three-line comment usually means
the code itself needs a rename.

## Naming
Use descriptive names for variables and functions. A name should tell a
reader what the value holds without needing the surrounding lines.
EOF
