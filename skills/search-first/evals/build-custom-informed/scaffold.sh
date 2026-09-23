#!/usr/bin/env bash
set -euo pipefail
cat > pyproject.toml <<'EOF'
[project]
name = "desk-etl"
version = "0.1.0"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.26",
]
EOF
