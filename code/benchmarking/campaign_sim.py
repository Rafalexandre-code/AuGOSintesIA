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
Comparação: Friedman, Wilcoxon pareado + Holm, redução relativa com IC por bootstrap, poder por reamostragem e
EXPERIMENTOS ATÉ O CRITÉRIO (critério = mediana final do braço de referência), com censura no orçamento:
média restrita (RMST, Kaplan–Meier) e teste log-rank contra a referência.

Cenário `transfer` (lote reservado L4, §4.7): "do zero" (receita, só dados do L4: 4 receitas LHS + rodadas) contra
"transfer-go" e "transfer-hierarchical" (24 sínteses de L1–L3 como histórico, nenhuma no L4 antes da 1ª rodada).
Métrica da proposta: nº de experimentos NO L4 até igualar o desempenho final do do-zero (com censura) e economia
relativa (code/transfer_learning/hierarchical.py → experiments_to_match).

Uso:
    python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --q 2 --workers 4                # cenário main
    python code/benchmarking/campaign_sim.py --scenario transfer --seeds 10 --workers 4
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
        "gp-ei": ("go", "gp-ei", {}), "rf-qnehvi": ("go", "rf-qnehvi", {})}
ARMS.update({f"novelty-w{w:g}": ("go", "novelty", {"w": w}) for w in _novelty_weights()})
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


def _propose(arm_spec, lab: str, space: dict, target: str, lots: dict, q: int, seed: int, acq: str | None):
    """Uma rodada de qualquer braço -> DataFrame de receitas (colunas do espaço)."""
    import strategies
    rep, strat, kw = arm_spec
    if strat == "random":
        from scipy.stats import qmc
        lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
        return pd.DataFrame(qmc.scale(qmc.Sobol(len(space), seed=seed).random(q), lo, hi), columns=list(space))
    camp = designer.load_campaign(lab, space, rep, designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints())
    fixed = designer.fixed_context(lab, camp, target, lots)
    if strat == "gp-qnehvi":
        return designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed)
    if strat == "novelty":
        return designer.propose(camp, space, q=q, fixed=fixed, acq=acq, seed=seed, novelty_w=kw["w"])
    if strat == "gp-ei":
        return strategies.propose_gp_ei(camp, space, q, fixed, seed)
    if strat == "rf-qnehvi":
        return strategies.propose_rf_qnehvi(camp, space, q, fixed, seed)
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


def _job(scenario: str, arm: str, seed: int, rounds: int, q: int, root: str, acq: str | None, resume: bool):
    path = os.path.join(root, "jobs", f"{arm.replace('+', '_')}_s{seed}.json")
    if resume and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    import torch
    torch.set_num_threads(1)
    warnings.simplefilter("ignore")
    t0 = time.time()
    curve = (run_campaign(arm, seed, rounds, q, root, acq) if scenario == "main"
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
        if isinstance(s["power_vs_reference"], dict) and s["power_vs_reference"]:
            lines += ["", "Poder (Wilcoxon unilateral, α = 0,05) por nº de campanhas:", "",
                      "| braço | n=5 | n=10 | n=20 | n=40 |", "|---|---|---|---|---|"]
            for arm, rows in s["power_vs_reference"].items():
                lines.append(f"| {arm} | " + " | ".join(f"{r['power']:.2f}" for r in rows) + " |")
        fp = (s.get("comparison") or {}).get("friedman_p")
        if fp is not None and np.isfinite(fp):
            lines += ["", f"Friedman p = {fp:.3g} (todos os braços); Wilcoxon pareados com Holm em summary.json."]
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
                  "`python code/miso/miso.py benchmark --seeds 8`", "",
                  "| modelo | arrependimento final (média) | mediana | atingiram o critério | custo até o critério (RMST) |",
                  "|---|---|---|---|---|"]
        for k, v in s["summary"].items():
            lines.append(f"| {k} | {v['final_regret_mean']:.4f} | {v['final_regret_median']:.4f} | "
                         f"{100 * v['hit_rate']:.0f} % | {v['cost_to_criterion_rmst']['rmst']:.1f} |")
        lines += ["", f"Critério: arrependimento simples ≤ {s['criterion_regret']} (objetivo −[ln(d/20)]²).", ""]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(report(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "outputs", "campaign_sim")))
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=["main", "transfer"], default="main")
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
    table = ARMS if a.scenario == "main" else TRANSFER_ARMS
    arms = a.arms or list(table)
    bad = [x for x in arms if x not in table]
    if bad:
        ap.error(f"braços desconhecidos {bad}; disponíveis: {list(table)}")
    rounds = a.rounds or (12 if a.scenario == "main" else 16)
    cv = run_all(a.scenario, arms, a.seeds, rounds, a.q, a.out, a.acq, a.workers, a.resume)
    s = summarize_main(cv, rounds, a.reference) if a.scenario == "main" else summarize_transfer(cv, rounds)
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
