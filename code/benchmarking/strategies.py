#!/usr/bin/env python3
"""Estratégias de referência do benchmark (§4.15), além do Designer (GP + qNEHVI por representação):

  gp-ei      GP Matérn-5/2 + ARD e qLogNEI (Ament et al. 2023) só na perda espectral J — a BO clássica de um objetivo;
  rf-qnehvi  floresta aleatória (cada árvore = um membro de ensemble, `botorch.models.ensemble.EnsembleModel`) com
             qNEHVI nos mesmos objetivos do Designer; a superfície é constante por partes, então a aquisição é
             maximizada sobre 2048 candidatos Sobol (`optimize_acqf_discrete`, gulosa para q > 1);
  random     Sobol (controle sem modelo).
As três usam o MESMO formato de entrada e saída de `designer.propose` (DataFrame com as colunas de `camp.X`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _pool(bounds, cols, fixed: dict, n: int, seed: int):
    from torch.quasirandom import SobolEngine
    pool = bounds[0] + (bounds[1] - bounds[0]) * SobolEngine(len(cols), scramble=True, seed=seed).draw(n).double()
    for k, v in (fixed or {}).items():
        if k in cols:
            pool[:, cols.index(k)] = float(v)
    return pool


def propose_random(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0) -> pd.DataFrame:
    import designer
    cols = list(camp.X.columns)
    return pd.DataFrame(_pool(designer._bounds(camp, space), cols, fixed, q, seed).numpy(), columns=cols)


def propose_gp_ei(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0,
                  objective: str = "spectral_loss_J") -> pd.DataFrame:
    import torch
    from botorch.acquisition.logei import qLogNoisyExpectedImprovement
    from botorch.optim import optimize_acqf
    import designer
    torch.manual_seed(seed)
    names = list(camp.objs.index)
    j = names.index(objective)
    model, tx, _, bounds = designer.build_model(camp, space)
    cols = list(camp.X.columns)
    fixed_idx = {cols.index(k): float(v) for k, v in (fixed or {}).items() if k in cols}
    af = qLogNoisyExpectedImprovement(model.models[j], X_baseline=tx, prune_baseline=True)
    try:
        cand, _ = optimize_acqf(af, bounds, q=q, num_restarts=8, raw_samples=256, fixed_features=fixed_idx or None,
                                sequential=True)
    except (RuntimeError, ValueError):
        from botorch.optim import optimize_acqf_discrete
        cand, _ = optimize_acqf_discrete(af, q=q, choices=_pool(bounds, cols, fixed, 2048, seed))
    return pd.DataFrame(cand.detach().numpy(), columns=cols)


def _rf_model_class():
    import torch
    from botorch.models.ensemble import EnsembleModel

    class RFEnsemble(EnsembleModel):
        """Floresta aleatória multi-saída; cada árvore é um membro do ensemble (posterior = mistura das árvores)."""

        def __init__(self, X: np.ndarray, Y: np.ndarray, n_trees: int = 200, seed: int = 0):
            from sklearn.ensemble import RandomForestRegressor
            super().__init__()
            self.rf = RandomForestRegressor(n_estimators=n_trees, min_samples_leaf=2, max_features=0.6,
                                            random_state=seed).fit(X, Y if Y.shape[1] > 1 else Y.ravel())
            self._num_outputs = Y.shape[1]

        def forward(self, X):
            shape = X.shape[:-1]
            flat = X.reshape(-1, X.shape[-1]).detach().cpu().numpy()
            p = np.stack([t.predict(flat) for t in self.rf.estimators_])         # s × N (× m)
            p = p.reshape(len(p), -1, self._num_outputs)
            v = torch.as_tensor(p, dtype=X.dtype).reshape(len(p), *shape, self._num_outputs)
            return v.movedim(0, -3)                                                # batch × s × n × m
    return RFEnsemble


def propose_rf_qnehvi(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0,
                      n_trees: int = 200, n_pool: int = 2048) -> pd.DataFrame:
    import torch
    from botorch.acquisition.multi_objective import qNoisyExpectedHypervolumeImprovement
    from botorch.optim import optimize_acqf_discrete
    from botorch.sampling.index_sampler import IndexSampler
    import designer
    cols = list(camp.X.columns)
    bounds = designer._bounds(camp, space)
    X = camp.X.to_numpy(float)
    Y = np.asarray(camp.Y, float)
    model = _rf_model_class()(X, Y, n_trees, seed)
    ty = torch.tensor(Y, dtype=torch.double)
    span = (ty.max(0).values - ty.min(0).values).clamp_min(1e-6)
    ref = ty.min(0).values - 0.1 * span
    af = qNoisyExpectedHypervolumeImprovement(model, ref_point=ref, X_baseline=torch.tensor(X, dtype=torch.double),
                                              sampler=IndexSampler(torch.Size([128]), seed=seed),
                                              prune_baseline=False, cache_root=False)
    cand, _ = optimize_acqf_discrete(af, q=q, choices=_pool(bounds, cols, fixed, n_pool, seed), max_batch_size=256)
    return pd.DataFrame(cand.detach().numpy(), columns=cols)
