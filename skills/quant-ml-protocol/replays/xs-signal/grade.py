"""Score a predictor submission: train on the public span, predict the held-out hours, per-hour Sharpe net of 5 bp.

grade.py <submission.py> <private_dir>    the replay grade
evaluate.py <submission.py> --local       the same procedure on the public data (this file ships as evaluate.py)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

COST = 0.0005
# The public target stops this many hours before the features, so no training label sees a scored hour.
EMBARGO = 240
TRAIN_LIMIT_S, PREDICT_LIMIT_S = 240.0, 60.0
# Runs and grading share one box, often in parallel, so the stated limits get 25% headroom before they fail a run.
SLACK = 1.25
CHILD_TIMEOUT_S = 900
LOCAL_SEED = 7
LOCAL_HOLDOUT = 8760


def relabel(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Rename tickers by one seeded shuffle, the same in features and returns, then restore the usual column order."""
    multi = isinstance(frame.columns, pd.MultiIndex)
    names = sorted(set(frame.columns.get_level_values(-1)), key=lambda s: int(s.split(".")[-1]))
    mapping = dict(zip(names, np.random.default_rng(seed).permutation(names).tolist()))
    out = frame.rename(columns=mapping, level=1 if multi else None)
    return out.sort_index(axis=1) if multi else out[names]


def tickers(features: pd.DataFrame) -> list[str]:
    return sorted(set(features.columns.get_level_values(-1)), key=lambda s: int(s.split(".")[-1]))


def sharpe(pred: np.ndarray, rets: np.ndarray, start: int) -> float:
    """Sharpe of r(i) = <P(i-1), X(i)> - c |P(i-1) - P(i-2)|_1 over rows start.. of the predict call."""
    p = pd.DataFrame(pred).ffill().fillna(0.0).to_numpy()
    held, before = p[start - 1:-1], p[start - 2:-2]
    r = (held * rets).sum(axis=1) - COST * np.abs(held - before).sum(axis=1)
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else 0.0


def probe_rows(m: int) -> tuple[int, ...]:
    return (EMBARGO + 1, EMBARGO + (m - EMBARGO) // 2, m - 1)


def pick_class(module: object) -> type:
    found = [c for c in vars(module).values() if isinstance(c, type) and c.__module__ == "submission"
             and callable(getattr(c, "train", None)) and callable(getattr(c, "predict", None))]
    preferred = [c for c in found if any(b.__name__ == "Predictor" for b in c.__mro__[1:])]
    if not found:
        raise ValueError("no class with train() and predict() in the submission")
    return (preferred or found)[0]


def as_matrix(pred: object, rows: int, names: list[str]) -> np.ndarray:
    if not isinstance(pred, pd.DataFrame):
        raise ValueError(f"predict() returned {type(pred).__name__}, not a DataFrame")
    if len(pred) != rows or set(map(str, pred.columns)) != set(names):
        raise ValueError(f"predict() gave shape {pred.shape}; expected {rows} rows and the {len(names)} ticker columns")
    values = pred.set_axis(list(map(str, pred.columns)), axis=1)[names].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("predict() returned infinite values")
    return values


def child(work: Path) -> None:
    """Runs inside the subprocess: load, train, predict, re-predict on prefixes, write numbers only."""
    out: dict[str, object] = {}
    try:
        os.chdir(work)
        # Drop this script's own folder so a submission resolves imports the same locally and in grading.
        sys.path[0] = str(work)
        spec = importlib.util.spec_from_file_location("submission", work / "submission.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["submission"] = module
        spec.loader.exec_module(module)
        model = pick_class(module)()
        feats, target = pd.read_parquet("train_features.parquet"), pd.read_parquet("train_target.parquet")
        t0 = time.perf_counter()
        model.train(feats, target)
        out["train_s"] = time.perf_counter() - t0
        del feats, target
        pf = pd.read_parquet("predict_features.parquet")
        names = tickers(pf)
        t0 = time.perf_counter()
        pred = model.predict(pf.copy())
        out["predict_s"] = time.perf_counter() - t0
        out["worst_row_mean"] = float(pred.mean(axis=1).abs().max()) if isinstance(pred, pd.DataFrame) else None
        full = as_matrix(pred, len(pf), names)
        scale = max(float(np.nanmax(np.abs(full), initial=0.0)), 1e-12)
        diffs = []
        for k in probe_rows(len(pf)):
            part = as_matrix(model.predict(pf.iloc[:k].copy()), k, names)
            diffs.append(float(np.nanmax(np.abs(part - full[:k]), initial=0.0)) / scale)
            # A NaN in one call and a number in the other is also a change caused by later rows.
            diffs[-1] += float((np.isnan(part) != np.isnan(full[:k])).any())
        out["probe_rel_diff"] = max(diffs)
        np.save(work / "pred.npy", full)
    except BaseException as e:  # the submission's failure is the result, reported to the parent
        own = [f for f in traceback.extract_tb(e.__traceback__) if f.filename.endswith("submission.py")]
        where = f" (submission.py line {own[-1].lineno})" if own else ""
        out["error"] = f"{type(e).__name__}: {e}"[:400] + where
    (work / "result.json").write_text(json.dumps(out), encoding="utf-8")


def run(submission: Path, data: Path, train_f: pd.DataFrame, train_t: pd.DataFrame,
        predict_f: pd.DataFrame, rets: pd.DataFrame) -> tuple[float | None, str]:
    names = tickers(predict_f)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        work = Path(tmp)
        shutil.copy2(submission, work / "submission.py")
        if (data / "predictor.py").is_file():
            shutil.copy2(data / "predictor.py", work / "predictor.py")
        train_f.to_parquet(work / "train_features.parquet")
        train_t.to_parquet(work / "train_target.parquet")
        predict_f.to_parquet(work / "predict_features.parquet")
        try:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child", str(work)], cwd=work,
                           capture_output=True, timeout=CHILD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return None, f"killed after {CHILD_TIMEOUT_S} s"
        if not (work / "result.json").is_file():
            return None, "the scoring process died without a result (out of memory or a hard crash)"
        res = json.loads((work / "result.json").read_text(encoding="utf-8"))
        if "error" in res:
            return None, res["error"]
        timing = f"train {res['train_s']:.0f} s, predict {res['predict_s']:.1f} s"
        if res["train_s"] > TRAIN_LIMIT_S * SLACK or res["predict_s"] > PREDICT_LIMIT_S * SLACK:
            return None, f"too slow: {timing} (limits {TRAIN_LIMIT_S:.0f} s and {PREDICT_LIMIT_S:.0f} s)"
        if not res["worst_row_mean"] < 1e-6:
            return None, f"not de-meaned: worst row mean {res['worst_row_mean']}"
        if res["probe_rel_diff"] > 1e-5:
            return None, f"looks ahead: predictions changed when later rows were removed (rel diff {res['probe_rel_diff']:.2g})"
        value = sharpe(np.load(work / "pred.npy"), rets[names].to_numpy(), EMBARGO)
    if not np.isfinite(value):
        return None, f"non-finite Sharpe; {timing}"
    return value, f"{timing}, look-ahead probes clean"


def load(data: Path, local: bool, holdout: int) -> tuple[pd.DataFrame, ...]:
    """(train features, train target, predict features, scored returns), the same shape in both modes."""
    if not local:
        return tuple(pd.read_parquet(data / f"{n}.parquet")
                     for n in ("train_features", "train_target", "predict_features", "heldout_returns"))
    feats, target, rets = (pd.read_parquet(data / f"{n}.parquet") for n in ("features", "target", "returns"))
    cut = len(feats) - holdout
    start = cut - EMBARGO
    return (feats.iloc[:start], target.iloc[:start], relabel(feats.iloc[start:], LOCAL_SEED),
            relabel(rets.iloc[cut:], LOCAL_SEED))


def grade(submission: Path, data: Path, local: bool = False, holdout: int = LOCAL_HOLDOUT) -> dict[str, object]:
    train_f, train_t, predict_f, rets = load(data, local, holdout)
    naive = sharpe(np.zeros((len(predict_f), rets.shape[1])), rets.to_numpy(), EMBARGO)
    out: dict[str, object] = {"metric": "sharpe_hourly_net_5bp", "lower_is_better": False, "naive": naive,
                              "n": len(rets)}
    if not submission.is_file():
        return {**out, "value": None, "valid": False, "note": f"no submission file at {submission}"}
    try:
        value, note = run(submission, data, train_f, train_t, predict_f, rets)
    except Exception as e:  # a grader fault on odd input still has to produce the one JSON line
        value, note = None, f"grader error: {type(e).__name__}: {e}"[:400]
    return {**out, "value": value, "valid": value is not None, "note": note}


def main(argv: list[str]) -> int:
    if argv[:1] == ["--child"]:
        child(Path(argv[1]))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("submission", type=Path)
    ap.add_argument("data", type=Path, nargs="?", help="private dir (grade) or public data dir (--local)")
    ap.add_argument("--local", action="store_true", help="hold out the tail of the public data instead")
    ap.add_argument("--holdout", type=int, default=LOCAL_HOLDOUT, help="hours held out in --local mode")
    a = ap.parse_args(argv)
    data = a.data or Path(__file__).resolve().parent
    print(json.dumps(grade(a.submission, data, a.local, a.holdout)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
