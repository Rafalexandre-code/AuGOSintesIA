#!/usr/bin/env python3
"""Estatística de benchmark e de decisão (§4.15, §4.18).

* indicadores multiobjetivo: hipervolume, IGD e spread (pymoo), com a convenção de MINIMIZAÇÃO do pymoo;
* comparação de algoritmos/braços em várias sementes: Friedman (≥ 3 grupos) e Wilcoxon pareado com correção de Holm;
* diferença relativa com IC 95 % por bootstrap pareado entre campanhas;
* poder estatístico por reamostragem: probabilidade de detectar uma redução relativa (ex.: 20 %) com n campanhas.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def hv_igd_spread(F: np.ndarray, ref_point: np.ndarray, pareto_front: np.ndarray | None = None) -> dict:
    """F: pontos (n × m) a MINIMIZAR. IGD e spread exigem uma frente de referência (ex.: a união de todas as execuções)."""
    from pymoo.indicators.hv import HV
    out = {"hypervolume": float(HV(ref_point=np.asarray(ref_point))(np.asarray(F)))}
    if pareto_front is not None and len(pareto_front) > 1:
        from pymoo.indicators.igd import IGD
        out["igd"] = float(IGD(np.asarray(pareto_front))(np.asarray(F)))
    nd = np.asarray(F)[np.argsort(np.asarray(F)[:, 0])]
    gaps = np.linalg.norm(np.diff(nd, axis=0), axis=1) if len(nd) > 1 else np.array([0.0])
    out["spread"] = float(np.std(gaps) / (np.mean(gaps) + 1e-12))  # uniformidade: sd/média dos espaçamentos
    return out


def holm(pvals: dict) -> dict:
    """Correção de Holm–Bonferroni: {rótulo: p} -> {rótulo: p ajustado}."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, adj, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        adj[k] = run
    return adj


def compare_arms(results: pd.DataFrame, metric: str = "final_best_loss", arm: str = "arm", seed: str = "seed",
                 lower_is_better: bool = True) -> dict:
    """results: uma linha por (braço, semente). Friedman entre braços + Wilcoxon pareado de cada par (Holm)."""
    from scipy.stats import friedmanchisquare, wilcoxon
    wide = results.pivot_table(index=seed, columns=arm, values=metric).dropna()
    out = {"n_seeds": len(wide), "median": wide.median().to_dict()}
    if wide.shape[1] >= 3 and len(wide) >= 3:
        out["friedman_p"] = float(friedmanchisquare(*[wide[c] for c in wide.columns]).pvalue)
    raw = {}
    for a, b in itertools.combinations(wide.columns, 2):
        d = wide[a] - wide[b]
        raw[f"{a} vs {b}"] = float(wilcoxon(d).pvalue) if len(d) >= 5 and np.any(d != 0) else np.nan
    out["wilcoxon_p"] = raw
    out["wilcoxon_p_holm"] = holm({k: v for k, v in raw.items() if np.isfinite(v)})
    return out


def paired_bootstrap_relative_reduction(base: np.ndarray, new: np.ndarray, n_boot: int = 5000, seed: int = 0) -> dict:
    """Redução relativa média (1 − new/base) com IC 95 % por bootstrap pareado (campanhas como unidade)."""
    base, new = np.asarray(base, float), np.asarray(new, float)
    rng = np.random.default_rng(seed)
    rel = 1 - new / base
    boots = np.array([np.mean(rel[rng.integers(0, len(rel), len(rel))]) for _ in range(n_boot)])
    return {"mean_reduction": float(np.mean(rel)), "ci95": (float(np.percentile(boots, 2.5)),
                                                             float(np.percentile(boots, 97.5)))}


def power_by_resampling(base: np.ndarray, new: np.ndarray, n_campaigns: list[int], alpha: float = 0.05,
                        n_sim: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Poder empírico: reamostra n campanhas pareadas e aplica Wilcoxon unilateral (new < base)."""
    from scipy.stats import wilcoxon
    base, new = np.asarray(base, float), np.asarray(new, float)
    rng = np.random.default_rng(seed)
    rows = []
    for n in n_campaigns:
        hits = 0
        for _ in range(n_sim):
            i = rng.integers(0, len(base), n)
            d = new[i] - base[i]
            if np.all(d == 0):
                continue
            if wilcoxon(d, alternative="less").pvalue < alpha:
                hits += 1
        rows.append({"n_campaigns": n, "power": hits / n_sim})
    return pd.DataFrame(rows)
