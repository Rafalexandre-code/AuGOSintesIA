#!/usr/bin/env python3
"""Simulação de campanha e de poder (§4.11, §4.15, §4.18) com o laboratório SIMULADO (code/benchmarking/sim_lab.py).

Para cada semente e cada braço (random, recipe, batch, go, go+impurities), com a MESMA inicialização (4 receitas ×
lotes L1–L3 = 12 sínteses, como na proposta), mesmo alvo e mesmo orçamento, roda rodadas adaptativas alternando o
lote-alvo e registra o desfecho primário da proposta: **melhor perda J acumulada por rodada, média balanceada entre
lotes**. Depois compara os braços (Friedman, Wilcoxon + Holm), estima a redução relativa com IC 95 % por bootstrap
pareado e o poder de detectar a diferença com n campanhas.

Uso:
    python code/benchmarking/campaign_sim.py --seeds 5 --rounds 12 --q 2           # ~10–20 min em CPU
    python code/benchmarking/campaign_sim.py --seeds 2 --rounds 3 --arms recipe go  # teste rápido
Saídas em outputs/campaign_sim/: curves.csv, final.csv, summary.json. Os números valem para o SIMULADOR — servem
para dimensionar e testar o protocolo, não como previsão do ganho real.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "aunp_designer")]
import designer  # noqa: E402
import sim_lab  # noqa: E402
import stats  # noqa: E402

ARMS = ("random", "recipe", "batch", "go", "go+impurities")
BATCHES = ("L1", "L2", "L3")


def _best_by_batch(lab: str) -> float:
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))[["synthesis_id", "go_batch_id"]]
    j = out[out["objective"] == "spectral_loss_J"].merge(syn, on="synthesis_id")
    return float(j.groupby("go_batch_id")["value"].min().reindex(list(BATCHES)).mean())


def run_campaign(arm: str, seed: int, rounds: int, q: int, root: str, acq: str) -> list[dict]:
    from scipy.stats import qmc
    space = designer.DEFAULT_SPACE
    lab = os.path.join(root, f"{arm.replace('+', '_')}_s{seed}", "lab")
    sim_lab.init_lab(lab, BATCHES, seed=seed)
    rng = np.random.default_rng(seed)
    lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
    recipes = pd.DataFrame(qmc.scale(qmc.LatinHypercube(len(space), seed=seed).random(4), lo, hi), columns=list(space))
    for b in BATCHES:
        syn = designer.proposals_to_syntheses(recipes, space, b, f"INIT-{b}", 0, seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
    curve = [{"arm": arm, "seed": seed, "round": 0, "n": 12, "best_loss": _best_by_batch(lab)}]
    for r in range(1, rounds + 1):
        target = BATCHES[(r - 1) % len(BATCHES)]
        lots = {"reductant": ("RED-A", "RED-B")[r % 2]}           # lotes de reagente variam entre rodadas
        if arm == "random":
            pts = qmc.scale(qmc.Sobol(len(space), seed=seed * 1000 + r).random(q), lo, hi)
            cands = pd.DataFrame(pts, columns=list(space))
        else:
            camp = designer.load_campaign(lab, space, arm, ("spectral_loss_J",))
            fixed = designer.fixed_context(lab, camp, target, lots)
            cands = designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed * 1000 + r)
        syn = designer.proposals_to_syntheses(cands, space, target, "SIM", r, lots=lots, seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
        curve.append({"arm": arm, "seed": seed, "round": r, "n": 12 + r * q, "best_loss": _best_by_batch(lab)})
    return curve


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=12, help="rodadas adaptativas (proposta: 24 sínteses = 12 × q=2)")
    ap.add_argument("--q", type=int, default=2)
    ap.add_argument("--arms", nargs="*", default=list(ARMS), choices=ARMS)
    ap.add_argument("--acq", choices=["qlognehvi", "qnehvi"], default="qlognehvi")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "campaign_sim"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    curves, t0 = [], time.time()
    for s in range(a.seeds):
        for arm in a.arms:
            curves += run_campaign(arm, s, a.rounds, a.q, a.out, a.acq)
            last = curves[-1]
            print(f"semente {s} {arm:14} melhor perda final {last['best_loss']:8.3f}  ({time.time() - t0:5.0f} s)")
    cv = pd.DataFrame(curves)
    cv.to_csv(os.path.join(a.out, "curves.csv"), index=False)
    final = cv[cv["round"] == a.rounds].rename(columns={"best_loss": "final_best_loss"})
    final.to_csv(os.path.join(a.out, "final.csv"), index=False)
    summary = {"arms": a.arms, "seeds": a.seeds, "rounds": a.rounds, "q": a.q, "acq": a.acq,
               "comparison": stats.compare_arms(final) if a.seeds >= 2 else None, "relative_reduction_vs_recipe": {},
               "power_vs_recipe": {}}
    if "recipe" in a.arms and a.seeds >= 2:
        wide = final.pivot_table(index="seed", columns="arm", values="final_best_loss")
        for arm in a.arms:
            if arm in ("recipe",):
                continue
            summary["relative_reduction_vs_recipe"][arm] = stats.paired_bootstrap_relative_reduction(
                wide["recipe"].to_numpy(), wide[arm].to_numpy())
            if a.seeds >= 8:   # com poucas campanhas-base a reamostragem é degenerada (poder ≈ 0 ou 1)
                summary["power_vs_recipe"][arm] = stats.power_by_resampling(
                    wide["recipe"].to_numpy(), wide[arm].to_numpy(), [5, 10, 20, 40], n_sim=500).to_dict("records")
    if a.seeds < 8:
        summary["power_vs_recipe"] = "não estimado: use --seeds >= 8 (a reamostragem de poucas campanhas é degenerada)"
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1, default=float)
    print(json.dumps(summary, indent=1, default=float)[:3000])
    print(f"-> {os.path.relpath(a.out, ROOT)}/ (curves.csv, final.csv, summary.json) — resultados do SIMULADOR")


if __name__ == "__main__":
    main()
