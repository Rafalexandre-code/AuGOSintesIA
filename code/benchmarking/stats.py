#!/usr/bin/env python3
"""Estatística de benchmark e de decisão (§4.15, §4.18).

* indicadores multiobjetivo: hipervolume, IGD e spread (pymoo), com a convenção de MINIMIZAÇÃO do pymoo;
* comparação de algoritmos/braços em várias sementes: Friedman (≥ 3 grupos) e Wilcoxon pareado com correção de Holm;
* diferença relativa com IC 95 % por bootstrap pareado entre campanhas;
* poder estatístico por reamostragem: probabilidade de detectar uma redução relativa (ex.: 20 %) com n campanhas;
* experimentos até o critério (tempo até evento, censurado no orçamento): média restrita (RMST, Kaplan–Meier) e
  teste log-rank entre braços — campanhas que não atingem o critério entram como censuradas, não como "orçamento".
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "transfer_learning"))


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


def paired_bootstrap_geometric_reduction(base: np.ndarray, new: np.ndarray, n_boot: int = 5000, seed: int = 0) -> dict:
    """Redução GEOMÉTRICA 1 − exp(média de ln(new/base)) com IC 95 % por bootstrap pareado. Robusta quando a perda varia
    em ordens de grandeza entre campanhas: a média aritmética de 1 − new/base é dominada pelas campanhas cuja base é
    pequena (uma só pode levar a média a −1000 %), a do log-razão não."""
    base, new = np.asarray(base, float), np.asarray(new, float)
    rng = np.random.default_rng(seed)
    lr = np.log(new / base)
    boots = np.array([np.mean(lr[rng.integers(0, len(lr), len(lr))]) for _ in range(n_boot)])
    return {"geometric_reduction": float(1 - np.exp(np.mean(lr))),
            "ci95": (float(1 - np.exp(np.percentile(boots, 97.5))), float(1 - np.exp(np.percentile(boots, 2.5)))),
            "fraction_better": float(np.mean(lr < 0))}


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


def logrank(t1: np.ndarray, t2: np.ndarray, budget: float) -> float:
    """Log-rank de duas amostras (inf = censurado no orçamento); p bilateral (χ², 1 gl)."""
    from scipy.stats import chi2
    t1, t2 = np.asarray(t1, float), np.asarray(t2, float)
    e1, e2 = np.isfinite(t1), np.isfinite(t2)
    t1, t2 = np.where(e1, t1, budget), np.where(e2, t2, budget)
    times = np.unique(np.r_[t1[e1], t2[e2]])
    o_e, var = 0.0, 0.0
    for t in times:
        n1, n2 = np.sum(t1 >= t), np.sum(t2 >= t)
        d1, d2 = np.sum((t1 == t) & e1), np.sum((t2 == t) & e2)
        n, d = n1 + n2, d1 + d2
        if n < 2 or d == 0:
            continue
        o_e += d1 - d * n1 / n
        var += d * (n1 / n) * (n2 / n) * (n - d) / (n - 1)
    return float(chi2.sf(o_e ** 2 / var, 1)) if var > 0 else 1.0


def time_to_criterion(curves: pd.DataFrame, threshold: float, reference: str | None = None, arm: str = "arm",
                      seed: str = "seed", n: str = "n", value: str = "value", lower_is_better: bool = True) -> dict:
    """curves: (braço, semente, n experimentos, melhor valor acumulado). Experimentos até value ≤ limiar por
    campanha (inf = não atingiu), RMST com censura no orçamento e log-rank contra `reference`."""
    import hierarchical
    budget = float(curves[n].max())
    times = {}
    for a, g in curves.groupby(arm):
        tt = []
        for _, c in g.sort_values(n).groupby(seed):
            ok = c[value] <= threshold if lower_is_better else c[value] >= threshold
            tt.append(float(c.loc[ok, n].iloc[0]) if ok.any() else float("inf"))
        times[a] = np.array(tt)
    out = {"threshold": float(threshold), "budget": budget, "arms": {}}
    for a, tt in times.items():
        r = hierarchical.censored_mean(tt, budget)
        r["times"] = [None if not np.isfinite(t) else t for t in tt]
        if reference in times and a != reference:
            r["logrank_p"] = logrank(tt, times[reference], budget)
        out["arms"][a] = r
    return out
