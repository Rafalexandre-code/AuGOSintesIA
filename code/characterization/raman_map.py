#!/usr/bin/env python3
"""Distribuição ESPACIAL de descritores Raman em mapas de GO (§4.2: "priorizadas larguras de banda e distribuição
espacial de medidas").

Recebe uma tabela (x, y, grandeza…) — por exemplo, o ajuste de cada espectro do mapa por `raman.py` — e devolve,
por grandeza: média, sd, CV, percentis 10/90 e o I de MORAN (autocorrelação espacial; pesos k-vizinhos) com p-valor
por permutação. I ≈ 0: variação aleatória ponto a ponto (ruído/heterogeneidade fina); I > 0 significativo: domínios
espaciais (heterogeneidade em escala maior que o passo do mapa) — o lote não é homogêneo e uma medida pontual não o
representa. A média do lote deve vir com o sd ESPACIAL, não com o erro do ajuste.

Uso:
    python code/characterization/raman.py mapa/*.csv --per-spectrum --out pontos.csv   # (ou outra tabela x, y, …)
    python code/characterization/raman_map.py pontos.csv --quantities ID_IG D_FWHM_cm-1 G_FWHM_cm-1 --sample GO-B01-S01
"""
from __future__ import annotations

import argparse
import csv

import numpy as np
import pandas as pd


def knn_weights(xy: np.ndarray, k: int = 4) -> np.ndarray:
    from scipy.spatial import cKDTree
    _, idx = cKDTree(xy).query(xy, k=k + 1)
    W = np.zeros((len(xy), len(xy)))
    for i, nb in enumerate(idx[:, 1:]):
        W[i, nb] = 1.0
    W = (W + W.T) / 2
    return W / W.sum()


def morans_i(v: np.ndarray, W: np.ndarray, n_perm: int = 999, seed: int = 0) -> tuple[float, float]:
    z = np.asarray(v, float) - np.mean(v)
    den = np.sum(z ** 2)
    if den == 0:
        return 0.0, 1.0
    n = len(z)
    I = n * (z @ W @ z) / den                           # I = (n/S0)·zᵀWz/Σz², com S0 = ΣW = 1
    rng = np.random.default_rng(seed)
    perm = np.array([n * ((zz := rng.permutation(z)) @ W @ zz) / den for _ in range(n_perm)])
    p = (1 + np.sum(perm >= I)) / (n_perm + 1)
    return float(I), float(p)


def spatial_summary(df: pd.DataFrame, quantities: list[str], k: int = 4) -> dict:
    xy = df[["x", "y"]].to_numpy(float)
    W = knn_weights(xy, k)
    out = {}
    for q in quantities:
        v = pd.to_numeric(df[q], errors="coerce").to_numpy(float)
        ok = np.isfinite(v)
        Wq = W[np.ix_(ok, ok)]
        Wq = Wq / Wq.sum()
        I, p = morans_i(v[ok], Wq)
        m, s = float(np.mean(v[ok])), float(np.std(v[ok], ddof=1))
        out[q] = {"mean": m, "sd_spatial": s, "cv": s / abs(m) if m else float("nan"),
                  "p10": float(np.percentile(v[ok], 10)), "p90": float(np.percentile(v[ok], 90)),
                  "morans_I": I, "morans_p": p, "n_points": int(ok.sum()),
                  "spatially_structured": bool(p < 0.05 and I > 0)}
    return out


def to_rows(s: dict, sample_id: str, files: str = "") -> list[dict]:
    rows, i = [], 0
    for q, v in s.items():
        for suffix, val, unc in (("", v["mean"], v["sd_spatial"]), ("_spatial_cv", v["cv"], None),
                                 ("_morans_I", v["morans_I"], None)):
            i += 1
            rows.append({"measurement_id": f"M-RMAP-{sample_id}-{i:02d}", "go_sample_id": sample_id, "technique": "Raman",
                         "quantity": q + suffix, "value": round(val, 5), "uncertainty": "" if unc is None else round(unc, 5),
                         "uncertainty_type": "" if unc is None else "sd", "n_replicates": v["n_points"],
                         "unit": "a.u.", "method_details": f"mapa: sd espacial; I de Moran (p = {v['morans_p']:.3f}) "
                                                           "(code/characterization/raman_map.py)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table")
    ap.add_argument("--quantities", nargs="+", default=["ID_IG"])
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--sample", default="GO-SAMPLE")
    ap.add_argument("--out")
    a = ap.parse_args()
    df = pd.read_csv(a.table)
    s = spatial_summary(df, a.quantities, a.k)
    for q, v in s.items():
        print(f"{q}: média {v['mean']:.4f} ± {v['sd_spatial']:.4f} (CV {100 * v['cv']:.1f} %); "
              f"I de Moran {v['morans_I']:.3f} (p = {v['morans_p']:.3f}) -> "
              f"{'domínios espaciais' if v['spatially_structured'] else 'sem estrutura espacial'}")
    if a.out:
        rows = to_rows(s, a.sample, a.table)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
