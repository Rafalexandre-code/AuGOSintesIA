"""
TabPFN-based classifier with GPC-compatible interface.

Falls back to calibrated GradientBoosting if TabPFN is unavailable.
"""

import importlib
from typing import Optional

import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV

try:
    _mod = importlib.import_module("tabpfn")
    if hasattr(_mod, "TabPFNClassifier") and getattr(_mod, "__file__", None) != __file__:
        from tabpfn import TabPFNClassifier as _TabPFN

        _HAVE_TABPFN = True
    else:
        _HAVE_TABPFN = False
except Exception:
    _HAVE_TABPFN = False


class TabPFNClassifier:
    """
    TabPFN-based classifier with unified interface.

    Methods: create_model, fit, predict, sample_model, probability_model, variance_model
    Input: list of dicts with 'coordination' (list[float]) and 'label' (int)
    """

    def __init__(
        self, train, test, random_state: int = 52, calibration: str = "isotonic"
    ):
        self.train = train
        self.test = test
        self.random_state = random_state
        self.calibration = calibration

        if len(self.train) > 0:
            d = len(self.train[0]["coordination"])
        else:
            d = 0

        def _xy_from_list(lst, d_):
            xs, ys = [], []
            for r in lst:
                yv = r.get("label", None)
                if yv is None:
                    continue
                xs.append(r["coordination"])
                ys.append(int(yv))
            X = (
                np.asarray(xs, dtype=float).reshape(-1, d_)
                if (d_ > 0 and len(xs) > 0)
                else (np.empty((0, d_)) if d_ > 0 else np.empty((0, 0)))
            )
            y = (
                np.asarray(ys, dtype=int).ravel()
                if len(ys) > 0
                else np.empty((0,), dtype=int)
            )
            return X, y

        self.x_train, self.y_train = _xy_from_list(self.train, d)

        if len(self.test) > 0:
            d2 = len(self.test[0]["coordination"])
        else:
            d2 = d
        self.x_test, self.y_test = _xy_from_list(self.test, d2)

        self.model = None
        self._use_tabpfn = _HAVE_TABPFN

    def create_model(self):
        if self._use_tabpfn:
            try:
                self.model = _TabPFN(device="cpu", random_state=self.random_state)
            except TypeError:
                try:
                    self.model = _TabPFN(random_state=self.random_state)
                except TypeError:
                    try:
                        self.model = _TabPFN(
                            (self.x_train, self.y_train), (self.x_test, self.y_test)
                        )
                    except Exception:
                        self._use_tabpfn = False
                        base = GradientBoostingClassifier(random_state=self.random_state)
                        self.model = CalibratedClassifierCV(
                            estimator=base, cv=3, method=self.calibration
                        )
        else:
            base = GradientBoostingClassifier(random_state=self.random_state)
            self.model = CalibratedClassifierCV(
                estimator=base, cv=3, method=self.calibration
            )

    def fit(self):
        assert self.model is not None, "Call create_model() before fit()"
        if self.x_train.shape[0] == 0:
            raise ValueError("Training data is empty.")
        self.model.fit(self.x_train, self.y_train)

    def predict(self) -> float:
        assert self.model is not None, "Model not created. Call create_model()"
        if self.x_test.shape[0] == 0:
            return 0.0
        y_pred = self.model.predict(self.x_test)
        return accuracy_score(self.y_test, y_pred)

    def sample_model(self, x_new):
        assert self.model is not None, "Model not created. Call create_model()"
        X = self._to_2d_array(x_new)
        return self.model.predict(X)

    def probability_model(self, x_new):
        assert self.model is not None, "Model not created. Call create_model()"
        X = self._to_2d_array(x_new)
        return self.model.predict_proba(X)

    def variance_model(self, x_new):
        """Return uncertainty via predictive entropy. Shape: (N,)"""
        P = self.probability_model(x_new)
        eps = 1e-12
        ent = -np.sum(P * np.log(P + eps), axis=1)
        return ent

    @staticmethod
    def _to_2d_array(x):
        if isinstance(x, np.ndarray):
            X = x
        else:
            X = np.asarray(x, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        return X.astype(float)
