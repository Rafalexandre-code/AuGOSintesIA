#!/usr/bin/env python3
"""Análise pré-registrada da comparação entre braços (§4.18; config/preregistration.yaml → arms, primary_outcome).

Por que esta estrutura (simulação registrada em docs/SIMULACOES.md, cenário prospectivo): com o orçamento real, o
teste por rodada na fase ADAPTATIVA tem poder ≈ 0 e é anticonservador (erro tipo I ≈ 12 % no par nulo), porque a
vantagem de uma trajetória numa rodada se arrasta para as seguintes. A inferência confirmatória fica onde as
observações são independentes: a CONFIRMAÇÃO nos lotes reservados, com modelos congelados.

1. PRIMÁRIO — valor preditivo da informação de contexto (§6.1 cenários 1–4): antes de sintetizar, o modelo
   só-receita e o contextual, CONGELADOS e treinados nos mesmos dados de desenvolvimento, preveem log J de cada
   síntese de confirmação (confirmation_predictions.csv, gravado por plan.py confirm). Por síntese i:
       d_i = (ŷ_ctx,i − y_i)² − (ŷ_ref,i − y_i)²      (negativo = o contexto previu melhor um lote NUNCA visto)
   Teste de randomização por troca de sinais (unilateral), Hodges–Lehmann com IC exato e razão de RMSE.
2. SECUNDÁRIO — otimização em lotes novos: nos pares de confirmação (uma receita de cada braço congelado, mesmo
   lote e dia), d_p = log J(trat) − log J(ref); mesmo teste.
3. EXPLORATÓRIO — fase adaptativa: d_r por rodada pareada e curvas de melhor perda acumulada por braço
   (o desfecho da proposta, aqui descritivo; o p-valor é reportado com o aviso de anticonservadorismo).

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


def confirmation_long(lab: str, objective: str = "spectral_loss_J") -> pd.DataFrame:
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    syn = syn[syn["campaign_id"].astype(str) == "CONFIRMATION"]
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["failed", "planned"])]
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    df = syn.merge(out[out["objective"] == objective][["synthesis_id", "value"]], on="synthesis_id")
    parts = df["design_id"].astype(str).str.extract(r"^(.+):conf-p(\d+)$")
    return df.assign(arm=parts[0], pair=pd.to_numeric(parts[1]))


def _paired_block(d: np.ndarray, level: float) -> dict:
    hl = hodges_lehmann(d, level)
    return {"n": int(len(d)), "p_value_sign_flip_one_sided": sign_flip_test(d, "less") if len(d) else float("nan"),
            "hodges_lehmann": hl}


def predictive_comparison(lab: str, ref_rep: str, trt_rep: str, eps: float, level: float = 0.95,
                          predictions: pd.DataFrame | None = None) -> dict:
    """Primário: erro quadrático de previsão de log J (modelos congelados) contextual × só-receita, por síntese."""
    path = os.path.join(lab, "confirmation_predictions.csv")
    preds = predictions if predictions is not None else (pd.read_csv(path) if os.path.exists(path) else None)
    conf = confirmation_long(lab)
    if preds is None or conf.empty:
        return {"status": "sem confirmação ou sem confirmation_predictions.csv (plan.py confirm)"}
    w = preds.pivot_table(index="synthesis_id", columns="representation", values="pred_logJ")
    if ref_rep not in w or trt_rep not in w:
        return {"status": f"previsões sem {ref_rep} e/ou {trt_rep}"}
    y = np.log(conf.set_index("synthesis_id")["value"].astype(float) + eps)
    j = w.join(y.rename("y"), how="inner")
    e_ref, e_trt = (j[ref_rep] - j["y"]) ** 2, (j[trt_rep] - j["y"]) ** 2
    d = (e_trt - e_ref).to_numpy(float)
    rmse_ref, rmse_trt = float(np.sqrt(e_ref.mean())), float(np.sqrt(e_trt.mean()))
    return {**_paired_block(d, level), "rmse_reference": rmse_ref, "rmse_treatment": rmse_trt,
            "rmse_ratio": rmse_trt / rmse_ref if rmse_ref > 0 else float("nan"),
            "relative_error_reduction": 1 - rmse_trt / rmse_ref if rmse_ref > 0 else float("nan")}


def confirmation_optimization(lab: str, ref: str, trt: str, eps: float, level: float = 0.95) -> dict:
    conf = confirmation_long(lab)
    if conf.empty:
        return {"status": "sem confirmação"}
    conf["logJ"] = np.log(conf["value"].astype(float) + eps)
    w = conf.pivot_table(index="pair", columns="arm", values="logJ").dropna()
    if ref not in w or trt not in w:
        return {"status": "pares incompletos"}
    d = (w[trt] - w[ref]).to_numpy(float)
    hl = _paired_block(d, level)
    hl["relative_reduction"] = 1 - float(np.exp(hl["hodges_lehmann"]["estimate"])) if len(d) else float("nan")
    return hl


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
    rep = {k: k for k in (ref, trt)}                  # braço = representação no desenho pré-registrado
    primary = predictive_comparison(lab, rep[ref], rep[trt], eps, level)
    secondary = confirmation_optimization(lab, ref, trt, eps, level)
    return {"primary_predictive_value": primary, "secondary_confirmation_optimization": secondary,
            "exploratory_adaptive_warning": "fase adaptativa: teste anticonservador sob dependência entre rodadas "
                                            "(erro tipo I simulado acima de α); leia como descritivo",
            "reference_arm": ref, "treatment_arm": trt, "n_pairs": int(len(d)), "epsilon": eps,
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
    pp, so = r["primary_predictive_value"], r["secondary_confirmation_optimization"]
    if "n" in pp:
        print(f"PRIMÁRIO (previsão em lotes reservados, {pp['n']} sínteses): RMSE de log J "
              f"{pp['rmse_treatment']:.3f} ({r['treatment_arm']}) × {pp['rmse_reference']:.3f} ({r['reference_arm']}); "
              f"redução {100 * pp['relative_error_reduction']:.0f} %; p = {pp['p_value_sign_flip_one_sided']:.4f}")
    else:
        print("PRIMÁRIO:", pp.get("status"))
    if "n" in so:
        print(f"SECUNDÁRIO (otimização, {so['n']} pares de confirmação): redução HL de J "
              f"{100 * so['relative_reduction']:.0f} %; p = {so['p_value_sign_flip_one_sided']:.4f}")
    hl, rr = r["hodges_lehmann_log_ratio"], r["relative_reduction"]
    print(f"EXPLORATÓRIO — {r['treatment_arm']} × {r['reference_arm']}: {r['n_pairs']} rodadas pareadas; "
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
