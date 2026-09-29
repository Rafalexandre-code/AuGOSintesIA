#!/usr/bin/env python3
"""Análise causal GO–AuNP (§4.9): DAG explícito, estimação por ajuste de backdoor (DoWhy), refutações, E-value e
descoberta exploratória (causal-learn).

O DAG abaixo codifica as hipóteses da proposta (lote/fornecedor → descritores do GO → nucleação/tamanho → espectro;
impurezas dos reagentes; receita; bloco = dia/operador; hardware → temperatura efetiva). Edite `EDGES` conforme o
conhecimento do laboratório — a estimativa só é tão boa quanto o grafo. O delineamento (randomização e blocos em
aunp_syntheses.block/run_order) é a principal proteção contra confundimento; esta análise é complementar.

Uso:
    python code/causal/causal_analysis.py datasets/lab --treatment C_O_ratio --outcome spectral_loss_J
    python code/causal/causal_analysis.py datasets/lab --treatment iodide_reductant --outcome size_mean_nm
    python code/causal/causal_analysis.py datasets/lab --discover            # PC (causal-learn), exploratório
    python code/causal/causal_analysis.py --dot > dag.dot                   # desenha o DAG (graphviz)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "go_navigator"))

EDGES = [
    ("C_O_ratio", "size_mean_nm"), ("C_O_ratio", "spectral_loss_J"), ("ID_IG", "size_mean_nm"),
    ("iodide_reductant", "size_mean_nm"), ("iodide_reductant", "spectral_loss_J"),
    ("HAuCl4_mM", "size_mean_nm"), ("HAuCl4_mM", "spectral_loss_J"),
    ("reductant_to_Au_ratio", "size_mean_nm"), ("reductant_to_Au_ratio", "spectral_loss_J"),
    ("GO_mg_mL", "size_mean_nm"), ("GO_mg_mL", "spectral_loss_J"),
    ("pH", "size_mean_nm"), ("pH", "spectral_loss_J"), ("temperature_C", "size_mean_nm"),
    ("block", "temperature_C"), ("block", "spectral_loss_J"),
    ("size_mean_nm", "spectral_loss_J"),
    # o otimizador escolhe a receita olhando o lote → receita depende do contexto (confundimento a ajustar)
    ("C_O_ratio", "GO_mg_mL"), ("C_O_ratio", "pH"), ("C_O_ratio", "reductant_to_Au_ratio"),
    ("iodide_reductant", "reductant_to_Au_ratio"),
]


def gml(edges=EDGES) -> str:
    nodes = sorted({n for e in edges for n in e})
    s = "graph [directed 1\n" + "".join(f'  node [id "{n}" label "{n}"]\n' for n in nodes)
    s += "".join(f'  edge [source "{a}" target "{b}"]\n' for a, b in edges)
    return s + "]"


def dot(edges=EDGES) -> str:
    return "digraph GO_AuNP {\n  rankdir=LR;\n" + "".join(f'  "{a}" -> "{b}";\n' for a, b in edges) + "}\n"


def build_table(lab: str) -> pd.DataFrame:
    """Uma linha por síntese: receita, descritores do lote de GO (média), impurezas dos lotes, bloco, desfechos."""
    from batch_descriptors import batch_matrix
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["failed", "planned"])]
    out = pd.read_csv(os.path.join(lab, "outcomes.csv")).pivot_table(index="synthesis_id", columns="objective",
                                                                     values="value")
    df = syn.set_index("synthesis_id").join(out, how="inner")
    mean, _ = batch_matrix(lab)
    if not mean.empty:
        df = df.join(mean, on="go_batch_id")
    ra_path = os.path.join(lab, "reagent_analyses.csv")
    if os.path.exists(ra_path):
        per_lot = pd.read_csv(ra_path).pivot_table(index="lot_id", columns="analyte", values="value")
        per_lot.index = per_lot.index.astype(str)
        for role, col in (("gold", "gold_precursor_lot_id"), ("reductant", "reductant_lot_id"),
                          ("stabilizer", "stabilizer_lot_id")):
            if col in df:
                j = per_lot.reindex(df[col].astype(str)).add_suffix(f"_{role}")
                j.index = df.index
                df = df.join(j)
    if "block" in df:
        df["block"] = pd.factorize(df["block"].astype(str))[0].astype(float)
    return df


def e_value_rr(rr: float) -> float:
    """E-value para razão de riscos (VanderWeele & Ding, Ann. Intern. Med. 2017)."""
    rr = 1 / rr if rr < 1 else rr
    return rr + math.sqrt(rr * (rr - 1))


def e_value_continuous(effect: float, sd_outcome: float, ci: tuple[float, float] | None = None) -> dict:
    """E-value aproximado para desfecho contínuo: d = efeito/sd, RR ≈ exp(0,91·d) (VanderWeele 2017).
    Só interpretável se o estimando e a escala permitirem (§4.9)."""
    d = effect / sd_outcome
    out = {"standardized_effect_d": d, "e_value_point": e_value_rr(math.exp(0.91 * abs(d)))}
    if ci is not None:
        lo, hi = sorted(ci)
        near = 0.0 if lo <= 0 <= hi else (lo if lo > 0 else hi)
        out["e_value_ci"] = 1.0 if near == 0 else e_value_rr(math.exp(0.91 * abs(near / sd_outcome)))
    return out


def estimate(lab: str, treatment: str, outcome: str, edges=EDGES, refute: bool = True, n_sim: int = 50) -> dict:
    import dowhy
    df = build_table(lab)
    nodes = sorted({n for e in edges for n in e})
    missing = [n for n in nodes if n not in df or pd.to_numeric(df[n], errors="coerce").isna().all()]
    use_edges = [(a, b) for a, b in edges if a not in missing and b not in missing]
    if treatment in missing or outcome in missing:
        raise ValueError(f"tratamento/desfecho sem dados: {[n for n in (treatment, outcome) if n in missing]}")
    data = df[sorted({n for e in use_edges for n in e})].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 10:
        raise ValueError(f"só {len(data)} sínteses completas para o DAG — poucas para estimar um efeito")
    model = dowhy.CausalModel(data=data, treatment=treatment, outcome=outcome, graph=gml(use_edges))
    ident = model.identify_effect(proceed_when_unidentifiable=False)
    est = model.estimate_effect(ident, method_name="backdoor.linear_regression", confidence_intervals=True)
    ci = est.get_confidence_intervals()
    ci = tuple(np.ravel(ci).astype(float)) if ci is not None else None
    res = {"treatment": treatment, "outcome": outcome, "n": len(data), "dropped_nodes": missing,
           "backdoor_set": list(ident.get_backdoor_variables()), "effect_per_unit": float(est.value),
           "ci95": ci, **e_value_continuous(float(est.value) * float(data[treatment].std()),
                                            float(data[outcome].std()),
                                            tuple(c * float(data[treatment].std()) for c in ci) if ci else None)}
    if refute:
        refs = {}
        for name in ("placebo_treatment_refuter", "random_common_cause", "data_subset_refuter"):
            try:
                kw = {"num_simulations": n_sim, **({"placebo_type": "permute"} if name.startswith("placebo") else {})}
                r = model.refute_estimate(ident, est, method_name=name, **kw)
                refs[name] = {"new_effect": float(r.new_effect),
                              "p_value": float(r.refutation_result["p_value"]) if r.refutation_result else None}
            except Exception as exc:  # noqa: BLE001
                refs[name] = {"erro": str(exc)[:120]}
        res["refutations"] = refs
    return res


def discover(lab: str, alpha: float = 0.05) -> list[str]:
    """PC com teste de Fisher-z (causal-learn): arestas sugeridas — hipóteses, não conclusões."""
    from causallearn.search.ConstraintBased.PC import pc
    df = build_table(lab)
    cols = [c for c in sorted({n for e in EDGES for n in e}) if c in df]
    data = df[cols].apply(pd.to_numeric, errors="coerce")
    data = data.loc[:, data.notna().any()].dropna()          # colunas sem nenhum dado não derrubam todas as linhas
    data = data.loc[:, data.std() > 0]
    cg = pc(data.to_numpy(float), alpha=alpha, indep_test="fisherz", show_progress=False)
    names = list(data.columns)
    out = []
    G = cg.G.graph
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if G[i, j] == 0 and G[j, i] == 0:
                continue
            if G[i, j] == -1 and G[j, i] == 1:
                out.append(f"{names[i]} -> {names[j]}")
            elif G[i, j] == 1 and G[j, i] == -1:
                out.append(f"{names[j]} -> {names[i]}")
            else:
                out.append(f"{names[i]} -- {names[j]}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab_dir", nargs="?")
    ap.add_argument("--treatment", default="C_O_ratio")
    ap.add_argument("--outcome", default="spectral_loss_J")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--no-refute", action="store_true")
    ap.add_argument("--n-sim", type=int, default=50, help="simulações por refutação")
    ap.add_argument("--dot", action="store_true", help="imprime o DAG em DOT e sai")
    a = ap.parse_args()
    if a.dot:
        print(dot())
        return
    if not a.lab_dir:
        ap.error("informe a pasta de dados (ex.: datasets/lab)")
    if a.discover:
        print("\n".join(discover(a.lab_dir)))
        return
    print(json.dumps(estimate(a.lab_dir, a.treatment, a.outcome, refute=not a.no_refute, n_sim=a.n_sim), indent=1, default=float))


if __name__ == "__main__":
    main()
