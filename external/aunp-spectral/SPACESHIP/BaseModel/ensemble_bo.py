"""
Ensemble Bayesian Optimization Classifier

Combines GP (ExactGPModel), RandomForest, and XGBoost/GradientBoosting
with dynamic weighting based on validation log-loss.
"""

import os
import sys
from typing import Optional, List, Tuple

import numpy as np
import torch
import gpytorch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from baseGP import ExactGPModel

try:
    from sklearn.ensemble import RandomForestClassifier

    _HAVE_SKLEARN = True
except Exception:
    _HAVE_SKLEARN = False

try:
    from xgboost import XGBClassifier as _XGBClassifier

    _HAVE_XGB = True
except Exception:
    try:
        from xgboost.sklearn import XGBClassifier as _XGBClassifier

        _HAVE_XGB = True
    except Exception:
        _HAVE_XGB = False

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, accuracy_score


class EnsembleBO:
    """
    Ensemble classifier combining GP + RandomForest + XGBoost.

    Provides the same interface as GPC:
    - create_model, fit, predict, sample_model, probability_model, variance_model
    - Input: train/test as [{'coordination': [...], 'label': int}, ...]
    """

    def __init__(self, train, test):
        self.train = train
        self.test = test
        torch.manual_seed(52)

        datasize = len(train[0]["coordination"])

        self.x_train = torch.Tensor(
            np.array([i["coordination"] for i in train]).reshape(-1, datasize)
        )
        self.x_test = torch.Tensor(
            np.array([i["coordination"] for i in test]).reshape(-1, datasize)
        )

        self.y_train_raw = torch.Tensor(
            np.array([i["label"] for i in train]).reshape(-1, 1)
        )
        self.y_test_raw = torch.Tensor(
            np.array([i["label"] for i in test]).reshape(-1, 1)
        )

        self.y_train = (
            torch.nn.functional.one_hot(self.y_train_raw.long(), num_classes=3)
            .float()
            .squeeze(1)
        )
        self.y_test = torch.nn.functional.one_hot(
            self.y_test_raw.long(), num_classes=3
        ).float()

        self.model: Optional[ExactGPModel] = None
        self.likelihood: Optional[gpytorch.likelihoods.MultitaskGaussianLikelihood] = (
            None
        )
        self.K = 3

        self.rf = (
            RandomForestClassifier(
                n_estimators=600,
                min_samples_leaf=2,
                max_features="sqrt",
                class_weight="balanced_subsample",
                random_state=52,
                n_jobs=-1,
            )
            if _HAVE_SKLEARN
            else None
        )

        self.xgb = (
            _XGBClassifier(
                n_estimators=600,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.8,
                reg_lambda=1.0,
                n_jobs=-1,
                tree_method="hist",
                eval_metric="logloss",
                random_state=52,
            )
            if _HAVE_XGB
            else GradientBoostingClassifier(random_state=52)
        )

        self.weights_: Optional[np.ndarray] = None

    def create_model(self):
        num_tasks = self.y_train.shape[1]
        self.likelihood = gpytorch.likelihoods.MultitaskGaussianLikelihood(
            num_tasks=num_tasks
        )
        self.model = ExactGPModel(
            self.x_train, self.y_train, self.likelihood, num_tasks=num_tasks
        )

    def fit(self):
        self.model.train()
        likelihood = self.model.likelihood
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.1)
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, self.model)

        for _ in range(50):
            optimizer.zero_grad()
            output = self.model(self.x_train)
            loss = -mll(output, self.y_train)
            loss.backward()
            optimizer.step()

        if self.rf is not None:
            X_np = self.x_train.detach().cpu().numpy()
            y_np = self.y_train_raw.detach().cpu().numpy().ravel().astype(int)
            if len(np.unique(y_np)) >= 2:
                self.rf.fit(X_np, y_np)

        if self.xgb is not None:
            X_np = self.x_train.detach().cpu().numpy()
            y_np = self.y_train_raw.detach().cpu().numpy().ravel().astype(int)
            if len(np.unique(y_np)) >= 2 and X_np.shape[0] > 0:
                try:
                    self.xgb.fit(X_np, y_np)
                except Exception:
                    pass

        try:
            self._calc_dynamic_weights()
        except Exception:
            self.weights_ = None

    def _gp_predict_dist(self, X_tensor: torch.Tensor):
        self.model.eval()
        likelihood = self.model.likelihood
        with torch.no_grad():
            output = self.model(X_tensor)
            observed_pred = likelihood(output)
        return observed_pred

    def _ensure_rf_fitted(self) -> bool:
        if self.rf is None:
            return False
        if hasattr(self.rf, "classes_"):
            return True
        if (
            self.x_train is None
            or self.y_train_raw is None
            or len(self.x_train) == 0
        ):
            return False
        X_np = self.x_train.detach().cpu().numpy()
        y_np = self.y_train_raw.detach().cpu().numpy().ravel().astype(int)
        if len(np.unique(y_np)) < 2:
            return False
        try:
            self.rf.fit(X_np, y_np)
            return True
        except Exception:
            return False

    def _rf_proba(self, X_np: np.ndarray) -> Optional[np.ndarray]:
        if self.rf is None:
            return None
        if not self._ensure_rf_fitted():
            return None
        try:
            proba = self.rf.predict_proba(X_np)
        except Exception:
            if not self._ensure_rf_fitted():
                return None
            proba = self.rf.predict_proba(X_np)
        K = self.K
        out = np.zeros((X_np.shape[0], K), dtype=float)
        for i, cls in enumerate(self.rf.classes_.astype(int)):
            if 0 <= cls < K:
                out[:, cls] = proba[:, i]
        row_sum = out.sum(axis=1, keepdims=True)
        row_sum[row_sum == 0] = 1.0
        return out / row_sum

    def _xgb_proba(self, X_np: np.ndarray) -> Optional[np.ndarray]:
        if self.xgb is None:
            return None
        try:
            proba = self.xgb.predict_proba(X_np)
        except Exception:
            return None
        K = self.K
        classes = getattr(self.xgb, "classes_", None)
        if classes is None:
            if proba.shape[1] == K:
                out = proba
            else:
                out = np.zeros((X_np.shape[0], K), dtype=float)
                out[:, : proba.shape[1]] = proba
            row_sum = out.sum(axis=1, keepdims=True)
            row_sum[row_sum == 0] = 1.0
            return out / row_sum
        out = np.zeros((X_np.shape[0], K), dtype=float)
        for i, cls in enumerate(classes.astype(int)):
            if 0 <= cls < K:
                out[:, cls] = proba[:, i]
        row_sum = out.sum(axis=1, keepdims=True)
        row_sum[row_sum == 0] = 1.0
        return out / row_sum

    def _softmax(self, Z: np.ndarray, T: float = 1.0) -> np.ndarray:
        Z = Z / max(T, 1e-6)
        Z = Z - Z.max(axis=1, keepdims=True)
        E = np.exp(Z)
        S = E.sum(axis=1, keepdims=True)
        S[S == 0] = 1.0
        return E / S

    def _gp_prob(self, X_tensor: torch.Tensor) -> np.ndarray:
        gp_pred = self._gp_predict_dist(X_tensor)
        gp_mean = gp_pred.mean.detach().cpu().numpy()
        return self._softmax(gp_mean, T=1.0)

    def _calc_dynamic_weights(self) -> None:
        """Calculate dynamic weights [w_gp, w_rf, w_xgb] using inverse log-loss."""
        X = self.x_train.detach().cpu().numpy()
        y = self.y_train_raw.detach().cpu().numpy().ravel().astype(int)
        if len(np.unique(y)) < 2 or X.shape[0] < 10:
            self.weights_ = None
            return
        X_tr, X_va, y_tr, y_va = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=52
        )

        X_va_t = torch.tensor(X_va, dtype=torch.float32)
        P_gp = self._gp_prob(X_va_t)

        P_rf = self._rf_proba(X_va) if self.rf is not None else None
        P_xg = self._xgb_proba(X_va) if self.xgb is not None else None

        losses: List[Tuple[str, float]] = []
        labels = list(range(self.K))
        try:
            losses.append(("gp", float(log_loss(y_va, P_gp, labels=labels))))
        except Exception:
            pass
        if P_rf is not None:
            try:
                losses.append(("rf", float(log_loss(y_va, P_rf, labels=labels))))
            except Exception:
                pass
        if P_xg is not None:
            try:
                losses.append(("xg", float(log_loss(y_va, P_xg, labels=labels))))
            except Exception:
                pass
        if not losses:
            self.weights_ = None
            return
        inv = np.array([1.0 / max(l, 1e-9) for _, l in losses], dtype=float)
        w = inv / inv.sum()
        w_map = {name: w[i] for i, (name, _) in enumerate(losses)}
        self.weights_ = np.array(
            [
                w_map.get("gp", 0.0),
                w_map.get("rf", 0.0),
                w_map.get("xg", 0.0),
            ],
            dtype=float,
        )

    def _ensemble_prob(self, X_tensor: torch.Tensor) -> np.ndarray:
        X_np = X_tensor.detach().cpu().numpy()
        P_gp = self._gp_prob(X_tensor)
        P_rf = self._rf_proba(X_np)
        P_xg = self._xgb_proba(X_np)

        comps: List[np.ndarray] = []
        comp_names: List[str] = []
        if P_gp is not None:
            comps.append(P_gp)
            comp_names.append("gp")
        if P_rf is not None:
            comps.append(P_rf)
            comp_names.append("rf")
        if P_xg is not None:
            comps.append(P_xg)
            comp_names.append("xg")
        if not comps:
            return P_gp

        if self.weights_ is None:
            w = np.ones(len(comps), dtype=float) / len(comps)
        else:
            w_all = {
                "gp": self.weights_[0] if self.weights_ is not None else 0.0,
                "rf": self.weights_[1] if self.weights_ is not None else 0.0,
                "xg": self.weights_[2] if self.weights_ is not None else 0.0,
            }
            w = np.array([w_all.get(n, 0.0) for n in comp_names], dtype=float)
            if w.sum() <= 0:
                w = np.ones(len(comps), dtype=float) / len(comps)
            else:
                w = w / w.sum()

        P = np.zeros_like(comps[0])
        for wi, Pi in zip(w, comps):
            P += wi * Pi
        s = P.sum(axis=1, keepdims=True)
        s[s == 0] = 1.0
        return P / s

    def _ensemble_variance(self, X_tensor: torch.Tensor) -> np.ndarray:
        P = self._ensemble_prob(X_tensor)
        eps = 1e-12
        ent = -np.sum(P * np.log(P + eps), axis=1)
        return ent

    # Public API
    def predict(self):
        probs = self._ensemble_prob(self.x_test)
        pred_classes = np.argmax(probs, axis=-1)
        true_classes = self.y_test.detach().cpu().numpy()
        return accuracy_score(true_classes, pred_classes)

    def sample_model(self, x_new):
        x_new_tensor = torch.Tensor(np.array(x_new))
        probs = self._ensemble_prob(x_new_tensor)
        return np.argmax(probs, axis=-1)

    def probability_model(self, x_new):
        x_new_tensor = torch.Tensor(np.array(x_new))
        return self._ensemble_prob(x_new_tensor)

    def variance_model(self, x_new):
        x_new_tensor = torch.Tensor(np.array(x_new))
        return self._ensemble_variance(x_new_tensor)

    # Diagnostics
    def rf_status(self) -> dict:
        """Return RF participation/fit status."""
        exists = self.rf is not None
        fitted = bool(exists and hasattr(self.rf, "classes_"))
        n_estimators = int(len(getattr(self.rf, "estimators_", []))) if exists else 0
        classes = list(getattr(self.rf, "classes_", [])) if fitted else None
        return {
            "exists": exists,
            "fitted": fitted,
            "classes": classes,
            "n_estimators": n_estimators,
        }

    def proba_components(self, x_new) -> dict:
        """Return separate GP, RF, and ensemble probabilities."""
        x_new_tensor = torch.Tensor(np.array(x_new))
        gp_pred = self._gp_predict_dist(x_new_tensor)
        gp_mean = gp_pred.mean.detach().cpu().numpy()
        gp_mean = np.maximum(gp_mean, 0.0)
        s = gp_mean.sum(axis=1, keepdims=True)
        s[s == 0] = 1.0
        gp_prob = gp_mean / s

        rf_prob = None
        if self.rf is not None:
            rf_prob = self._rf_proba(x_new_tensor.detach().cpu().numpy())

        ens_prob = 0.5 * gp_prob + 0.5 * rf_prob if rf_prob is not None else gp_prob
        s2 = ens_prob.sum(axis=1, keepdims=True)
        s2[s2 == 0] = 1.0
        ens_prob = ens_prob / s2
        return {"gp_prob": gp_prob, "rf_prob": rf_prob, "ens_prob": ens_prob}

    def debug_summary(self, x_new=None, n_samples: int = 5) -> dict:
        """Quick summary for debugging."""
        status = self.rf_status()
        if x_new is None:
            try:
                x_new = self.x_test[:n_samples]
            except Exception:
                x_new = []
        comps = self.proba_components(x_new)
        gp = comps["gp_prob"]
        ens = comps["ens_prob"]
        mad = (
            float(np.abs(ens - gp).mean())
            if gp is not None and ens is not None
            else None
        )
        return {"rf_status": status, "mean_abs_diff_ens_vs_gp": mad}
