#!/usr/bin/env python3
"""Análise pré-registrada da comparação prospectiva entre braços (§4.18; config/preregistration.yaml → arms,
primary_outcome).

Desenho: em cada rodada adaptativa r, cada braço prospectivo propõe UMA síntese, no mesmo lote de GO e no mesmo dia
(ordem sorteada dentro do dia); cada braço treina só com os dados compartilhados e as suas rodadas
(`designer.py propose --arm`). A unidade de análise é o par da rodada:

    d_r = log(J_trat + ε) − log(J_ref + ε)        (negativo = o braço de tratamento acertou mais perto do alvo)

* Teste: randomização por troca de sinais, unilateral (H1: d < 0), EXATO para até 20 pares (2^n atribuições) e por
  Monte Carlo acima disso. É inferência baseada no desenho: sob H0 os rótulos dos dois braços dentro do par são
  permutáveis; não exige normalidade nem independência entre rodadas além do pareamento.
* Estimativa: Hodges–Lehmann (mediana das médias de Walsh) com IC exato pela distribuição do posto sinalizado;
  em escala de razão: redução relativa = 1 − exp(HL), comparada ao limiar de relevância pré-registrado (20 %).
* Descritivo (desfecho da proposta): melhor perda acumulada por rodada e por braço, média balanceada entre lotes,
  contando os dados compartilhados e as rodadas do próprio braço.

Uso:
    python code/campaign/analysis.py datasets/lab [--arms recipe go+impurities] [--out outputs/analise.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "aunp_designer")]
ARM_SEP = ":"


def _arm_round(design_id) -> tuple[str, int | None]:
    d = "" if pd.isna(design_id) else str(design_id)
    if ARM_SEP not in d:
        return "", None
    arm, rest = d.split(ARM_SEP, 1)
    try:
        return arm, int(rest.split("-")[0].lstrip("it"))
    except ValueError:
        return arm, None


def load_long(lab: str, objective: str = "spectral_loss_J") -> pd.DataFrame:
    """Uma linha por síntese concluída com braço, rodada, lote e valor do objetivo."""
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["failed", "planned"])]
    if "is_control" in syn:
        syn = syn[~syn["is_control"].astype(str).isin(["GO_blank", "no_GO"])]
    if "campaign_id" in syn:
        syn = syn[syn["campaign_id"].astype(str) != "CONFIRMATION"]
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    out = out[out["objective"] == objective][["synthesis_id", "value"]]
    df = syn.merge(out, on="synthesis_id")
    ar = df["design_id"].map(_arm_round) if "design_id" in df else pd.Series([("", None)] * len(df))
    df["arm"] = [a for a, _ in ar]
    df["round"] = [r for _, r in ar]
    return df


def paired_differences(df: pd.DataFrame, ref: str, trt: str, eps: float) -> pd.DataFrame:
    """d_r por rodada (média de log J se um braço tiver mais de uma síntese na rodada); só rodadas completas."""
    a = df[df["arm"].isin([ref, trt]) & df["round"].notna()].copy()
    a["logJ"] = np.log(a["value"].astype(float) + eps)
    w = a.pivot_table(index="round", columns="arm", values="logJ", aggfunc="mean")
    b = a.groupby("round")["go_batch_id"].first()
    w = w.dropna(subset=[c for c in (ref, trt) if c in w])
    if ref not in w or trt not in w:
        return pd.DataFrame(columns=["round", "go_batch_id", "d"])
    return pd.DataFrame({"round": w.index.astype(int), "go_batch_id": b.reindex(w.index).values,
                         "d": (w[trt] - w[ref]).values}).reset_index(drop=True)


def sign_flip_test(d: np.ndarray, alternative: str = "less", n_mc: int = 200_000, seed: int = 0) -> float:
    """p-valor do teste de randomização por troca de sinais com a soma como estatística (exato até 20 pares)."""
    d = np.asarray(d, float)
    n = len(d)
    if n == 0:
        return float("nan")
    obs = d.sum()
    if n <= 20:
        signs = np.array(list(itertools.product((1.0, -1.0), repeat=n)))
        stats = signs @ np.abs(d)
    else:
        rng = np.random.default_rng(seed)
        stats = rng.choice((1.0, -1.0), size=(n_mc, n)) @ np.abs(d)
    if alternative == "less":
        return float(np.mean(stats <= obs + 1e-12))
    if alternative == "greater":
        return float(np.mean(stats >= obs - 1e-12))
    return float(np.mean(np.abs(stats) >= abs(obs) - 1e-12))


def _signed_rank_null(n: int) -> np.ndarray:
    """Distribuição exata de W+ (soma dos postos positivos) sob H0, por programação dinâmica."""
    f = np.zeros(n * (n + 1) // 2 + 1)
    f[0] = 1.0
    for k in range(1, n + 1):
        g = f.copy()
        g[k:] += f[:-k] if k <= len(f) - 1 else 0
        f = g
    return f / f.sum()


def hodges_lehmann(d: np.ndarray, level: float = 0.95) -> dict:
    """Estimador de Hodges–Lehmann (mediana das médias de Walsh) e IC exato pela distribuição de W+."""
    d = np.asarray(d, float)
    n = len(d)
    if n == 0:
        return {"estimate": float("nan"), "ci": (float("nan"), float("nan")), "achieved_level": float("nan")}
    walsh = np.sort([(d[i] + d[j]) / 2 for i in range(n) for j in range(i, n)])
    est = float(np.median(walsh))
    if n < 3:
        return {"estimate": est, "ci": (float(walsh[0]), float(walsh[-1])), "achieved_level": float("nan")}
    cdf = np.cumsum(_signed_rank_null(n))
    alpha = (1 - level) / 2
    k = int(np.searchsorted(cdf, alpha, side="right"))         # P(W+ ≤ k−1) ≤ α/2
    k = max(k, 1)
    lo, hi = walsh[k - 1], walsh[len(walsh) - k]
    achieved = 1 - 2 * (cdf[k - 1] if k - 1 < len(cdf) else 0.0)
    return {"estimate": est, "ci": (float(lo), float(hi)), "achieved_level": float(achieved)}


def cumulative_curves(df: pd.DataFrame, arms: list[str], batches: list[str]) -> pd.DataFrame:
    """Melhor perda acumulada por rodada e braço (dados compartilhados + rodadas do braço), média entre lotes."""
    shared = df[df["arm"] == ""]
    rounds = sorted(int(r) for r in df["round"].dropna().unique())
    rows = []
    for arm in arms:
        own = df[df["arm"] == arm]
        for r in [0] + rounds:
            pool = pd.concat([shared, own[own["round"].notna() & (own["round"] <= r)]])
            best = pool.groupby("go_batch_id")["value"].min().reindex(batches)
            rows.append({"arm": arm, "round": r, "best_loss_balanced": float(best.mean()),
                         "n_batches_with_data": int(best.notna().sum())})
    return pd.DataFrame(rows)


def analyze(lab: str, arms: tuple[str, str] | None = None, eps: float | None = None, batches=None,
            level: float = 0.95) -> dict:
    import prereg
    cfg = prereg.load()
    a = prereg.arms(cfg)
    ref, trt = arms or (a["reference"], next(x for x in a["prospective"] if x != a["reference"]))
    eps = prereg.epsilon(cfg) if eps is None else eps
    batches = batches or list(cfg["batches"]["development"])
    df = load_long(lab)
    pairs = paired_differences(df, ref, trt, eps)
    d = pairs["d"].to_numpy(float)
    hl = hodges_lehmann(d, level)
    curves = cumulative_curves(df, [ref, trt], batches)
    last = curves["round"].max()
    end = curves[curves["round"] == last].set_index("arm")["best_loss_balanced"]
    thr = float(cfg["relevance_threshold"])
    red = {k: (1 - float(np.exp(v)) if np.isfinite(v) else float("nan"))
           for k, v in (("estimate", hl["estimate"]), ("ci_high", hl["ci"][0]), ("ci_low", hl["ci"][1]))}
    return {"reference_arm": ref, "treatment_arm": trt, "n_pairs": int(len(d)), "epsilon": eps,
            "pairs": pairs.to_dict("records"),
            "p_value_sign_flip_one_sided": sign_flip_test(d, "less"),
            "hodges_lehmann_log_ratio": hl,
            "relative_reduction": {"estimate": red["estimate"], "ci95": (red["ci_low"], red["ci_high"]),
                                   "relevance_threshold": thr,
                                   "ci_excludes_zero": bool(np.isfinite(hl["ci"][1]) and hl["ci"][1] < 0),
                                   "estimate_above_threshold": bool(red["estimate"] >= thr)},
            "cumulative_best": curves.to_dict("records"),
            "final_best_balanced": end.to_dict(),
            "final_geometric_reduction": float(1 - end.get(trt, np.nan) / end.get(ref, np.nan))
            if ref in end and trt in end else float("nan"),
            "prereg_sha256": prereg.sha256(cfg), "prereg_state": prereg.check()["state"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--arms", nargs=2, metavar=("REFERENCIA", "TRATAMENTO"))
    ap.add_argument("--out")
    a = ap.parse_args()
    r = analyze(a.lab, tuple(a.arms) if a.arms else None)
    hl, rr = r["hodges_lehmann_log_ratio"], r["relative_reduction"]
    print(f"{r['treatment_arm']} × {r['reference_arm']}: {r['n_pairs']} rodadas pareadas; "
          f"p (randomização, unilateral) = {r['p_value_sign_flip_one_sided']:.4f}")
    print(f"redução relativa de J (Hodges–Lehmann) = {100 * rr['estimate']:.1f} % "
          f"(IC {100 * hl['achieved_level']:.1f} %: {100 * rr['ci95'][0]:.1f} a {100 * rr['ci95'][1]:.1f} %); "
          f"limiar de relevância {100 * rr['relevance_threshold']:.0f} %")
    print("melhor perda acumulada (média entre lotes) ao fim:", {k: round(v, 4) for k, v in r["final_best_balanced"].items()})
    if r["prereg_state"] != "frozen_ok":
        print(f"AVISO: pré-registro em estado {r['prereg_state']} — a análise só é confirmatória com o plano congelado")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1, default=float, ensure_ascii=False)


if __name__ == "__main__":
    main()
