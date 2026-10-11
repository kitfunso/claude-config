"""Freeze the cross-sectional signal replay: the hourly panel up to 12 monthly releases before the end is public."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from grade import EMBARGO, relabel

SRC = Path("C:/Users/skf_s/alphanova/comp6_scientist_release/data/train")
# Release files are cumulative and calendar-monthly: 031 holds the whole history, 019 ends exactly 365 days earlier.
LATEST, CUT_AT = "031", "019"
# Lives here, never in grade.py, because grade.py ships to the run as evaluate.py.
GRADE_SEED = 20260630
BASE_CLASS = '''"""Base class for submissions: subclass it and implement train() and predict()."""
from abc import ABC, abstractmethod

import pandas as pd


class Predictor(ABC):
    @abstractmethod
    def train(self, features: pd.DataFrame, target: pd.DataFrame) -> None:
        """features: hourly rows, MultiIndex columns (feature, ticker). target: the same rows, one column per ticker."""

    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """One row per input row, one column per ticker, de-meaned across tickers in every row."""
'''


def main(cache: Path) -> None:
    public, private = cache / "public", cache / "private"
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    feats, rets, target = (pd.read_parquet(SRC / f"{LATEST}.small.{n}.parquet")
                           for n in ("features", "returns", "target"))
    cut = pq.ParquetFile(SRC / f"{CUT_AT}.small.returns.parquet").metadata.num_rows
    start = cut - EMBARGO
    feats.iloc[:cut].to_parquet(public / "features.parquet")
    rets.iloc[:cut].to_parquet(public / "returns.parquet")
    target.iloc[:start].to_parquet(public / "target.parquet")
    (public / "predictor.py").write_text(BASE_CLASS, encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("grade.py"), public / "evaluate.py")
    feats.iloc[:start].to_parquet(private / "train_features.parquet")
    target.iloc[:start].to_parquet(private / "train_target.parquet")
    relabel(feats.iloc[start:], GRADE_SEED).to_parquet(private / "predict_features.parquet")
    relabel(rets.iloc[cut:], GRADE_SEED).to_parquet(private / "heldout_returns.parquet")
    (private / "predictor.py").write_text(BASE_CLASS, encoding="utf-8")
    meta = {"rows_total": len(feats), "cut": cut, "train_rows": start, "heldout_rows": len(feats) - cut,
            "embargo": EMBARGO, "release": LATEST, "cut_release": CUT_AT}
    (private / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
