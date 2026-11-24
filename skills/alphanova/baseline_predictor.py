import numpy as np
import pandas as pd

import lightgbm as lgb

from predictor import Predictor


class BaselinePredictor(Predictor):
    SPAN = 96
    TILT_K = 1.0
    EMBARGO = 120
    PARAMS = {
        "objective": "regression",
        "max_depth": 3,
        "num_leaves": 7,
        "learning_rate": 0.05,
        "min_data_in_leaf": 500,
        "lambda_l2": 5.0,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "verbosity": -1,
        "num_threads": 4,
        "seed": 7,
    }
    N_ROUNDS = 40

    def __init__(self):
        self.model = None

    @staticmethod
    def _csrank(df: pd.DataFrame) -> pd.DataFrame:
        r = df.rank(axis=1)
        n = df.notna().sum(axis=1).values.reshape(-1, 1)
        return (r - 0.5 * (n + 1)) / (0.5 * np.maximum(n - 1, 1))

    def _blocks(self, features: pd.DataFrame) -> dict:
        g = {i: features[f"Feature.{i}"] for i in range(1, 7)}
        rk = {i: self._csrank(g[i]) for i in range(1, 7)}
        ext = self._csrank(sum(rk[i].abs() for i in (1, 2, 3, 4)))
        b = {}
        b["ext"] = ext
        b["f5"] = rk[5]
        b["f6"] = rk[6]
        b["ext_x_f5"] = ext * rk[5]
        b["ext_x_f6"] = ext * rk[6]
        b["sp13"] = self._csrank(g[1] - g[3])
        b["sp34"] = self._csrank(g[3] - g[4])
        b["ext2"] = ext * ext
        return b

    def _design(self, features: pd.DataFrame):
        b = self._blocks(features)
        tickers = list(b["ext"].columns)
        X = np.hstack([d[tickers].values.reshape(-1, 1) for d in b.values()])
        return X, tickers, b["ext"].index

    def train(self, features: pd.DataFrame, target: pd.DataFrame) -> None:
        live = target.abs().sum(axis=1) > 0
        live.iloc[-self.EMBARGO:] = False
        features, target = features.loc[live], target.loc[live]
        X, tickers, _ = self._design(features)
        y = target[tickers].values.reshape(-1)
        ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
        self.model = lgb.train(
            self.PARAMS,
            lgb.Dataset(X[ok], label=y[ok]),
            num_boost_round=self.N_ROUNDS,
        )

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        assert self.model is not None, "Must call train() before predict()"
        X, tickers, index = self._design(features)
        raw = self.model.predict(np.nan_to_num(X))
        sig = pd.DataFrame(
            raw.reshape(-1, len(tickers)), index=index, columns=tickers
        )
        sig = sig.ewm(span=self.SPAN, min_periods=1).mean()
        tilt = sig.shift(1).expanding(min_periods=1).mean()
        sig = (sig - self.TILT_K * tilt).fillna(0.0)
        sig = sig.sub(sig.mean(axis=1), axis=0)
        return sig.fillna(0.0)
