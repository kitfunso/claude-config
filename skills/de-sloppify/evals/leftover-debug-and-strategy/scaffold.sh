#!/usr/bin/env bash
set -euo pipefail
cat > feature.py <<'EOF'
"""Compute the weekly freight adjustment for the arb sheet."""
import numpy as np  # unused, leftover from an earlier draft
import pandas as pd


def compute_adjustment(df):
    # old version used a fixed 2.10 flat rate, keeping for reference
    # return df["price"] - 2.10
    print("DEBUG: df shape", df.shape)
    temp = df.copy()
    temp["adj"] = temp["price"] - temp["freight"]
    print("adj computed:", temp["adj"].head())
    return temp


class AdjustmentStrategy:
    """Strategy interface for computing adjustments (future: support other strategies)."""

    def compute(self, df):
        raise NotImplementedError


class FlatFreightStrategy(AdjustmentStrategy):
    def compute(self, df):
        return compute_adjustment(df)
EOF
