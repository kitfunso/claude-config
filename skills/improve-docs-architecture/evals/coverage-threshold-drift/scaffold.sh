#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs
cat > CLAUDE.md <<'EOF'
# Project Rules

## Testing
- Use pytest. Minimum coverage: 80%. Run `pytest --cov` before every commit.
- Mock external APIs with unittest.mock.

## Git
- Commit format: `<type>: <description>`.
- Never force-push main.
EOF
cat > docs/TESTING.md <<'EOF'
# Testing Guide

We use pytest for all tests. The coverage gate is 90% — CI fails under that.
Run `pytest --cov=src --cov-report=term-missing` locally before pushing.

Mock all external API calls with unittest.mock so tests don't hit the network.
EOF
cat > docs/INDEX.md <<'EOF'
# Docs Index

- [TESTING.md](TESTING.md): everything about running and writing tests, coverage
  thresholds, how to mock APIs, how CI enforces the gate, and what to do when a
  test flakes locally versus in CI.
- [CLAUDE.md](../CLAUDE.md): the project rules file, loaded every session.
EOF
