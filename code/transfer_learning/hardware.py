#!/usr/bin/env python3
"""Correção linear entre plataformas de síntese (hot plate, banho-maria, reator de fluxo) — §4.7, nível 3.

A proposta pede "um modelo de correção linear para estimar deslocamentos específicos da plataforma" e separar
mudança de plataforma de mudança química. Modelo em dois estágios:

  1. GP (Matérn-5/2 + ARD, o mesmo do Designer) ajustado só na plataforma de REFERÊNCIA (a mais usada);
  2. para cada outra plataforma h, os resíduos r = y − μ_ref(x) são regredidos linearmente na receita padronizada:
        δ_h(x) = a_h + b_hᵀ·z(x)      (ridge, λ por validação cruzada; IC de a_h por bootstrap)
     a_h é o deslocamento médio da plataforma; b_h, quanto ele depende da receita (ex.: temperatura efetiva).

Previsão em h: μ_ref(x) + δ_h(x). A utilidade é medida por validação cruzada leave-one-out nas sínteses de h:
RMSE sem correção × com correção. Com poucas sínteses em h, b_h é encolhido para 0 e sobra só o deslocamento a_h.

Uso:
    python code/transfer_learning/hardware.py datasets/lab [--objective spectral_loss_J] [--reference hot_plate]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "aunp_designer")]


def _gp(X: np.ndarray, y: np.ndarray, bounds: np.ndarray):
    import torch
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Normalize, Standardize
    from gpytorch.kernels import ScaleKernel
    import designer
    import hierarchical
    m = SingleTaskGP(torch.tensor(X), torch.tensor(y).unsqueeze(-1),
                     covar_module=ScaleKernel(hierarchical.matern52(X.shape[1])),
                     input_transform=Normalize(X.shape[1], bounds=torch.tensor(bounds)),
                     outcome_transform=Standardize(1))
    designer._fit(m)
    return lambda Z: m.posterior(torch.tensor(Z)).mean.detach().numpy().ravel()


def ridge_cv(Z: np.ndarray, r: np.ndarray, lambdas=(0.1, 1.0, 10.0, 100.0, 1e4)) -> tuple[np.ndarray, float]:
    """Ridge com intercepto não penalizado; λ por LOO (fórmula fechada da matriz chapéu)."""
    A = np.c_[np.ones(len(Z)), Z]
    best, best_lam = None, None
    for lam in lambdas:
        P = np.diag([0.0] + [lam] * Z.shape[1])
        H = A @ np.linalg.solve(A.T @ A + P, A.T)
        loo = np.mean(((r - H @ r) / np.clip(1 - np.diag(H), 1e-9, None)) ** 2)
        if best is None or loo < best:
            best, best_lam = loo, lam
    P = np.diag([0.0] + [best_lam] * Z.shape[1])
    return np.linalg.solve(A.T @ A + P, A.T @ r), best_lam


def fit(df: pd.DataFrame, space: dict, y_col: str, reference: str | None = None, n_boot: int = 200,
        seed: int = 0) -> dict:
    """df: uma linha por síntese com as variáveis do espaço, `hardware` e o desfecho `y_col` (escala do modelo)."""
    cols = list(space)
    bounds = np.array([[space[c][0] for c in cols], [space[c][1] for c in cols]], float)
    df = df.dropna(subset=cols + [y_col]).copy()
    df["hardware"] = df["hardware"].fillna("").replace("", "unspecified")
    counts = df["hardware"].value_counts()
    reference = reference or counts.index[0]
    ref = df[df["hardware"] == reference]
    if len(ref) < 5:
        raise ValueError(f"plataforma de referência {reference!r} com só {len(ref)} sínteses")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mu = _gp(ref[cols].to_numpy(float), ref[y_col].to_numpy(float), bounds)
    rng = np.random.default_rng(seed)
    out = {"reference": reference, "n_reference": int(len(ref)), "platforms": {}}
    for h, g in df[df["hardware"] != reference].groupby("hardware"):
        X = g[cols].to_numpy(float)
        Z = (X - bounds[0]) / (bounds[1] - bounds[0]) - 0.5
        r = g[y_col].to_numpy(float) - mu(X)
        coef, lam = ridge_cv(Z, r)
        boots = []
        for _ in range(n_boot):
            i = rng.integers(0, len(r), len(r))
            boots.append(ridge_cv(Z[i], r[i])[0][0])
        loo_raw, loo_cor = [], []
        for i in range(len(r)):                       # LOO honesto: a correção é reajustada sem o ponto i
            m = np.arange(len(r)) != i
            c_i = ridge_cv(Z[m], r[m])[0] if m.sum() >= 2 else np.r_[r[m].mean(), np.zeros(Z.shape[1])]
            loo_raw.append(r[i])
            loo_cor.append(r[i] - (c_i[0] + Z[i] @ c_i[1:]))
        out["platforms"][h] = {
            "n": int(len(r)), "offset": float(coef[0]),
            "offset_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "slopes": dict(zip(cols, map(float, coef[1:]))), "ridge_lambda": float(lam),
            "rmse_loo_uncorrected": float(np.sqrt(np.mean(np.square(loo_raw)))),
            "rmse_loo_corrected": float(np.sqrt(np.mean(np.square(loo_cor))))}
        v = out["platforms"][h]
        v["correction_improves"] = bool(v["rmse_loo_corrected"] < v["rmse_loo_uncorrected"])
        v["offset_significant"] = bool(v["offset_ci95"][0] > 0 or v["offset_ci95"][1] < 0)
    return out


def from_lab(lab: str, objective: str = "spectral_loss_J", reference: str | None = None) -> dict:
    import designer
    space = designer.DEFAULT_SPACE
    syn = designer.usable_syntheses(lab)
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    y = out[out["objective"] == objective].set_index("synthesis_id")["value"].astype(float)
    df = syn.set_index("synthesis_id").join(y.rename("y"), how="inner")
    if objective in designer.default_logs():
        df["y"] = np.log(df["y"] + designer.default_eps())
    if "hardware" not in df or df["hardware"].fillna("").nunique() < 2:
        raise SystemExit("só uma plataforma em aunp_syntheses.hardware: não há o que corrigir")
    res = fit(df.reset_index(), space, "y", reference)
    res["objective"] = objective
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--objective", default="spectral_loss_J")
    ap.add_argument("--reference")
    a = ap.parse_args()
    print(json.dumps(from_lab(a.lab, a.objective, a.reference), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
