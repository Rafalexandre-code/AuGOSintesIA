#!/usr/bin/env python3
"""Experimento fatorial 2×2 para o teste causal exploratório (§4.9, Objetivo 8; config → factorial_2x2).

Fatores: lote de GO (C/O alto × baixo) e impureza do reagente (CTAB limpo × contaminado), com a receita FIXA.
Desenho em blocos completos aleatorizados: cada dia (bloco) tem uma réplica de cada uma das 4 células, em ordem
sorteada — o dia não se confunde com nenhum fator. Fica fora das 60 sínteses do orçamento (é condicional).

Análise (escala log J, ou outro desfecho com --outcome):
  * efeitos principais e interação por contrastes: Δ_GO, Δ_imp e (Δ_imp | C/O baixo) − (Δ_imp | C/O alto);
  * efeitos principais por RANDOMIZAÇÃO RESTRITA exata: o rótulo de um fator só troca dentro do mesmo bloco e do
    mesmo nível do outro fator (2^(2r) atribuições) — válida sem normalidade e sem supor nada do outro fator;
  * permutação das 4 células dentro de cada bloco (nulo nítido "nenhum efeito"), como complemento;
  * interação: OLS com bloco (log J ~ GO × impureza + bloco), erros HC3 e IC 95 % — não há randomização que isole a
    interação com os efeitos principais presentes.
Poder por réplica no simulador: `campaign_sim.py --scenario factorial` (docs/SIMULACOES.md).
A interação responde à pergunta causal da proposta: o efeito da impureza depende da química do lote de GO?

Uso:
    python code/campaign/factorial.py plan --go-high L1 --go-low L3 --clean LOT-CTAB-A --contaminated LOT-CTAB-B \\
           [--replicates 3 --role stabilizer --gold LOT-AU] --out outputs/fatorial
    python code/campaign/factorial.py analyze datasets/lab [--outcome spectral_loss_J]
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
CAMPAIGN = "FACTORIAL"
CELLS = [("high", "clean"), ("high", "contaminated"), ("low", "clean"), ("low", "contaminated")]
ROLE_COLUMN = {"gold": "gold_precursor_lot_id", "reductant": "reductant_lot_id", "stabilizer": "stabilizer_lot_id"}


def design(go_high: str, go_low: str, clean: str, contaminated: str, replicates: int = 3, role: str = "stabilizer",
           recipe: dict | None = None, seed: int = 0, gold_lot: str = "") -> pd.DataFrame:
    """Linhas de aunp_syntheses (status planned) do fatorial em blocos completos aleatorizados."""
    import designer
    import plan as plan_mod
    import prereg
    space = prereg.search_space()
    recipe = recipe or plan_mod.reference_recipe(space)
    rng = np.random.default_rng(seed)
    cols = designer._syn_columns()
    rows = []
    for rep in range(1, replicates + 1):
        order = rng.permutation(len(CELLS))
        for pos, ci in enumerate(order, 1):
            go_lvl, imp_lvl = CELLS[ci]
            row = {c: "" for c in cols}
            sid = f"FAC-B{rep:02d}-{pos:02d}"
            row.update({"synthesis_id": sid, "go_batch_id": go_high if go_lvl == "high" else go_low,
                        "method": "in_situ_reduction_on_GO", "campaign_id": CAMPAIGN,
                        "design_id": f"FAC:{go_lvl}-{imp_lvl}-rep{rep}", "fidelity": "high", "block": f"FAC-DAY{rep:02d}",
                        "run_order": pos, "status": "planned", "preparation_id": f"PREP-{sid}", "is_control": "none",
                        "notes": f"fatorial 2×2: GO C/O {go_lvl}, impureza {imp_lvl} (§4.9)"})
            row[ROLE_COLUMN[role]] = clean if imp_lvl == "clean" else contaminated
            if gold_lot:
                row["gold_precursor_lot_id"] = gold_lot
            for k, v in recipe.items():
                if k in row:
                    row[k] = v
            rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def cell_table(lab: str, outcome: str = "spectral_loss_J", log: bool = True, eps: float = 1e-3) -> pd.DataFrame:
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    syn = syn[syn["campaign_id"].astype(str) == CAMPAIGN]
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["failed", "planned"])]
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    out = out[out["objective"] == outcome][["synthesis_id", "value"]]
    df = syn.merge(out, on="synthesis_id")
    parts = df["design_id"].astype(str).str.extract(r"FAC:(high|low)-(clean|contaminated)-rep(\d+)")
    df = df.assign(go=parts[0], imp=parts[1], block=parts[2].astype(int))
    df["y"] = np.log(df["value"].astype(float) + eps) if log else df["value"].astype(float)
    return df[["synthesis_id", "go", "imp", "block", "value", "y"]]


def contrasts(df: pd.DataFrame) -> dict:
    m = df.groupby(["go", "imp"])["y"].mean()
    d_imp_high = m[("high", "contaminated")] - m[("high", "clean")]
    d_imp_low = m[("low", "contaminated")] - m[("low", "clean")]
    return {"effect_impurity": float((d_imp_high + d_imp_low) / 2),
            "effect_GO_low_vs_high": float((m[("low", "clean")] + m[("low", "contaminated")]
                                            - m[("high", "clean")] - m[("high", "contaminated")]) / 2),
            "interaction": float(d_imp_low - d_imp_high),
            "impurity_effect_by_GO": {"high": float(d_imp_high), "low": float(d_imp_low)}}


def _weights(go: np.ndarray, imp: np.ndarray) -> np.ndarray:
    """Os três contrastes são lineares em y: c = W·y (linhas: impureza, GO, interação)."""
    n_cell = {c: np.sum((go == c[0]) & (imp == c[1])) for c in CELLS}
    nc = np.array([n_cell[(g, i)] for g, i in zip(go, imp)], float)
    s_imp = np.where(imp == "contaminated", 1.0, -1.0)
    s_go = np.where(go == "low", 1.0, -1.0)
    return np.vstack([s_imp / (2 * nc), s_go / (2 * nc), s_imp * s_go / nc])


def restricted_test(df: pd.DataFrame, factor: str, n_mc: int = 200_000, seed: int = 0) -> dict:
    """Efeito principal de UM fator sem supor nada do outro: o rótulo do fator só troca entre as unidades do mesmo
    bloco e do mesmo nível do outro fator (a randomização que o desenho realmente fez para esse contraste).
    Com r réplicas: 2^(2r) atribuições por célula de 1 unidade (r = 3 → 64; p bilateral mínimo 2/64)."""
    other = "go" if factor == "imp" else "imp"
    d = df.sort_values(["block", other, factor]).reset_index(drop=True)
    W = _weights(d["go"].to_numpy(), d["imp"].to_numpy())[0 if factor == "imp" else 1]
    y = d["y"].to_numpy(float)
    obs = float(W @ y)
    strata = [np.asarray(g) for g in d.groupby(["block", other]).indices.values()]
    perms = [np.array(list(itertools.permutations(g))) for g in strata]
    total = int(np.prod([float(len(p)) for p in perms]))
    rng = np.random.default_rng(seed)
    if total <= n_mc:
        grids = np.meshgrid(*[np.arange(len(p)) for p in perms], indexing="ij")
        choice = np.stack([g.ravel() for g in grids], axis=1)
    else:
        choice = np.stack([rng.integers(len(p), size=n_mc) for p in perms], axis=1)
    idx = np.concatenate([perms[b][choice[:, b]] for b in range(len(perms))], axis=1)
    pos = np.concatenate(strata)
    Y = np.empty((len(idx), len(y)))
    Y[:, pos] = y[idx]
    sims = Y @ W
    return {"estimate": obs, "p_two_sided": float(np.mean(np.abs(sims) >= abs(obs) - 1e-12)),
            "n_assignments": int(len(sims)), "exact": total <= n_mc}


def permutation_test(df: pd.DataFrame, n_mc: int = 200_000, seed: int = 0) -> dict:
    """p bilaterais exatos (ou Monte Carlo) permutando os rótulos das 4 células dentro de cada bloco. Testa o nulo
    NÍTIDO "nenhuma célula difere": para um efeito principal com o outro fator ativo fica conservador (o outro
    efeito entra na distribuição nula) — use restricted_test; para a interação, o OLS com bloco."""
    d = df.sort_values(["block", "go", "imp"]).reset_index(drop=True)
    W = _weights(d["go"].to_numpy(), d["imp"].to_numpy())
    y = d["y"].to_numpy(float)
    obs = W @ y
    groups = [np.flatnonzero(d["block"].to_numpy() == b) for b in sorted(d["block"].unique())]
    perms = [np.array(list(itertools.permutations(g))) for g in groups]
    total = int(np.prod([len(p) for p in perms]))
    rng = np.random.default_rng(seed)
    if total <= n_mc:
        grids = np.meshgrid(*[np.arange(len(p)) for p in perms], indexing="ij")
        choice = np.stack([g.ravel() for g in grids], axis=1)
        exact = True
    else:
        choice = np.stack([rng.integers(len(p), size=n_mc) for p in perms], axis=1)
        exact = False
    idx = np.concatenate([perms[b][choice[:, b]] for b in range(len(perms))], axis=1)   # (n_perm × n)
    pos = np.concatenate(groups)
    Y = np.empty((len(idx), len(y)))
    Y[:, pos] = y[idx]
    sims = Y @ W.T
    keys = ("effect_impurity", "effect_GO_low_vs_high", "interaction")
    return {"exact": exact, "n_permutations": int(len(sims)),
            "p_two_sided": {k: float(np.mean(np.abs(sims[:, j]) >= abs(obs[j]) - 1e-12)) for j, k in enumerate(keys)}}


def ols(df: pd.DataFrame) -> dict:
    import statsmodels.formula.api as smf
    d = df.assign(go_low=(df["go"] == "low").astype(float), contaminated=(df["imp"] == "contaminated").astype(float))
    fit = smf.ols("y ~ go_low * contaminated + C(block)", data=d).fit(cov_type="HC3")
    ci = fit.conf_int()
    out = {}
    for term, name in (("go_low", "GO_low_at_clean"), ("contaminated", "impurity_at_high_CO"),
                       ("go_low:contaminated", "interaction")):
        out[name] = {"coef": float(fit.params[term]), "ci95": [float(ci.loc[term, 0]), float(ci.loc[term, 1])],
                     "p": float(fit.pvalues[term])}
    out["r2"] = float(fit.rsquared)
    return out


def analyze(lab: str, outcome: str = "spectral_loss_J", log: bool = True) -> dict:
    df = cell_table(lab, outcome, log)
    n = df.groupby(["go", "imp"]).size()
    if len(n) < 4:
        raise SystemExit(f"fatorial incompleto: células com dados {n.to_dict()}")
    return {"outcome": outcome, "scale": "log" if log else "linear", "n_per_cell": n.to_dict(),
            "cell_means": df.groupby(["go", "imp"])["y"].mean().to_dict(), **contrasts(df),
            "main_effects_restricted_randomization": holm({"impurity": restricted_test(df, "imp"),
                                                           "GO_low_vs_high": restricted_test(df, "go")}),
            "permutation_sharp_null": permutation_test(df), "ols_hc3": ols(df)}


def holm(tests: dict) -> dict:
    """Acrescenta p_holm (Holm–Bonferroni entre os efeitos principais, como no pré-registro → premise_test)."""
    names = sorted(tests, key=lambda k: tests[k]["p_two_sided"])
    m, running = len(names), 0.0
    for i, k in enumerate(names):
        running = max(running, min(1.0, (m - i) * tests[k]["p_two_sided"]))
        tests[k]["p_holm"] = running
    return tests


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    for k in ("--go-high", "--go-low", "--clean", "--contaminated"):
        p.add_argument(k, required=True)
    p.add_argument("--replicates", type=int)
    p.add_argument("--role", choices=list(ROLE_COLUMN))
    p.add_argument("--gold", default="", help="lote de HAuCl4 (obrigatório no modelo de dados)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default=os.path.join(ROOT, "outputs", "fatorial"))
    q = sub.add_parser("analyze")
    q.add_argument("lab")
    q.add_argument("--outcome", default="spectral_loss_J")
    q.add_argument("--linear", action="store_true", help="desfecho na escala original (padrão: log)")
    a = ap.parse_args()
    if a.cmd == "plan":
        import prereg
        spec = prereg.load().get("factorial_2x2", {}) or {}
        syn = design(a.go_high, a.go_low, a.clean, a.contaminated, a.replicates or int(spec.get("replicates", 3)),
                     a.role or spec.get("impurity_role", "stabilizer"), seed=a.seed, gold_lot=a.gold)
        os.makedirs(a.out, exist_ok=True)
        f = os.path.join(a.out, "fatorial_aunp_syntheses.csv")
        syn.to_csv(f, index=False)
        print(syn[["synthesis_id", "block", "run_order", "go_batch_id", "design_id"]].to_string(index=False))
        print(f"-> {os.path.relpath(f, ROOT)} ({len(syn)} sínteses, {syn['block'].nunique()} blocos)")
    else:
        r = analyze(a.lab, a.outcome, not a.linear)
        print(json.dumps(r, indent=1, default=lambda o: str(o) if isinstance(o, tuple) else float(o), ensure_ascii=False))


if __name__ == "__main__":
    main()
