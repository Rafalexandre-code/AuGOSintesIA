#!/usr/bin/env python3
"""Calibração do simulador pelo piloto e pela inicialização (§4.11) — antes do `prereg.py freeze`.

Os números de poder em docs/SIMULACOES.md dependem de dois tamanhos que o simulador ASSUME: a variação entre
preparações da mesma receita e o efeito do lote de GO. O piloto (receita de referência repetida em L1–L3) e a
inicialização (as mesmas receitas LHS em cada lote) medem os dois. Método dos momentos simulados:

  momentos observados (em ln J, J derivado por code/campaign/ingest.py com as regras do pré-registro):
    s_rep   — dp agrupado entre preparações da MESMA receita no MESMO lote (piloto);
    s_batch — dp dos efeitos de lote no modelo aditivo ln J ~ receita + lote (piloto + inicialização);
    s_res   — dp residual desse modelo (interação receita × lote + ruído);
  para cada par (k_noise, k_batch) de uma grade, o MESMO desenho (mesmas receitas, lotes com o C/O medido em
  go_descriptors.csv, mesmos lotes de redutor) é simulado R vezes; escolhe-se o par cujos momentos médios
  (em log) ficam mais perto dos observados, ponderados pela variância simulada de cada momento. O conjunto
  plausível (distância ≤ mínimo + χ²₂(0,95)) dá a faixa de cada multiplicador.
  k_instrument vem direto das leituras em duplicata (SOP-UVVIS-01): dp de (A₁ − A₂)/√2.

Saída: JSON para `campaign_sim.py --calibration` (e simulator.apply_calibration). Sem piloto, nada a calibrar.

Uso:
    python code/benchmarking/calibrate.py datasets/lab --out config/simulator_calibration.json [--reps 60]
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
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "campaign"), os.path.join(ROOT, "code", "spectral")]
import simulator as sim  # noqa: E402

K_NOISE = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
K_BATCH = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
CHI2_2DF_95 = 5.991
STAGES = ("PILOT", "INIT")


def _design(lab: str) -> pd.DataFrame:
    """Sínteses do piloto e da inicialização com ln J (outcomes.csv) e um id de receita."""
    import prereg
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    syn = syn[syn["campaign_id"].astype(str).str.upper().str.startswith(STAGES)]
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["planned", "failed"])]
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    J = out[out["objective"] == "spectral_loss_J"].set_index("synthesis_id")["value"]
    d = syn.join(J.rename("J"), on="synthesis_id").dropna(subset=["J"])
    space = [c for c in sim.SPACE if c in d]
    d["recipe"] = d[space].astype(float).round(6).astype(str).agg("|".join, axis=1)
    d["y"] = np.log(d["J"].astype(float) + prereg.epsilon())
    return d.reset_index(drop=True)


def moments(d: pd.DataFrame, y: np.ndarray | None = None) -> np.ndarray:
    """(s_rep, s_batch, s_res) de ln J; y substitui d['y'] (réplica simulada)."""
    y = d["y"].to_numpy(float) if y is None else y
    cell = d["recipe"] + "@" + d["go_batch_id"].astype(str)
    df = pd.DataFrame({"y": y, "cell": cell})
    g = df.groupby("cell")["y"]
    n = g.size()
    ss = g.apply(lambda v: float(np.sum((v - v.mean()) ** 2)))
    dof = int((n - 1)[n > 1].sum())
    s_rep = float(np.sqrt(ss[n > 1].sum() / dof)) if dof else float("nan")
    R = pd.get_dummies(d["recipe"], drop_first=True, dtype=float)
    B = pd.get_dummies(d["go_batch_id"].astype(str), dtype=float)
    X = np.c_[R.to_numpy(), B.to_numpy()]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    df_res = max(len(y) - np.linalg.matrix_rank(X), 1)
    b = beta[R.shape[1]:]
    return np.array([s_rep, float(np.std(b - b.mean(), ddof=1)) if len(b) > 1 else float("nan"),
                     float(np.sqrt(res @ res / df_res))])


def instrument_noise(lab: str) -> float | None:
    """dp do ruído de absorbância pelas leituras repetidas da mesma síntese (pares consecutivos)."""
    import uvvis
    sp = pd.read_csv(os.path.join(lab, "spectra.csv"))
    sp = sp[(sp["technique"].astype(str) == "UV-Vis") & sp["synthesis_id"].notna()]
    grid = np.arange(420.0, 780.0, 4.0)
    diffs = []
    for _, g in sp.groupby("synthesis_id"):
        if len(g) < 2:
            continue
        A = [np.interp(grid, *uvvis.read_spectrum(os.path.join(lab, f))) for f in g["file"].iloc[:2]]
        diffs.append((A[0] - A[1]) / np.sqrt(2))
    return float(np.sqrt(np.mean(np.square(diffs)))) if diffs else None


def measured_batches(lab: str) -> dict:
    """C/O e ID/IG medidos (go_descriptors.csv) → nomes do simulador L1… pela ordem do pré-registro."""
    import prereg
    cfg = prereg.load()
    order = list(cfg["batches"]["development"]) + list(cfg["batches"].get("reserved", []))
    p = os.path.join(lab, "go_descriptors.csv")
    if not os.path.exists(p):
        return {}
    gd = pd.read_csv(p)
    w = gd.pivot_table(index="go_batch_id", columns="descriptor", values="mean")
    out = {}
    for i, b in enumerate(order):
        if b in w.index and "C_O_ratio" in w:
            simname = f"L{i + 1}"
            out[simname] = {"C_O_ratio": float(w.loc[b, "C_O_ratio"]), "lab_batch": b,
                            **({"ID_IG": float(w.loc[b, "ID_IG"])} if "ID_IG" in w and pd.notna(w.loc[b, "ID_IG"])
                               else {})}
    return out


def _j_function():
    import prereg
    import uvvis
    cfg = prereg.load()
    tw, te = prereg.target_spectrum(cfg)
    s, grid = prereg.s_m(cfg), prereg.grid(cfg)
    norm = cfg["target_spectrum"].get("normalization", "none")
    eps = prereg.epsilon(cfg)
    def jfun(specs) -> float:
        """ln(média de J das leituras + ε) — como code/campaign/ingest.py agrega as leituras repetidas."""
        J = [uvvis.spectral_loss_J(sim.WL, x, tw, te, s=s, grid=grid, norm=None if norm == "none" else norm)
             for x in specs]
        return float(np.log(np.mean(J) + eps))
    return jfun


def readings_per_synthesis(lab: str) -> int:
    sp = pd.read_csv(os.path.join(lab, "spectra.csv"))
    sp = sp[(sp["technique"].astype(str) == "UV-Vis") & sp["synthesis_id"].notna()]
    return int(max(1, round(sp.groupby("synthesis_id").size().median()))) if len(sp) else 1


def simulate_moments(d: pd.DataFrame, k_noise: float, k_batch: float, reps: int, seed: int, batch_map: dict,
                     jfun, n_read: int = 1) -> np.ndarray:
    sim.CAL.update({"noise": k_noise, "batch": k_batch})
    rng = np.random.default_rng(seed)
    space = [c for c in sim.SPACE if c in d]
    conds = [{k: float(r[k]) for k in space} for _, r in d.iterrows()]
    batches = [batch_map.get(str(b), str(b)) for b in d["go_batch_id"]]
    lots = [r if r in sim.REAGENT_LOTS else "RED-A" for r in d.get("reductant_lot_id", pd.Series("RED-A",
                                                                                          index=d.index)).astype(str)]
    M = np.empty((reps, 3))
    for i in range(reps):
        y = []
        for c, b, lot in zip(conds, batches, lots):
            r = sim.simulate(c, b, lot, rng=rng)
            extra = [r["spectrum_noiseless"] + rng.normal(0, sim.NOISE_SD * sim.CAL["instrument"], sim.WL.size)
                     for _ in range(n_read - 1)]
            y.append(jfun([r["spectrum"], *extra]))
        y = np.array(y)
        M[i] = moments(d, y)
    return M


def calibrate(lab: str, reps: int = 60, seed: int = 0, k_noise=K_NOISE, k_batch=K_BATCH) -> dict:
    d = _design(lab)
    if d["go_batch_id"].nunique() < 2 or len(d) < 6:
        raise SystemExit("piloto/inicialização insuficientes: preciso de ≥ 6 sínteses com J em ≥ 2 lotes")
    obs = moments(d)
    batches = measured_batches(lab)
    lab_to_sim = {v["lab_batch"]: k for k, v in batches.items()}
    saved = dict(sim.CAL), {k: dict(v) for k, v in sim.BATCHES.items()}
    try:
        sim.apply_calibration({"batches": {k: {q: v[q] for q in ("C_O_ratio", "ID_IG") if q in v}
                                           for k, v in batches.items()},
                               "co_ref": float(np.mean([v["C_O_ratio"] for v in batches.values()])) if batches
                               else sim.CAL["co_ref"]})
        co_ref = sim.CAL["co_ref"]
        noise = instrument_noise(lab)
        k_inst = noise / sim.NOISE_SD if noise else 1.0
        sim.CAL["instrument"] = k_inst
        jfun = _j_function()
        n_read = readings_per_synthesis(lab)
        grid = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for kn in k_noise:
                for kb in k_batch:
                    M = np.log(np.clip(simulate_moments(d, kn, kb, reps, seed, lab_to_sim, jfun, n_read), 1e-9, None))
                    ok = np.isfinite(obs)
                    mu, var = M.mean(0), M.var(0, ddof=1) + 1e-9
                    dist = float(np.sum(((np.log(obs) - mu) ** 2 / var)[ok]))
                    grid.append({"k_noise": kn, "k_batch": kb, "distance": dist,
                                 **{f"sim_{n}": float(np.exp(m)) for n, m in zip(("s_rep", "s_batch", "s_res"), mu)}})
    finally:
        sim.CAL.clear()
        sim.CAL.update(saved[0])
        sim.BATCHES.clear()
        sim.BATCHES.update(saved[1])
    g = pd.DataFrame(grid)
    best = g.loc[g["distance"].idxmin()]
    plaus = g[g["distance"] <= best["distance"] + CHI2_2DF_95]
    return {"SIMULADOR_CALIBRADO_COM": os.path.abspath(lab), "n_syntheses": int(len(d)),
            "observed": dict(zip(("s_rep", "s_batch", "s_res"), map(float, obs))),
            "noise": float(best["k_noise"]), "batch": float(best["k_batch"]), "instrument": float(k_inst),
            "co_ref": float(co_ref),
            "plausible_range": {"noise": [float(plaus["k_noise"].min()), float(plaus["k_noise"].max())],
                                "batch": [float(plaus["k_batch"].min()), float(plaus["k_batch"].max())]},
            "simulated_at_best": {k: float(best[f"sim_{k}"]) for k in ("s_rep", "s_batch", "s_res")},
            "batches": {k: {q: v[q] for q in ("C_O_ratio", "ID_IG") if q in v} for k, v in batches.items()},
            "batch_map": lab_to_sim, "reps": reps, "grid": grid}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--out", default=os.path.join(ROOT, "config", "simulator_calibration.json"))
    ap.add_argument("--reps", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    c = calibrate(a.lab, a.reps, a.seed)
    o, s = c["observed"], c["simulated_at_best"]
    print(f"{c['n_syntheses']} sínteses do piloto/inicialização")
    for k in ("s_rep", "s_batch", "s_res"):
        print(f"  {k:8s} observado {o[k]:.3f} | simulado no melhor ajuste {s[k]:.3f}")
    pr = c["plausible_range"]
    print(f"multiplicadores: ruído entre preparações {c['noise']} (faixa {pr['noise']}), efeito de lote {c['batch']} "
          f"(faixa {pr['batch']}), instrumento {c['instrument']:.2f}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(c, fh, indent=1, ensure_ascii=False)
    print(f"-> {a.out}  (use: campaign_sim.py --scenario prospective --calibration {a.out})")


if __name__ == "__main__":
    main()
