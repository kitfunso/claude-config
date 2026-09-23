#!/usr/bin/env bash
set -euo pipefail
cat > fetch_prices.py <<'EOF'
"""Fetch desk prices and store them, or preview with --dry-run."""
import argparse


def fetch_and_store(dry_run: bool = False) -> None:
    rows = _fetch()
    if dry_run:
        print(f"[dry-run] would store {len(rows)} rows")
        return
    _store(rows)


def _fetch() -> list[dict]:
    return [{"symbol": "MOG92", "price": 91.4}]


def _store(rows: list[dict]) -> None:
    pass  # writes to the desk db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fetch_and_store(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
EOF
