#!/usr/bin/env python3
"""Estratégias de referência do benchmark (§4.15), além do Designer (GP + qNEHVI por representação):

  gp-ei      GP Matérn-5/2 + ARD e qLogNEI (Ament et al. 2023) só na perda espectral J — a BO clássica de um objetivo;
  rf-qnehvi  floresta aleatória (cada árvore = um membro de ensemble, `botorch.models.ensemble.EnsembleModel`) com
             qNEHVI nos mesmos objetivos do Designer; a superfície é constante por partes, então a aquisição é
             maximizada sobre 2048 candidatos Sobol (`optimize_acqf_discrete`, gulosa para q > 1);
  random     Sobol (controle sem modelo).
Exploratórios da §4.15 (mesma interface):
  dnn-qnehvi    ensemble de 8 redes MLP (sementes distintas) como EnsembleModel + qNEHVI sobre candidatos;
  egbo          Evolution-Guided BO (Low et al. 2024): NSGA-II (pymoo) sobre a média do GP gera candidatos perto da
                frente, e o qNEHVI escolhe entre eles e um conjunto Sobol;
  optuna-tpe    TPE multiobjetivo do Optuna alimentado com o histórico (sem modelo GP);
  (A* não se aplica a um espaço contínuo de receitas; o Olympus fica em external/ como referência de benchmark.)
Todas usam o MESMO formato de entrada e saída de `designer.propose` (DataFrame com as colunas de `camp.X`).
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


def _ensemble_model_class():
    import torch
    from botorch.models.ensemble import EnsembleModel

    class PredictorEnsemble(EnsembleModel):
        """Lista de preditores (cada um: X numpy → n × m) como membros de um EnsembleModel do BoTorch."""

        def __init__(self, predictors: list, m: int):
            super().__init__()
            self.predictors, self._num_outputs = predictors, m

        def forward(self, X):
            shape = X.shape[:-1]
            flat = X.reshape(-1, X.shape[-1]).detach().cpu().numpy()
            p = np.stack([np.asarray(f(flat)).reshape(len(flat), self._num_outputs) for f in self.predictors])
            v = torch.as_tensor(p, dtype=X.dtype).reshape(len(p), *shape, self._num_outputs)
            return v.movedim(0, -3)
    return PredictorEnsemble


def _qnehvi_on_pool(model, X: np.ndarray, Y: np.ndarray, pool, q: int, seed: int, ensemble: bool):
    import torch
    from botorch.acquisition.multi_objective import qNoisyExpectedHypervolumeImprovement
    from botorch.optim import optimize_acqf_discrete
    ty = torch.tensor(Y, dtype=torch.double)
    span = (ty.max(0).values - ty.min(0).values).clamp_min(1e-6)
    kw = {}
    if ensemble:
        from botorch.sampling.index_sampler import IndexSampler
        kw = {"sampler": IndexSampler(torch.Size([128]), seed=seed), "prune_baseline": False, "cache_root": False}
    af = qNoisyExpectedHypervolumeImprovement(model, ref_point=ty.min(0).values - 0.1 * span,
                                              X_baseline=torch.tensor(X, dtype=torch.double), **kw)
    cand, _ = optimize_acqf_discrete(af, q=q, choices=pool, max_batch_size=256)
    return cand


def propose_dnn_qnehvi(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0, n_nets: int = 8,
                       n_pool: int = 2048) -> pd.DataFrame:
    """Ensemble de MLPs (entradas e saídas padronizadas; sementes diferentes) + qNEHVI sobre candidatos."""
    from sklearn.neural_network import MLPRegressor
    import designer
    cols = list(camp.X.columns)
    bounds = designer._bounds(camp, space)
    X, Y = camp.X.to_numpy(float), np.asarray(camp.Y, float)
    lo, hi = bounds[0].numpy(), bounds[1].numpy()
    mu, sd = Y.mean(0), Y.std(0) + 1e-9
    nets = []
    for k in range(n_nets):
        net = MLPRegressor(hidden_layer_sizes=(64, 64), alpha=1e-3, max_iter=3000, random_state=seed * 100 + k)
        idx = np.random.default_rng(seed * 100 + k).integers(0, len(X), len(X))      # bootstrap: diversidade
        net.fit((X[idx] - lo) / (hi - lo + 1e-12), (Y[idx] - mu) / sd)
        nets.append(lambda Z, net=net: net.predict((Z - lo) / (hi - lo + 1e-12)).reshape(len(Z), -1) * sd + mu)
    model = _ensemble_model_class()(nets, Y.shape[1])
    cand = _qnehvi_on_pool(model, X, Y, _pool(bounds, cols, fixed, n_pool, seed), q, seed, ensemble=True)
    return pd.DataFrame(cand.detach().numpy(), columns=cols)


def propose_egbo(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0, pop: int = 64,
                 gens: int = 25, n_sobol: int = 512) -> pd.DataFrame:
    """EGBO: NSGA-II na média a posteriori do GP (partindo dos pontos medidos) gera candidatos perto da frente; o
    qNEHVI escolhe o lote entre eles e um conjunto Sobol (exploração)."""
    import torch
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    import designer
    cols = list(camp.X.columns)
    model, tx, ty, bounds = designer.build_model(camp, space)
    n_obj = ty.shape[1]
    free = [j for j, c in enumerate(cols) if c not in (fixed or {})]
    lo, hi = bounds[0].numpy(), bounds[1].numpy()
    base = camp.X.to_numpy(float).mean(0)
    for c, v in (fixed or {}).items():
        if c in cols:
            base[cols.index(c)] = float(v)

    def full(Z):
        F = np.tile(base, (len(Z), 1))
        F[:, free] = Z
        return F

    class P(Problem):
        def __init__(self):
            super().__init__(n_var=len(free), n_obj=n_obj, xl=lo[free], xu=hi[free])

        def _evaluate(self, Z, out, *a, **k):
            with torch.no_grad():
                m = model.posterior(torch.tensor(full(Z), dtype=torch.double)).mean[..., :n_obj].numpy()
            out["F"] = -m
    X0 = camp.X.to_numpy(float)[:, free]
    init = np.vstack([X0, lo[free] + np.random.default_rng(seed).random((max(pop - len(X0), 0), len(free)))
                      * (hi[free] - lo[free])])[:pop]
    res = minimize(P(), NSGA2(pop_size=pop, sampling=init), ("n_gen", gens), seed=seed, verbose=False)
    evo = full(np.atleast_2d(res.pop.get("X")))
    pool = torch.cat([torch.tensor(evo, dtype=torch.double), _pool(bounds, cols, fixed, n_sobol, seed)])
    from botorch.optim import optimize_acqf_discrete
    af, _ = designer._acq(model, tx, ty, "qnehvi", camp)          # mesma aquisição (e restrições) do Designer
    cand, _ = optimize_acqf_discrete(af, q=q, choices=pool, max_batch_size=256)
    return pd.DataFrame(cand.detach().numpy(), columns=cols)


def propose_optuna_tpe(camp, space: dict, q: int, fixed: dict | None = None, seed: int = 0) -> pd.DataFrame:
    """TPE multiobjetivo (Optuna) com o histórico como trials concluídos; contexto fixo fora da busca."""
    import optuna
    from optuna.distributions import FloatDistribution
    import designer
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    cols = list(camp.X.columns)
    bounds = designer._bounds(camp, space).numpy()
    free = [c for c in cols if c not in (fixed or {})]
    dist = {c: FloatDistribution(float(bounds[0][cols.index(c)]), float(bounds[1][cols.index(c)])) for c in free}
    Y = np.asarray(camp.Y, float)
    study = optuna.create_study(directions=["maximize"] * Y.shape[1],
                                sampler=optuna.samplers.TPESampler(seed=seed, multivariate=True))
    for x, y in zip(camp.X.to_numpy(float), Y):
        params = {c: float(np.clip(x[cols.index(c)], dist[c].low, dist[c].high)) for c in free}
        study.add_trial(optuna.trial.create_trial(params=params, distributions=dist, values=list(map(float, y))))
    rows = []
    for _ in range(q):
        t = study.ask(dist)
        rows.append({**{c: t.params[c] for c in free}, **{c: float(v) for c, v in (fixed or {}).items() if c in cols}})
        study.tell(t, state=optuna.trial.TrialState.FAIL)             # pendente: não reamostrar o mesmo ponto
    return pd.DataFrame(rows)[cols]


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
