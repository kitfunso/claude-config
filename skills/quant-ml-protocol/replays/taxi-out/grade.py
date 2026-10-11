"""Score a taxi-out submission: RMSE in seconds on the hidden departures, missing rows filled with the naive."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def rmse(truth: pd.Series, pred: pd.Series) -> float:
    return float(np.sqrt(np.mean((truth.to_numpy(float) - pred.to_numpy(float)) ** 2)))


def grade(submission: Path, private: Path) -> dict[str, object]:
    truth = pd.read_parquet(private / "truth.parquet")
    base = truth.merge(pd.read_parquet(private / "naive.parquet"), on="MVT_ID_mvt")
    out: dict[str, object] = {"metric": "rmse_s", "lower_is_better": True, "n": len(truth),
                              "naive": rmse(base["TAXITIME_SEC_mvt"], base["pred"])}
    try:
        sub = pd.read_csv(submission, usecols=["MVT_ID_mvt", "TAXITIME_SEC_mvt"])
    except (OSError, ValueError) as e:
        return {**out, "value": None, "valid": False, "note": f"unreadable submission: {e}"}
    sub = sub.dropna().drop_duplicates("MVT_ID_mvt").rename(columns={"TAXITIME_SEC_mvt": "sub"})
    scored = base.merge(sub, on="MVT_ID_mvt", how="left")
    coverage = float(scored["sub"].notna().mean())
    pred = scored["sub"].fillna(scored["pred"])
    return {**out, "value": rmse(scored["TAXITIME_SEC_mvt"], pred), "valid": coverage > 0,
            "note": f"coverage {coverage:.3f}"}


if __name__ == "__main__":
    print(json.dumps(grade(Path(sys.argv[1]), Path(sys.argv[2]))))
