#!/usr/bin/env python3
"""Simulação de campanha, benchmark e poder (§4.11, §4.15, §4.18) com o laboratório SIMULADO (sim_lab.py).

Cenário `main` (desenvolvimento, lotes L1–L3): todos os braços com a MESMA inicialização (4 receitas × L1–L3 = 12
sínteses, como na proposta), mesmo alvo e orçamento; rodadas adaptativas alternando o lote-alvo. Desfecho primário
pré-registrado: melhor perda J acumulada por rodada, média balanceada entre lotes. Braços (nome: representação +
estratégia):
  random                Sobol, sem modelo
  recipe | batch | go | go+impurities | hierarchical      GP Matérn-5/2 + ARD + qNEHVI (o Designer), por representação
  gp-ei                 GP (representação go) + qLogNEI só em J — a BO clássica de um objetivo
  rf-qnehvi             floresta aleatória (ensemble) + qNEHVI sobre candidatos (representação go)
  novelty-w<w>          Designer 'go' com seleção novelty-aware, w de config/preregistration.yaml → novelty.weights
  dnn-qnehvi | egbo | optuna-tpe | autopilot   exploratórios (strategies.py; aunp_designer/autopilot.py)
Comparação: Friedman, Wilcoxon pareado + Holm, redução relativa com IC por bootstrap, poder por reamostragem e
EXPERIMENTOS ATÉ O CRITÉRIO (critério = mediana final do braço de referência), com censura no orçamento:
média restrita (RMST, Kaplan–Meier) e teste log-rank contra a referência.

Cenário `prospective` (o desenho REAL pré-registrado, config/preregistration.yaml → arms): 8 piloto + 12 de
inicialização compartilhados e 12 rodadas pareadas — em cada rodada, cada braço propõe 1 síntese no mesmo lote, com
modelo treinado só nos dados compartilhados + nas suas rodadas; depois 8 pares de confirmação em L4–L6. Mede o
poder do desfecho primário (code/campaign/analysis.py: valor preditivo do contexto com o LOTE como unidade) e o erro
tipo I nos pares "placebo" (contexto registrado sem informação) e "null" (braços idênticos). `--resume` acrescenta o
desfecho por lote a campanhas gravadas antes dele (refaz as previsões congeladas).

Cenário `batches`: as mesmas 60 sínteses repartidas entre K = 6…16 lotes (poder e erro tipo I do desfecho por lote).
Cenário `factorial`: poder do fatorial 2×2 (§4.9) por nº de réplicas, com a análise pré-registrada (factorial.py).

Cenário `transfer` (lote reservado L4, §4.7): "do zero" (receita, só dados do L4: 4 receitas LHS + rodadas) contra
"transfer-go" e "transfer-hierarchical" (24 sínteses de L1–L3 como histórico, nenhuma no L4 antes da 1ª rodada).
Métrica da proposta: nº de experimentos NO L4 até igualar o desempenho final do do-zero (com censura) e economia
relativa (code/transfer_learning/hierarchical.py → experiments_to_match).

Uso:
    python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --q 2 --workers 4                # cenário main
    python code/benchmarking/campaign_sim.py --scenario transfer --seeds 10 --workers 4
    python code/benchmarking/campaign_sim.py --scenario prospective --seeds 40 --workers 4      # desenho real + nulo
    python code/benchmarking/campaign_sim.py --scenario batches --seeds 40 --workers 4          # mais lotes
    python code/benchmarking/campaign_sim.py --scenario factorial --seeds 100 --workers 4       # fatorial 2×2
    python code/benchmarking/campaign_sim.py --seeds 2 --rounds 3 --arms recipe go                    # teste rápido
    python code/benchmarking/campaign_sim.py report outputs/campaign_sim > docs/SIMULACOES.md         # resumo
Saídas em outputs/campaign_sim/<cenário>/: jobs/*.json (retomáveis com --resume), curves.csv, final.csv,
summary.json. Os números valem para o SIMULADOR — dimensionam e testam o protocolo; não preveem o ganho real.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "aunp_designer"), os.path.join(ROOT, "code", "transfer_learning")]
import designer  # noqa: E402
import sim_lab  # noqa: E402
import stats  # noqa: E402

BATCHES = ("L1", "L2", "L3")
NEW_BATCH = "L4"


def _novelty_weights() -> list[float]:
    try:
        import prereg
        return [float(w) for w in prereg.load()["novelty"]["weights"]]
    except Exception:          # noqa: BLE001
        return [0.0, 0.25, 0.5, 0.75, 1.0]


ARMS = {"random": ("recipe", "random", {}), "recipe": ("recipe", "gp-qnehvi", {}),
        "batch": ("batch", "gp-qnehvi", {}), "go": ("go", "gp-qnehvi", {}),
        "go+impurities": ("go+impurities", "gp-qnehvi", {}), "hierarchical": ("hierarchical", "gp-qnehvi", {}),
        "gp-ei": ("go", "gp-ei", {}), "rf-qnehvi": ("go", "rf-qnehvi", {}),
        # exploratórios da §4.15
        "dnn-qnehvi": ("go", "dnn-qnehvi", {}), "egbo": ("go", "egbo", {}), "optuna-tpe": ("go", "optuna-tpe", {}),
        "autopilot": ("go", "autopilot", {})}
ARMS.update({f"novelty-w{w:g}": ("go", "novelty", {"w": w}) for w in _novelty_weights()})
# Cenário prospectivo (o desenho REAL: 8 piloto + 12 inicialização compartilhados; 12 rodadas pareadas, 1 síntese
# de cada braço por rodada, cada braço com a sua trajetória). "null" usa dois braços idênticos para medir o erro
# tipo I do teste sob a dependência adaptativa.
PROSPECTIVE = {"contextual": (("recipe", "recipe"), ("go+impurities", "go+impurities")),
               "placebo": (("recipe", "recipe"), ("go+impurities", "go+impurities")),   # contexto sem informação
               "null": (("recipe", "recipe"), ("recipe_bis", "recipe"))}
RESERVED = ("L4", "L5", "L6")
# Cenário `batches`: poder do desfecho primário com mais LOTES de GO e o mesmo orçamento (60 sínteses repartidas
# entre K lotes). Lotes extras do simulador com C/O sorteado na faixa de L1–L6; "placebo" = contexto sem informação.
BATCH_SIZING = {f"{kind}-K{k}": (kind, k) for kind in ("contextual", "placebo") for k in (6, 9, 12, 16)}
SIZING_BUDGET = 60
# Cenário `factorial`: poder do fatorial 2×2 (§4.9) por nº de réplicas (blocos) — "effect" = L1 × L3 (C/O 2,2 × 1,5)
# e RED-A × RED-B (iodeto 2 × 45 ppm); "null" = mesmo lote de GO e mesmo lote de redutor rotulados como níveis.
FACTORIAL_SIZING = {f"{kind}-r{r}": (kind, r) for kind in ("effect", "null") for r in (3, 4, 6)}


def _placebo(lab: str, seed: int) -> None:
    """Contexto registrado SEM informação (o simulador continua usando a química verdadeira): os descritores de GO
    trocam de lote (permutação sem ponto fixo); os lotes de redutor são embaralhados nos registros por _run. Trocar
    só os valores de impureza entre os 2 lotes NÃO serve de placebo — a distinção entre lotes continuaria informativa."""
    rng = np.random.default_rng(seed + 991)
    d = pd.read_csv(os.path.join(lab, "go_descriptors.csv"))
    ids = sorted(d["go_batch_id"].unique())
    while True:
        perm = rng.permutation(ids)
        if not np.any(perm == np.array(ids)):
            break
    d["go_batch_id"] = d["go_batch_id"].map(dict(zip(ids, perm)))
    d.to_csv(os.path.join(lab, "go_descriptors.csv"), index=False)


def _run(lab: str, syn: pd.DataFrame, rng: np.random.Generator, scramble: np.random.Generator | None = None) -> None:
    """Sintetiza no simulador; com `scramble` (placebo), o lote de redutor REGISTRADO passa a ser sorteado,
    independente do lote usado — a impureza registrada deixa de carregar informação."""
    import simulator as sim
    sim_lab.run_syntheses(lab, syn, rng)
    if scramble is not None:
        path = os.path.join(lab, "aunp_syntheses.csv")
        t = pd.read_csv(path)
        new = t["synthesis_id"].isin(syn["synthesis_id"])
        t.loc[new, "reductant_lot_id"] = scramble.choice(sorted(sim.REAGENT_LOTS), int(new.sum()))
        t.to_csv(path, index=False)


TRANSFER_ARMS = {"scratch": ("recipe", "gp-qnehvi", {}), "transfer-go": ("go", "gp-qnehvi", {}),
                 "transfer-hierarchical": ("hierarchical", "gp-qnehvi", {})}


def _best(lab: str, batches) -> float:
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))[["synthesis_id", "go_batch_id"]]
    j = out[out["objective"] == "spectral_loss_J"].merge(syn, on="synthesis_id")
    return float(j.groupby("go_batch_id")["value"].min().reindex(list(batches)).mean())


def _loss_sequence(lab: str, batch: str) -> list[float]:
    """Perdas das sínteses de um lote, na ordem em que foram feitas."""
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))[["synthesis_id", "go_batch_id"]]
    j = syn.merge(out[out["objective"] == "spectral_loss_J"], on="synthesis_id")
    return j.loc[j["go_batch_id"] == batch, "value"].astype(float).tolist()


def _propose(arm_spec, lab: str, space: dict, target: str, lots: dict, q: int, seed: int, acq: str | None,
             arm: str | None = None):
    """Uma rodada de qualquer braço -> DataFrame de receitas (colunas do espaço). Com `arm`, o modelo só vê os dados
    compartilhados e as rodadas desse braço (comparação prospectiva pareada)."""
    import strategies
    rep, strat, kw = arm_spec
    if strat == "autopilot":
        import autopilot
        return autopilot.propose(lab, space, target, lots, q, seed, acq, arm=arm)
    if strat == "random":
        from scipy.stats import qmc
        lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
        return pd.DataFrame(qmc.scale(qmc.Sobol(len(space), seed=seed).random(q), lo, hi), columns=list(space))
    camp = designer.load_campaign(lab, space, rep, designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints(), arm=arm)
    fixed = designer.fixed_context(lab, camp, target, lots)
    if strat == "gp-qnehvi":
        return designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed)
    if strat == "novelty":
        return designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed, novelty_w=kw["w"])
    if strat == "gp-ei":
        return strategies.propose_gp_ei(camp, space, q, fixed, seed)
    if strat == "rf-qnehvi":
        return strategies.propose_rf_qnehvi(camp, space, q, fixed, seed)
    if strat in ("dnn-qnehvi", "egbo", "optuna-tpe"):
        return getattr(strategies, "propose_" + strat.replace("-", "_"))(camp, space, q, fixed, seed)
    raise ValueError(strat)


def _lhs(space: dict, n: int, seed: int) -> pd.DataFrame:
    from scipy.stats import qmc
    lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
    return pd.DataFrame(qmc.scale(qmc.LatinHypercube(len(space), seed=seed).random(n), lo, hi), columns=list(space))


def run_campaign(arm: str, seed: int, rounds: int, q: int, root: str, acq: str | None = None) -> list[dict]:
    space = designer.DEFAULT_SPACE
    lab = os.path.join(root, "labs", f"{arm.replace('+', '_')}_s{seed}", "lab")
    sim_lab.init_lab(lab, BATCHES, seed=seed)
    rng = np.random.default_rng(seed)
    recipes = _lhs(space, 4, seed)
    for b in BATCHES:
        syn = designer.proposals_to_syntheses(recipes, space, b, f"INIT-{b}", 0, seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
    curve = [{"arm": arm, "seed": seed, "round": 0, "n": 12, "best_loss": _best(lab, BATCHES)}]
    for r in range(1, rounds + 1):
        target = BATCHES[(r - 1) % len(BATCHES)]
        lots = {"reductant": ("RED-A", "RED-B")[r % 2]}           # lotes de reagente variam entre rodadas
        cands = _propose(ARMS[arm], lab, space, target, lots, q, seed * 1000 + r, acq)
        syn = designer.proposals_to_syntheses(cands, space, target, "SIM", r, lots=lots, seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
        curve.append({"arm": arm, "seed": seed, "round": r, "n": 12 + r * q, "best_loss": _best(lab, BATCHES)})
    return curve


def run_transfer(arm: str, seed: int, budget: int, q: int, root: str, acq: str | None = None) -> list[dict]:
    """Curva do melhor J no lote novo por nº de experimentos NESSE lote (1..budget)."""
    space = designer.DEFAULT_SPACE
    lab = os.path.join(root, "labs", f"{arm}_s{seed}", "lab")
    rng = np.random.default_rng(seed)
    if arm == "scratch":
        sim_lab.init_lab(lab, (NEW_BATCH,), seed=seed)
        syn = designer.proposals_to_syntheses(_lhs(space, 4, seed + 7), space, NEW_BATCH, "INIT-L4", 0,
                                              seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
    else:
        sim_lab.init_lab(lab, BATCHES + (NEW_BATCH,), seed=seed)
        hist = pd.concat([_lhs(space, 4, seed), _lhs(space, 4, seed + 100)], ignore_index=True)
        for b in BATCHES:                                        # histórico: 8 sínteses por lote de desenvolvimento
            syn = designer.proposals_to_syntheses(hist, space, b, f"HIST-{b}", 0, seed=seed).assign(status="done")
            sim_lab.run_syntheses(lab, syn, rng)
    r = 0
    while len(_loss_sequence(lab, NEW_BATCH)) < budget:
        r += 1
        lots = {"reductant": ("RED-A", "RED-B")[r % 2]}
        n_left = budget - len(_loss_sequence(lab, NEW_BATCH))
        cands = _propose(TRANSFER_ARMS[arm], lab, space, NEW_BATCH, lots, min(q, n_left), seed * 1000 + r, acq)
        syn = designer.proposals_to_syntheses(cands, space, NEW_BATCH, "TL", r, lots=lots, seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, syn, rng)
    seq = np.minimum.accumulate(_loss_sequence(lab, NEW_BATCH)[:budget])
    return [{"arm": arm, "seed": seed, "n": i + 1, "best_loss": float(v)} for i, v in enumerate(seq)]


def run_prospective(pair: str, seed: int, rounds: int, root: str, acq: str | None = None) -> list[dict]:
    """Uma campanha com o desenho pré-registrado; devolve d_r por rodada e, na última linha, o teste e o HL."""
    sys.path.insert(0, os.path.join(ROOT, "code", "campaign"))
    import analysis
    import plan as plan_mod
    space = designer.DEFAULT_SPACE
    lab = os.path.join(root, "labs", f"{pair}_s{seed}", "lab")
    sim_lab.init_lab(lab, BATCHES + RESERVED, seed=seed)       # reservados caracterizados, nunca no treino
    scramble = np.random.default_rng(seed + 4049) if pair == "placebo" else None
    if scramble is not None:
        _placebo(lab, seed)
    rng = np.random.default_rng(seed)
    ref = pd.DataFrame([plan_mod.reference_recipe(space)])
    for b, n in zip(BATCHES, (4, 2, 2)):                      # piloto: receita de referência, 8 preparações
        syn = designer.proposals_to_syntheses(pd.concat([ref] * n, ignore_index=True), space, b, f"PILOT-{b}", 0,
                                              seed=seed).assign(status="done")
        _run(lab, syn, rng, scramble)
    recipes = _lhs(space, 4, seed)
    for b in BATCHES:
        syn = designer.proposals_to_syntheses(recipes, space, b, f"INIT-{b}", 0, seed=seed).assign(status="done")
        _run(lab, syn, rng, scramble)
    (ref_name, ref_rep), (trt_name, trt_rep) = PROSPECTIVE[pair]
    for r in range(1, rounds + 1):
        target = BATCHES[(r - 1) % len(BATCHES)]
        lots = {"reductant": ("RED-A", "RED-B")[r % 2]}
        new = []
        for k, (name, rep) in enumerate(((ref_name, ref_rep), (trt_name, trt_rep))):
            cands = _propose((rep, "gp-qnehvi", {}), lab, space, target, lots, 1, seed * 1000 + 10 * r + k, acq,
                             arm=name)
            new.append(designer.proposals_to_syntheses(cands, space, target, f"ADAPT-{name.replace('+', '_')}", r,
                                                       lots=lots, seed=seed, arm=name).assign(status="done"))
        _run(lab, pd.concat(new, ignore_index=True), rng, scramble)
    eps = designer.default_eps()
    # confirmação: 8 pares nos lotes reservados com os braços congelados + previsões congeladas
    lots = {"reductant": "RED-B"}
    conf, preds = plan_mod.confirm_paired(lab, [(ref_name, ref_rep), (trt_name, trt_rep)], list(RESERVED), 8, space,
                                          designer.default_logs(), eps, designer.default_constraints(), acq, lots,
                                          seed)
    sim_lab.run_syntheses(lab, conf.assign(status="done"), rng)
    prim = analysis.predictive_comparison(lab, ref_rep, trt_rep, eps, predictions=preds)
    sec = analysis.confirmation_optimization(lab, ref_name, trt_name, eps)
    bl = _batch_level(lab, ref_rep, trt_rep, preds)
    df = analysis.load_long(lab)
    pairs = analysis.paired_differences(df, ref_name, trt_name, eps)
    hl = analysis.hodges_lehmann(pairs["d"].to_numpy())
    cur = analysis.cumulative_curves(df, [ref_name, trt_name], list(BATCHES)).pivot(index="round", columns="arm",
                                                                                        values="best_loss_balanced")
    rows = [{"arm": pair, "seed": seed, "n": int(rr["round"]), "d": float(rr["d"]),
             "best_ref": float(cur.loc[int(rr["round"]), ref_name]), "best_loss": float(cur.loc[int(rr["round"]), trt_name])}
            for _, rr in pairs.iterrows()]
    rows[-1].update({"p_sign_flip": analysis.sign_flip_test(pairs["d"].to_numpy()), "hl": hl["estimate"],
                     "hl_lo": hl["ci"][0], "hl_hi": hl["ci"][1],
                     "p_predictive": prim.get("p_value_sign_flip_one_sided", np.nan),
                     "rmse_ratio": prim.get("rmse_ratio", np.nan),
                     "p_confirm_opt": sec.get("p_value_sign_flip_one_sided", np.nan),
                     "confirm_hl": sec.get("hodges_lehmann", {}).get("estimate", np.nan), **bl})
    return rows


def _batch_level(lab: str, ref_rep: str, trt_rep: str, preds=None) -> dict:
    """Desfecho primário com o LOTE como unidade (analysis.batch_level_predictive): p exato e d_b por lote."""
    sys.path.insert(0, os.path.join(ROOT, "code", "campaign"))
    import analysis
    r = analysis.batch_level_predictive(lab, ref_rep, trt_rep, designer.default_eps(), predictions=preds,
                                        dev_batches=list(BATCHES))
    if "n_batches" not in r:
        return {"p_batch": np.nan, "batch_ratio": np.nan, "batch_d": []}
    return {"p_batch": r["p_value_sign_flip_one_sided"], "batch_ratio": r["rmse_ratio_estimate"],
            "batch_d": [float(x["d"]) for x in r["per_batch"]]}


def _augment_prospective(path: str, root: str) -> dict:
    """Campanhas prospectivas gravadas antes do desfecho por lote: recalcula-o do laboratório salvo (as previsões
    congeladas só dependem dos dados de desenvolvimento, então são refeitas de forma idêntica)."""
    import torch
    torch.set_num_threads(1)
    warnings.simplefilter("ignore")
    with open(path, encoding="utf-8") as fh:
        res = json.load(fh)
    last = res["curve"][-1]
    if "p_batch" not in last:
        (_, ref_rep), (_, trt_rep) = PROSPECTIVE[res["arm"]]
        last.update(_batch_level(os.path.join(root, "labs", f"{res['arm']}_s{res['seed']}", "lab"), ref_rep, trt_rep))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
    return res


def _register_batches(k: int, seed: int) -> list[str]:
    """K lotes novos no simulador: C/O ~ U(1,5; 2,4) (faixa de L1–L6) e ID/IG na mesma relação aproximada."""
    import simulator as sim
    rng = np.random.default_rng(seed + 7919 * k)
    names = [f"K{k}S{seed}B{i:02d}" for i in range(k)]
    for b, co in zip(names, rng.uniform(1.5, 2.4, k)):
        sim.BATCHES[b] = {"C_O_ratio": float(co), "ID_IG": float(1.36 - 0.2 * co + rng.normal(0, 0.01))}
    return names


def run_batches(name: str, seed: int, root: str, budget: int = SIZING_BUDGET) -> list[dict]:
    """Desfecho primário (valor preditivo por lote, leave-one-batch-out do modelo agrupado) com K lotes e o
    orçamento fixo: receitas LHS em cada lote, metade com cada lote de redutor."""
    sys.path.insert(0, os.path.join(ROOT, "code", "campaign"))
    import analysis
    kind, k = BATCH_SIZING[name]
    space = designer.DEFAULT_SPACE
    lab = os.path.join(root, "labs", f"{name}_s{seed}", "lab")
    names = _register_batches(k, seed)
    sim_lab.init_lab(lab, names, seed=seed)
    scramble = np.random.default_rng(seed + 4049) if kind == "placebo" else None
    if scramble is not None:
        _placebo(lab, seed)
    rng = np.random.default_rng(seed)
    sizes = [budget // k + (i < budget % k) for i in range(k)]
    for i, (b, n) in enumerate(zip(names, sizes)):
        rec = _lhs(space, n, seed * 1000 + i)
        for h, lot in enumerate(("RED-A", "RED-B")):
            part = rec.iloc[h::2].reset_index(drop=True)
            if len(part):
                syn = designer.proposals_to_syntheses(part, space, b, f"SIZING-{b}-{lot}", 0, lots={"reductant": lot},
                                                      seed=seed).assign(status="done")
                _run(lab, syn, rng, scramble)
    r = analysis.batch_level_predictive(lab, "recipe", "go+impurities", designer.default_eps())
    best = float(pd.read_csv(os.path.join(lab, "outcomes.csv")).query("objective == 'spectral_loss_J'")["value"].min())
    return [{"arm": name, "seed": seed, "n": k, "best_loss": best,
             "p_batch": r.get("p_value_sign_flip_one_sided", np.nan), "batch_ratio": r.get("rmse_ratio_estimate", np.nan),
             "batch_d": [float(x["d"]) for x in r.get("per_batch", [])]}]


def run_factorial(name: str, seed: int, root: str) -> list[dict]:
    sys.path.insert(0, os.path.join(ROOT, "code", "campaign"))
    import factorial
    kind, r = FACTORIAL_SIZING[name]
    lab = os.path.join(root, "labs", f"{name}_s{seed}", "lab")
    sim_lab.init_lab(lab, ("L1", "L2", "L3"), seed=seed)
    levels = ("L1", "L3", "RED-A", "RED-B") if kind == "effect" else ("L2", "L2", "RED-A", "RED-A")
    syn = factorial.design(*levels, replicates=r, role="reductant", seed=seed, gold_lot="LOT-HAuCl4-SIM")
    sim_lab.run_syntheses(lab, syn.assign(status="done"), np.random.default_rng(seed))
    a = factorial.analyze(lab)
    m = a["main_effects_restricted_randomization"]
    return [{"arm": name, "seed": seed, "n": r, "best_loss": float(np.exp(min(a["cell_means"].values()))),
             "p_imp": m["impurity"]["p_holm"], "p_go": m["GO_low_vs_high"]["p_holm"],     # decisão pré-registrada
             "p_imp_raw": m["impurity"]["p_two_sided"], "p_go_raw": m["GO_low_vs_high"]["p_two_sided"],
             "p_int": a["ols_hc3"]["interaction"]["p"], "eff_imp": a["effect_impurity"],
             "eff_go": a["effect_GO_low_vs_high"], "eff_int": a["interaction"]}]


def summarize_factorial(cv: pd.DataFrame, alpha: float = 0.05) -> dict:
    s = {"SIMULADO": True, "scenario": "factorial", "alpha": alpha, "rows": {}}
    for name, g in cv.groupby("arm"):
        kind, r = FACTORIAL_SIZING[name]
        row = {"kind": kind, "replicates": r, "syntheses": 4 * r, "campaigns": int(len(g))}
        for k in ("imp", "go", "int"):
            p = g[f"p_{k}"].to_numpy(float)
            row[f"rejection_{k}"] = float(np.mean(p < alpha))
            row[f"rejection_{k}_ci95"] = _wilson(int(np.sum(p < alpha)), len(p))
            row[f"median_effect_{k}"] = float(np.median(g[f"eff_{k}"]))
        s["rows"][name] = row
    return s


def summarize_batches(cv: pd.DataFrame, alpha: float = 0.05) -> dict:
    s = {"SIMULADO": True, "scenario": "batches", "alpha": alpha, "budget": SIZING_BUDGET, "rows": {}}
    for name, g in cv.groupby("arm"):
        kind, k = BATCH_SIZING[name]
        p = g["p_batch"].to_numpy(float)
        p = p[np.isfinite(p)]
        d = np.concatenate([np.asarray(x, float) for x in g["batch_d"]] or [np.array([])])
        s["rows"][name] = {"kind": kind, "batches": k, "campaigns": int(len(p)),
                           "rejection": float(np.mean(p < alpha)) if len(p) else float("nan"),
                           "rejection_ci95": _wilson(int(np.sum(p < alpha)), len(p)),
                           "median_rmse_ratio": float(np.nanmedian(g["batch_ratio"].to_numpy(float))),
                           "mean_batch_log_ratio": float(np.mean(d)) if len(d) else float("nan"),
                           "sd_batch_log_ratio": float(np.std(d, ddof=1)) if len(d) > 1 else float("nan")}
    return s


def _job(scenario: str, arm: str, seed: int, rounds: int, q: int, root: str, acq: str | None, resume: bool):
    path = os.path.join(root, "jobs", f"{arm.replace('+', '_')}_s{seed}.json")
    if resume and os.path.exists(path):
        if scenario == "prospective":
            return _augment_prospective(path, root)
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    import torch
    torch.set_num_threads(1)
    warnings.simplefilter("ignore")
    t0 = time.time()
    curve = (run_campaign(arm, seed, rounds, q, root, acq) if scenario == "main"
             else run_prospective(arm, seed, rounds, root, acq) if scenario == "prospective"
             else run_batches(arm, seed, root) if scenario == "batches"
             else run_factorial(arm, seed, root) if scenario == "factorial"
             else run_transfer(arm, seed, rounds, q, root, acq))
    res = {"arm": arm, "seed": seed, "seconds": round(time.time() - t0, 1), "curve": curve}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh)
    return res


def run_all(scenario: str, arms, seeds: int, rounds: int, q: int, out: str, acq=None, workers: int = 1,
            resume: bool = False) -> pd.DataFrame:
    root = os.path.join(out, scenario)
    jobs = [(scenario, a, s, rounds, q, root, acq, resume) for s in range(seeds) for a in arms]
    curves, t0 = [], time.time()
    if workers > 1:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        with ProcessPoolExecutor(workers) as ex:
            futs = [ex.submit(_job, *j) for j in jobs]
            for f in as_completed(futs):
                r = f.result()
                curves += r["curve"]
                print(f"semente {r['seed']} {r['arm']:22s} melhor perda final {r['curve'][-1]['best_loss']:8.3f} "
                      f"({r['seconds']:.0f} s; total {time.time() - t0:.0f} s)", flush=True)
    else:
        for j in jobs:
            r = _job(*j)
            curves += r["curve"]
            print(f"semente {r['seed']} {r['arm']:22s} melhor perda final {r['curve'][-1]['best_loss']:8.3f} "
                  f"({time.time() - t0:.0f} s)", flush=True)
    cv = pd.DataFrame(curves).sort_values(["arm", "seed", "n"]).reset_index(drop=True)
    os.makedirs(root, exist_ok=True)
    cv.to_csv(os.path.join(root, "curves.csv"), index=False)
    return cv


def _objective_points(lab: str) -> np.ndarray:
    """Pontos (log J, |d − alvo|) a MINIMIZAR, um por síntese — o espaço dos 2 objetivos da comparação principal."""
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    w = out.pivot_table(index="synthesis_id", columns="objective", values="value")
    tgt = float(pd.to_numeric(out.loc[out["objective"] == "size_mean_nm", "target_value"], errors="coerce").dropna().iloc[0])
    w = w.dropna(subset=["spectral_loss_J", "size_mean_nm"])
    return np.c_[np.log(w["spectral_loss_J"].to_numpy() + designer.default_eps()),
                 np.abs(w["size_mean_nm"].to_numpy() - tgt)]


def _pareto(F: np.ndarray) -> np.ndarray:
    keep = [i for i, f in enumerate(F) if not np.any(np.all(F <= f, axis=1) & np.any(F < f, axis=1))]
    return F[keep]


def pareto_metrics(root: str, arms, seeds: int) -> dict:
    """Hipervolume, IGD e spread (§4.15) de cada campanha, com ponto de referência e frente de referência COMUNS
    (a frente não dominada da união de todas as campanhas de todos os braços)."""
    pts = {}
    for a in arms:
        for sd in range(seeds):
            lab = os.path.join(root, "labs", f"{a.replace('+', '_')}_s{sd}", "lab")
            if os.path.exists(os.path.join(lab, "outcomes.csv")):
                pts[(a, sd)] = _objective_points(lab)
    if not pts:
        return {}
    allF = np.vstack(list(pts.values()))
    ref = allF.max(axis=0) + 0.05 * (allF.max(axis=0) - allF.min(axis=0))
    front = _pareto(allF)
    rows = [{"arm": a, "seed": sd, **stats.hv_igd_spread(_pareto(F), ref, front)} for (a, sd), F in pts.items()]
    df = pd.DataFrame(rows)
    return {"reference_point": ref.tolist(), "per_arm_median": df.groupby("arm")[["hypervolume", "igd", "spread"]]
            .median().to_dict(orient="index"), "per_campaign": rows}


def summarize_main(cv: pd.DataFrame, rounds: int, reference: str = "recipe") -> dict:
    final = cv[cv["round"] == rounds].rename(columns={"best_loss": "final_best_loss"})
    seeds = final["seed"].nunique()
    arms = sorted(final["arm"].unique())
    s = {"SIMULADO": True, "scenario": "main", "arms": arms, "seeds": seeds, "rounds": rounds,
         "median_final_best_loss": final.groupby("arm")["final_best_loss"].median().to_dict(),
         "comparison": stats.compare_arms(final) if seeds >= 2 else None, "relative_reduction_vs_reference": {},
         "geometric_reduction_vs_reference": {},
         "power_vs_reference": {}, "reference": reference}
    if reference in arms and seeds >= 2:
        wide = final.pivot_table(index="seed", columns="arm", values="final_best_loss")
        thr = float(wide[reference].median())
        s["time_to_criterion"] = stats.time_to_criterion(cv.rename(columns={"best_loss": "value"}), thr,
                                                         reference=reference)
        for arm in arms:
            if arm == reference:
                continue
            s["relative_reduction_vs_reference"][arm] = stats.paired_bootstrap_relative_reduction(
                wide[reference].to_numpy(), wide[arm].to_numpy())
            s["geometric_reduction_vs_reference"][arm] = stats.paired_bootstrap_geometric_reduction(
                wide[reference].to_numpy(), wide[arm].to_numpy())
            if seeds >= 8:   # com poucas campanhas-base a reamostragem é degenerada (poder ≈ 0 ou 1)
                s["power_vs_reference"][arm] = stats.power_by_resampling(
                    wide[reference].to_numpy(), wide[arm].to_numpy(), [5, 10, 20, 40], n_sim=500).to_dict("records")
    if seeds < 8:
        s["power_vs_reference"] = "não estimado: use --seeds >= 8 (a reamostragem de poucas campanhas é degenerada)"
    return s


def summarize_transfer(cv: pd.DataFrame, budget: int) -> dict:
    import hierarchical
    piv = {a: g.pivot_table(index="seed", columns="n", values="best_loss").to_numpy() for a, g in cv.groupby("arm")}
    s = {"SIMULADO": True, "scenario": "transfer", "new_batch": NEW_BATCH, "budget_new_batch": budget,
         "seeds": int(cv["seed"].nunique()),
         "median_final_best_loss": cv[cv["n"] == budget].groupby("arm")["best_loss"].median().to_dict(),
         "experiments_to_match_scratch": {}}
    if "scratch" in piv:
        for a, m in piv.items():
            if a != "scratch":
                s["experiments_to_match_scratch"][a] = hierarchical.experiments_to_match(m, piv["scratch"], budget)
    return s


def summarize_prospective(cv: pd.DataFrame, rounds: int, alpha: float = 0.05, threshold: float = 0.20) -> dict:
    """Poder (fração de campanhas com p < α), erro tipo I (cenário null), distribuição do efeito e cobertura."""
    last = cv.sort_values("n").groupby(["arm", "seed"]).tail(1)
    s = {"SIMULADO": True, "scenario": "prospective", "rounds": rounds, "alpha": alpha, "pairs": {}}
    for pair, g in last.groupby("arm"):
        pv = g["p_sign_flip"].to_numpy(float)
        hl = g["hl"].to_numpy(float)
        fin = g["best_loss"].to_numpy(float) / g["best_ref"].to_numpy(float)
        def rate(col):
            v = g[col].to_numpy(float) if col in g else np.array([])
            v = v[np.isfinite(v)]
            return (float(np.mean(v < alpha)) if len(v) else float("nan"), _wilson(int(np.sum(v < alpha)), len(v)))
        r_pred, r_conf = rate("p_predictive"), rate("p_confirm_opt")
        rr = g["rmse_ratio"].to_numpy(float) if "rmse_ratio" in g else np.array([np.nan])
        s["pairs"][pair] = {
            "primary_predictive_rejection": r_pred[0], "primary_predictive_rejection_ci95": r_pred[1],
            "median_rmse_ratio": float(np.nanmedian(rr)), "fraction_context_predicts_better": float(np.nanmean(rr < 1)),
            "secondary_confirmation_rejection": r_conf[0], "secondary_confirmation_rejection_ci95": r_conf[1],
            "median_confirmation_reduction": float(1 - np.exp(np.nanmedian(g["confirm_hl"]))) if "confirm_hl" in g
            else float("nan"),
            "campaigns": int(len(g)), "rejection_rate": float(np.mean(pv < alpha)),
            "rejection_rate_ci95": _wilson(int(np.sum(pv < alpha)), len(pv)),
            "median_relative_reduction_HL": float(1 - np.exp(np.median(hl))),
            "fraction_HL_reduction_above_threshold": float(np.mean(1 - np.exp(hl) >= threshold)),
            "fraction_final_best_better": float(np.mean(fin < 1)),
            "median_final_geometric_reduction": float(1 - np.exp(np.median(np.log(fin))))}
        if "p_batch" in g:
            r_b = rate("p_batch")
            pool = np.concatenate([np.asarray(x, float) for x in g["batch_d"] if isinstance(x, (list, np.ndarray))]
                                  or [np.array([])])
            s["pairs"][pair].update({
                "primary_batch_rejection": r_b[0], "primary_batch_rejection_ci95": r_b[1],
                "median_batch_rmse_ratio": float(np.nanmedian(g["batch_ratio"].to_numpy(float))),
                "batches_per_campaign": int(np.median([len(x) for x in g["batch_d"] if isinstance(x, list)] or [0])),
                "batch_effect_mean_log_ratio": float(np.mean(pool)) if len(pool) else float("nan"),
                "batch_effect_sd": float(np.std(pool, ddof=1)) if len(pool) > 1 else float("nan")})
    return s


def _wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    mid, half = (p + z * z / (2 * n)) / den, z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(max(0.0, mid - half)), float(min(1.0, mid + half)))


def report(out: str) -> str:
    """Markdown com os resumos (cenários main/transfer e MISO, se existirem)."""
    lines = ["# Simulações registradas (SIMULADO)", "",
             "> **SIMULADO** — gerado por `code/benchmarking/campaign_sim.py report` a partir do laboratório simulado",
             "> (`code/benchmarking/simulator.py`). Os números dimensionam e testam o protocolo; não são medidas nem",
             "> previsões do ganho real. Regenerar: ver os comandos em cada seção.", ""]
    p = os.path.join(out, "main", "summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        lines += [f"## Cenário principal (L1–L3): {s['seeds']} sementes × {s['rounds']} rodadas", "",
                  "`python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --q 2 --workers 4`", "",
                  "| braço | mediana da melhor perda final | redução geométrica vs " + s["reference"] + " (IC 95 %) | "
                  "campanhas melhores | experimentos até o critério (RMST) | atingiram | log-rank p |",
                  "|---|---|---|---|---|---|---|"]
        ttc = s.get("time_to_criterion", {}).get("arms", {})
        for arm in sorted(s["median_final_best_loss"], key=s["median_final_best_loss"].get):
            rr = s.get("geometric_reduction_vs_reference", {}).get(arm)
            red = (f"{100 * rr['geometric_reduction']:.0f} % ({100 * rr['ci95'][0]:.0f}; {100 * rr['ci95'][1]:.0f})"
                   if rr else "—")
            better = f"{100 * rr['fraction_better']:.0f} %" if rr else "—"
            t = ttc.get(arm, {})
            fmt = lambda k, f: format(t[k], f) if k in t and np.isfinite(t[k]) else "—"     # noqa: E731
            pct = f"{100 * t['fraction_reached']:.0f} %" if "fraction_reached" in t else "—"
            lines.append(f"| {arm} | {s['median_final_best_loss'][arm]:.3f} | {red} | {better} | {fmt('rmst', '.1f')} | "
                         f"{pct} | {fmt('logrank_p', '.3g')} |")
        if s.get("time_to_criterion"):
            lines += ["", f"Critério: melhor perda balanceada ≤ {s['time_to_criterion']['threshold']:.3f} (mediana final "
                      f"do braço {s['reference']}). Tempo = nº total de sínteses (inclui as 12 iniciais, iguais em "
                      f"todos os braços); censura no orçamento ({s['time_to_criterion']['budget']:g} sínteses)."]
        pm = (s.get("pareto") or {}).get("per_arm_median")
        if pm:
            lines += ["", "Frente de Pareto (log J × |d − 20 nm|; mediana entre campanhas; referência e frente comuns a "
                      "todos os braços):", "", "| braço | hipervolume ↑ | IGD ↓ | spread ↓ |", "|---|---|---|---|"]
            for arm in sorted(pm, key=lambda k: -pm[k]["hypervolume"]):
                lines.append(f"| {arm} | {pm[arm]['hypervolume']:.2f} | {pm[arm]['igd']:.3f} | {pm[arm]['spread']:.2f} |")
        if isinstance(s["power_vs_reference"], dict) and s["power_vs_reference"]:
            lines += ["", "Poder (Wilcoxon unilateral, α = 0,05) por nº de campanhas:", "",
                      "| braço | n=5 | n=10 | n=20 | n=40 |", "|---|---|---|---|---|"]
            for arm, rows in s["power_vs_reference"].items():
                lines.append(f"| {arm} | " + " | ".join(f"{r['power']:.2f}" for r in rows) + " |")
        fp = (s.get("comparison") or {}).get("friedman_p")
        if fp is not None and np.isfinite(fp):
            lines += ["", f"Friedman p = {fp:.3g} (todos os braços); Wilcoxon pareados com Holm em summary.json."]
        lines.append("")
    p = os.path.join(out, "prospective", "summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        lines += [f"## Desenho real pré-registrado: 8 + 12 compartilhadas, {s['rounds']} rodadas pareadas (1 síntese de "
                  "cada braço por rodada, mesmo lote e dia)", "",
                  "`python code/benchmarking/campaign_sim.py --scenario prospective --seeds 40 --workers 4`", "",
                  "Cada linha é um par de braços simulado muitas vezes com o orçamento real; a análise é a de "
                  "`code/campaign/analysis.py` (randomização por troca de sinais, unilateral, α = "
                  f"{s['alpha']}), incluindo a confirmação: 8 pares nos lotes reservados L4–L6 com os braços "
                  "congelados e as previsões dos modelos congelados gravadas antes de sintetizar.",
                  "", "| par | campanhas | **primário**: rejeição — valor preditivo, unidade = lote (IC 95 %) | "
                  "razão de RMSE (HL, mediana) | descritivo: rejeição por síntese | secundário: rejeição — otimização "
                  "nos pares de confirmação | exploratório: rejeição — rodadas adaptativas | P(melhor perda final do "
                  "tratamento < referência) |",
                  "|---|---|---|---|---|---|---|---|"]

        def pct(v, ci=None):
            if v is None or not np.isfinite(v):
                return "—"
            return f"{100 * v:.0f} %" + (f" ({100 * ci[0]:.0f}–{100 * ci[1]:.0f})" if ci else "")
        for pair, v in s["pairs"].items():
            lines.append(f"| {pair} | {v['campaigns']} | "
                         f"{pct(v.get('primary_batch_rejection'), v.get('primary_batch_rejection_ci95'))} | "
                         f"{v.get('median_batch_rmse_ratio', float('nan')):.2f} | "
                         f"{pct(v.get('primary_predictive_rejection'), v.get('primary_predictive_rejection_ci95'))} | "
                         f"{pct(v.get('secondary_confirmation_rejection'), v.get('secondary_confirmation_rejection_ci95'))} | "
                         f"{pct(v['rejection_rate'], v['rejection_rate_ci95'])} | "
                         f"{pct(v['fraction_final_best_better'])} |")
        lines += ["", "Rejeição no par **contextual** = poder; nos pares **placebo** (contexto registrado sem "
                  "informação: descritores trocados entre lotes e lote de redutor registrado sorteado) "
                  "e **null** (braços idênticos) = erro tipo I. O valor preditivo não existe no null (mesma "
                  "representação → previsões idênticas). O primário usa o **lote** como unidade: os 3 lotes de "
                  "desenvolvimento por leave-one-batch-out e os 3 reservados pelas previsões congeladas (troca de "
                  "sinais exata, p mínimo 1/64); a versão por síntese trata sínteses do mesmo lote como independentes "
                  "e é anticonservadora (ver o placebo), por isso só descritiva."]
        c = s["pairs"].get("contextual", {})
        if "batch_effect_sd" in c:
            lines += ["", f"No cenário contextual, d_b = ln(RMSE_contexto/RMSE_receita) tem média "
                      f"{c['batch_effect_mean_log_ratio']:+.3f} (razão {np.exp(c['batch_effect_mean_log_ratio']):.3f}) e "
                      f"dp entre lotes {c['batch_effect_sd']:.3f}: o ganho preditivo do contexto é pequeno diante da "
                      "variação entre lotes. Mais lotes com o mesmo orçamento: seção seguinte (simulação direta com K "
                      "lotes — reamostrar os d_b daqui ignoraria a correlação dentro da campanha e o aprendizado "
                      "que mais lotes trazem)."]
        lines.append("")
    p = os.path.join(out, "batches", "summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        rows = s["rows"]
        ks = sorted({v["batches"] for v in rows.values()})
        get = lambda kind, k: next((v for v in rows.values() if v["kind"] == kind and v["batches"] == k), None)  # noqa: E731

        def cell(v):
            if not v or not np.isfinite(v["rejection"]):
                return "—"
            lo, hi = v["rejection_ci95"]
            return f"{100 * v['rejection']:.0f} % ({100 * lo:.0f}–{100 * hi:.0f})"
        lines += [f"## Mais lotes de GO com o mesmo orçamento ({s['budget']} sínteses repartidas entre K lotes)",
                  "", "`python code/benchmarking/campaign_sim.py --scenario batches --seeds 40 --workers 4`", "",
                  "Receitas LHS em cada lote (metade com cada lote de redutor); desfecho primário por lote "
                  "(leave-one-batch-out do modelo agrupado, recipe × go+impurities, troca de sinais exata, "
                  f"α = {s['alpha']}). Lotes extras do simulador com C/O sorteado na faixa de L1–L6; todo lote é "
                  "avaliado com os outros K − 1 no treino.", "",
                  "| lotes (K) | sínteses por lote | poder (contextual) | razão de RMSE mediana | erro tipo I (placebo) |",
                  "|---|---|---|---|---|"]
        for k in ks:
            c, pl = get("contextual", k), get("placebo", k)
            lines.append(f"| {k} | {s['budget'] / k:.1f} | {cell(c)} | "
                         f"{c['median_rmse_ratio']:.2f} | {cell(pl)} |" if c else f"| {k} | — | — | — | {cell(pl)} |")
        tot = {kind: [v for v in rows.values() if v["kind"] == kind] for kind in ("contextual", "placebo")}
        if all(tot.values()):
            rej = {kind: sum(v["rejection"] * v["campaigns"] for v in vs) / sum(v["campaigns"] for v in vs)
                   for kind, vs in tot.items()}
            lines += ["", f"Somando os K: rejeição {100 * rej['contextual']:.0f} % com efeito real × "
                      f"{100 * rej['placebo']:.0f} % sob o placebo. Se as duas forem parecidas, repartir o orçamento "
                      "em mais lotes não dá poder ao teste (as dobras do leave-one-batch-out compartilham o treino)."]
        lines.append("")
    p = os.path.join(out, "factorial", "summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        lines += ["## Fatorial 2×2 (§4.9): poder por nº de réplicas (blocos completos)", "",
                  "`python code/benchmarking/campaign_sim.py --scenario factorial --seeds 100 --workers 4`", "",
                  "Receita fixa (centro do espaço); GO C/O 2,2 × 1,5 (L1 × L3) e redutor com 2 × 45 ppm de iodeto. "
                  "Efeitos principais por randomização restrita exata com Holm entre os dois (`factorial.py`; com 3 "
                  "réplicas o menor p possível, 2/64, dobra para 0,0625 e nada é rejeitado), interação por OLS com bloco "
                  f"(HC3); α = {s['alpha']}. \"null\": o mesmo lote nos dois níveis (erro tipo I).", "",
                  "| cenário | réplicas | sínteses | rejeição — impureza | rejeição — GO | rejeição — interação | "
                  "efeito mediano GO (log J) | efeito mediano impureza (log J) |", "|---|---|---|---|---|---|---|---|"]

        def pc(v, ci):
            return f"{100 * v:.0f} % ({100 * ci[0]:.0f}–{100 * ci[1]:.0f})"
        for name in sorted(s["rows"], key=lambda n: (s["rows"][n]["kind"], s["rows"][n]["replicates"])):
            v = s["rows"][name]
            lines.append(f"| {v['kind']} | {v['replicates']} | {v['syntheses']} | "
                         f"{pc(v['rejection_imp'], v['rejection_imp_ci95'])} | {pc(v['rejection_go'], v['rejection_go_ci95'])} | "
                         f"{pc(v['rejection_int'], v['rejection_int_ci95'])} | {v['median_effect_go']:+.2f} | "
                         f"{v['median_effect_imp']:+.2f} |")
        lines.append("")
    p = os.path.join(out, "transfer", "summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        lines += [f"## Transferência para o lote reservado {s['new_batch']}: {s['seeds']} sementes, "
                  f"{s['budget_new_batch']} sínteses no lote novo", "",
                  "`python code/benchmarking/campaign_sim.py --scenario transfer --seeds 10 --workers 4`", "",
                  "| braço | mediana da melhor perda final | experimentos até o desempenho final do do-zero (RMST) | "
                  "atingiram | economia relativa |", "|---|---|---|---|---|"]
        for arm, m in s["median_final_best_loss"].items():
            e = s["experiments_to_match_scratch"].get(arm)
            if e:
                lines.append(f"| {arm} | {m:.3f} | {e['transfer']['rmst']:.1f} (do-zero: {e['scratch']['rmst']:.1f}) | "
                             f"{100 * e['transfer']['fraction_reached']:.0f} % | {100 * e['relative_saving']:.0f} % |")
            else:
                lines.append(f"| {arm} | {m:.3f} | — | — | — |")
        lines.append("")
    p = os.path.join(out, "..", "miso", "miso_benchmark.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        lines += [f"## MISO (UV-Vis/DLS/TEM, alvo TEM): {s['seeds']} sementes, orçamento {s['budget']:g}", "",
                  "`python code/miso/miso.py benchmark --seeds 8 --workers 4`", "",
                  "| modelo | consultas médias (TEM / UV-Vis / DLS) | recomendação pelo modelo: arrependimento final "
                  "média (mediana) | atingiram | custo até o critério (RMST) | recomendação CONFIRMADA por TEM: "
                  "arrependimento final média (mediana) | atingiram | custo até o critério (RMST) |",
                  "|---|---|---|---|---|---|---|---|"]
        for k, v in s["summary"].items():
            qm = v.get("queries_mean", {})
            qs = " / ".join(f"{qm.get(n, 0):.1f}" for n in ("TEM", "UV-Vis", "DLS"))
            row = f"| {k} | {qs} | {v['final_regret_mean']:.4f} ({v['final_regret_median']:.4f}) | " \
                  f"{100 * v['hit_rate']:.0f} % | {v['cost_to_criterion_rmst']['rmst']:.1f} |"
            if "final_regret_confirmed_mean" in v:
                row += (f" {v['final_regret_confirmed_mean']:.4f} ({v['final_regret_confirmed_median']:.4f}) | "
                        f"{100 * v['hit_rate_confirmed']:.0f} % | {v['cost_to_criterion_confirmed_rmst']['rmst']:.1f} |")
            else:
                row += " — | — | — |"
            lines.append(row)
        lines += ["", f"Critério: arrependimento simples ≤ {s['criterion_regret']} (objetivo −[ln(d/20)]²). "
                  "Recomendação pelo modelo = argmax da média a posteriori da TEM no conjunto de candidatos; "
                  "confirmada = o melhor (pela média a posteriori) entre os pontos já medidos por TEM.", ""]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(report(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "outputs", "campaign_sim")))
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=["main", "transfer", "prospective", "batches", "factorial"], default="main")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--rounds", type=int, help="main: rodadas adaptativas (padrão 12 = 24 sínteses com q=2); "
                                                "transfer: sínteses no lote novo (padrão 16)")
    ap.add_argument("--q", type=int, default=2)
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--reference", default="recipe")
    ap.add_argument("--acq", choices=["qlognehvi", "qnehvi"], help="padrão: o do pré-registro")
    ap.add_argument("--workers", type=int, default=1, help="processos em paralelo (1 thread de torch cada)")
    ap.add_argument("--resume", action="store_true", help="reaproveita jobs/*.json já concluídos")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "campaign_sim"))
    a = ap.parse_args()
    table = {"main": ARMS, "transfer": TRANSFER_ARMS, "prospective": PROSPECTIVE, "batches": BATCH_SIZING,
             "factorial": FACTORIAL_SIZING}[a.scenario]
    arms = a.arms or list(table)
    bad = [x for x in arms if x not in table]
    if bad:
        ap.error(f"braços desconhecidos {bad}; disponíveis: {list(table)}")
    rounds = a.rounds or {"main": 12, "transfer": 16, "prospective": 12, "batches": 0, "factorial": 0}[a.scenario]
    cv = run_all(a.scenario, arms, a.seeds, rounds, a.q, a.out, a.acq, a.workers, a.resume)
    s = (summarize_main(cv, rounds, a.reference) if a.scenario == "main" else
         summarize_prospective(cv, rounds) if a.scenario == "prospective" else
         summarize_batches(cv) if a.scenario == "batches" else
         summarize_factorial(cv) if a.scenario == "factorial" else summarize_transfer(cv, rounds))
    if a.scenario == "main":
        s["pareto"] = pareto_metrics(os.path.join(a.out, "main"), arms, a.seeds)
    s.update({"q": a.q, "acq": a.acq or designer.default_acq(), "prereg_sha256": _prereg_sha()})
    root = os.path.join(a.out, a.scenario)
    if a.scenario == "main":
        cv[cv["round"] == rounds].to_csv(os.path.join(root, "final.csv"), index=False)
    with open(os.path.join(root, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1, default=float)
    print(json.dumps(s, indent=1, default=float)[:3000])
    print(f"-> {os.path.relpath(root, ROOT)}/ (curves.csv, summary.json) — resultados do SIMULADOR")


def _prereg_sha() -> str:
    try:
        import prereg
        return prereg.sha256(prereg.load())
    except Exception:          # noqa: BLE001
        return ""


if __name__ == "__main__":
    main()
