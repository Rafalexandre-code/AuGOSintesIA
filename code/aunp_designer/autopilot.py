#!/usr/bin/env python3
"""Autopilot: seleção dinâmica do modelo a cada rodada (§4.5; inspirado no SPACESHIP, Kim et al. 2026).

A cada rodada, cada modelo candidato é avaliado PREQUENCIALMENTE (origem rolante): para cada uma das últimas k
sínteses, ajusta-se o modelo só com o que veio antes e prevê-se essa síntese — exatamente a situação de uma decisão
real. O escore é o erro quadrático médio padronizado no objetivo primário (escala do modelo) + a penalidade de
calibração |z̄²−1| (um modelo que erra pouco mas com incerteza mal estimada decide mal na aquisição). O modelo de
menor escore propõe a rodada com o qNEHVI do Designer. Com poucos dados (n < k + 6) usa o padrão (go).

Candidatos padrão: as representações do GP (recipe, go, go+impurities, hierarchical). A escolha e os escores ficam
em `attrs` da proposta (rastreabilidade: run_metadata).

Uso:
    python code/aunp_designer/autopilot.py datasets/lab --batch L2 [--q 2 --k 4 --lot reductant=RED-A]
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import designer  # noqa: E402

CANDIDATES = ("recipe", "go", "go+impurities", "hierarchical")


def prequential_scores(lab: str, space: dict, candidates=CANDIDATES, k: int = 4, arm: str | None = None) -> dict:
    import torch
    scores = {}
    for rep in candidates:
        try:
            camp = designer.load_campaign(lab, space, rep, designer.default_logs(), designer.default_eps(), arm=arm)
        except (ValueError, KeyError) as err:
            scores[rep] = {"score": float("inf"), "erro": str(err)[:100]}
            continue
        n = len(camp.X)
        if n < k + 6:
            scores[rep] = {"score": float("inf"), "erro": f"só {n} sínteses"}
            continue
        y = camp.Y[:, 0]
        sd_y = float(np.std(y)) or 1.0
        z = []
        for i in range(n - k, n):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model, *_ = designer.build_model(camp.__class__(**{**camp.__dict__, "C": None, "cons": {}}), space,
                                                 rows=np.arange(i))
            x = torch.tensor(camp.X.to_numpy(float)[i:i + 1], dtype=torch.double)
            with torch.no_grad():
                post = model.models[0].posterior(x)
            mu, sd = float(post.mean), float(post.variance.clamp_min(1e-12).sqrt())
            z.append(((y[i] - mu) / sd_y, (y[i] - mu) / sd))
        e = np.array([a for a, _ in z])
        zz = np.array([b for _, b in z])
        scores[rep] = {"score": float(np.mean(e ** 2) + abs(np.mean(zz ** 2) - 1) * 0.1),
                       "smse": float(np.mean(e ** 2)), "z2_mean": float(np.mean(zz ** 2))}
    return scores


def propose(lab: str, space: dict, batch: str | None, lots: dict | None, q: int = 2, seed: int = 0,
            acq: str | None = None, k: int = 4, candidates=CANDIDATES, arm: str | None = None,
            default: str = "go") -> pd.DataFrame:
    sc = prequential_scores(lab, space, candidates, k, arm)
    best = min(sc, key=lambda r: sc[r]["score"])
    if not np.isfinite(sc[best]["score"]):
        best = default
    camp = designer.load_campaign(lab, space, best, designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints(), arm=arm)
    fixed = designer.fixed_context(lab, camp, batch, lots)
    cands = designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed, lab=lab)
    cands.attrs.update({"autopilot_choice": best, "autopilot_scores": sc})
    return cands


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--q", type=int, default=2)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--lot", action="append", default=[])
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    lots = dict(x.split("=", 1) for x in a.lot)
    c = propose(a.lab, designer.DEFAULT_SPACE, a.batch, lots, a.q, a.seed, k=a.k)
    for rep, v in c.attrs["autopilot_scores"].items():
        print(f"{rep:15s} {v}")
    print(f"escolhido: {c.attrs['autopilot_choice']}")
    print(c.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
