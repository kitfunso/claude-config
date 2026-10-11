"""Freeze the taxi-out replay: April to August 2025 labelled, September and October with departure labels hidden."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SRC = Path("C:/Users/skf_s/prc26-final/data")
TRAIN = ("2025-04-01_2025-05-01", "2025-05-01_2025-06-01", "2025-06-01_2025-07-01",
         "2025-07-01_2025-08-01", "2025-08-01_2025-09-01")
TEST = ("2025-09-01_2025-10-01", "2025-10-01_2025-11-01")
# The competition's ranking file hides exactly these two columns on departure rows.
HIDDEN = ("BLOCK_TIME_UTC_mvt", "TAXITIME_SEC_mvt")


def months(names: tuple[str, ...]) -> pd.DataFrame:
    return pd.concat([pd.read_parquet(SRC / f"training_{m}.parquet") for m in names], ignore_index=True)


def naive(train: pd.DataFrame, test_dep: pd.DataFrame) -> pd.DataFrame:
    dep = train[train["PHASE_mvt"] == "DEP"]
    by_airport = dep.groupby("ADEP_mvt")["TAXITIME_SEC_mvt"].mean()
    pred = test_dep["ADEP_mvt"].map(by_airport).fillna(dep["TAXITIME_SEC_mvt"].mean())
    return pd.DataFrame({"MVT_ID_mvt": test_dep["MVT_ID_mvt"], "pred": pred})


def main(cache: Path) -> None:
    public, private = cache / "public", cache / "private"
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    train, test = months(TRAIN), months(TEST)
    dep = test["PHASE_mvt"] == "DEP"
    test.loc[dep, ["MVT_ID_mvt", "ADEP_mvt", "TAXITIME_SEC_mvt"]].to_parquet(private / "truth.parquet")
    naive(train, test.loc[dep]).to_parquet(private / "naive.parquet")
    test.loc[dep, list(HIDDEN)] = None
    train.to_parquet(public / "train.parquet")
    test.to_parquet(public / "test.parquet")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
