#!/usr/bin/env python3
"""Gerador do plano experimental da campanha (§4.9, §4.11, §4.17), a partir do plano pré-registrado.

Produz as 60 sínteses do orçamento, mais os controles, com blocos (dia/operador) e ordem aleatorizada:
  * PILOTO (8): a receita de referência (centro do espaço) em preparações independentes — 4 no L1 (repetibilidade
    da síntese, base do teste de heteroscedasticidade e da regra de ε) e 2 no L2 e no L3 (primeira estimativa do
    efeito de lote). Cada preparação é lida em duplicata no UV-Vis (repetição de medida ≠ síntese nova).
  * INICIALIZAÇÃO (12): 4 receitas de preenchimento do domínio (hipercubo latino maximin: a melhor de 2000 sorteadas
    pela menor distância entre pontos) × lotes L1–L3.
  * ADAPTATIVAS (24): 12 rodadas × q = 2, lote-alvo em rodízio; as receitas vêm do AuNP Designer na hora.
  * CONFIRMAÇÃO (16): lotes reservados L4–L6, recomendadas por um modelo CONGELADO, treinado só com o
    desenvolvimento (`plan.py confirm`); os resultados da confirmação nunca voltam para o treino.
  * CONTROLES (fora das 60): 1 controle sem GO a cada `no_GO_every_n_days` dias; 1 branco de GO tratado (mesmo
    redutor da referência, sem Au) por lote, no 1º dia em que o lote aparece.
Blocos: cada dia tem capacidade `syntheses_per_day`; na inicialização e na confirmação os lotes são distribuídos de
forma balanceada entre os dias (lote não se confunde com dia). Dentro do dia, ordem aleatória (semente registrada).
Volumes de pipetagem calculados a partir dos estoques do pré-registro, com alertas de volume mínimo/excesso.

Saídas (padrão outputs/plano/): plano_experimental.csv (todas as vagas), aunp_syntheses_planejadas.csv (linhas no
formato do modelo de dados, status=planned), fichas/dia_XX.md (folhas de bancada) e plano_manifest.json.

Uso:
    python code/campaign/plan.py generate [--out outputs/plano] [--seed 20261001]
    python code/campaign/plan.py confirm datasets/lab [--representation go]   # receitas dos lotes reservados
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import prereg  # noqa: E402

CONFIRMATION_CAMPAIGN = "CONFIRMATION"


def _syn_columns() -> list[str]:
    with open(os.path.join(ROOT, "datasets", "data-model", "templates", "aunp_syntheses.csv"), encoding="utf-8") as fh:
        return next(csv.reader(fh))


def reference_recipe(space: dict) -> dict:
    return {k: round((lo + hi) / 2, 4) for k, (lo, hi) in space.items()}


def maximin_lhs(space: dict, n: int, seed: int, tries: int = 2000) -> tuple[pd.DataFrame, float]:
    """Hipercubo latino maximin: entre `tries` LHS sorteados, o de maior menor-distância (escala unitária)."""
    from scipy.spatial.distance import pdist
    from scipy.stats import qmc
    rng = np.random.default_rng(seed)
    best, best_d = None, -1.0
    for _ in range(tries):
        u = qmc.LatinHypercube(len(space), seed=rng).random(n)
        d = pdist(u).min()
        if d > best_d:
            best, best_d = u, d
    lo = np.array([v[0] for v in space.values()])
    hi = np.array([v[1] for v in space.values()])
    return pd.DataFrame(np.round(lo + best * (hi - lo), 4), columns=list(space)), float(best_d)


def volumes(recipe: dict, stocks: dict) -> dict:
    """µL de cada estoque para o volume total; alerta se < volume mínimo pipetável ou se excede o total."""
    vt = float(stocks["total_volume_mL"]) * 1000.0
    out, warn = {}, []
    if "HAuCl4_mM" in recipe:
        out["V_HAuCl4_uL"] = recipe["HAuCl4_mM"] * vt / float(stocks["HAuCl4_mM"])
    red = recipe.get("reductant_mM")
    if red is None and "reductant_to_Au_ratio" in recipe and "HAuCl4_mM" in recipe:
        red = recipe["reductant_to_Au_ratio"] * recipe["HAuCl4_mM"]
    if red:
        out["V_reductant_uL"] = red * vt / float(stocks["reductant_mM"])
    if recipe.get("GO_mg_mL", 0) > 0:
        out["V_GO_uL"] = recipe["GO_mg_mL"] * vt / float(stocks["GO_mg_mL"])
    water = vt - sum(out.values())
    out = {k: round(v, 1) for k, v in out.items()}
    out["V_water_uL"] = round(water, 1)
    for k, v in out.items():
        if k != "V_water_uL" and 0 < v < float(stocks["min_pipette_uL"]):
            warn.append(f"{k} = {v} µL < mínimo pipetável: dilua o estoque")
    if water < 0:
        warn.append("soma dos estoques excede o volume total: use estoques mais concentrados")
    out["volume_warnings"] = "; ".join(warn)
    return out


def _balanced_days(cells: list[tuple], cap: int, rng: np.random.Generator, tries: int = 400) -> list[list[tuple]]:
    """Distribui células (receita, lote) em dias de capacidade `cap` balanceando lotes e receitas entre os dias."""
    n_days = int(np.ceil(len(cells) / cap))
    best, best_score = None, np.inf
    for _ in range(tries):
        perm = [cells[i] for i in rng.permutation(len(cells))]
        days = [perm[i::n_days] for i in range(n_days)]
        score = 0.0
        for key in (0, 1):                       # desbalanço de receitas e de lotes entre os dias
            labels = sorted({c[key] for c in cells}, key=str)
            counts = np.array([[sum(1 for c in d if c[key] == lab) for lab in labels] for d in days])
            score += counts.std(axis=0).sum()
        if score < best_score:
            best, best_score = days, score
    return best


def generate(seed: int | None = None, cfg: dict | None = None) -> dict:
    cfg = cfg or prereg.load()
    seed = int(cfg.get("random_seed", 0) if seed is None else seed)
    rng = np.random.default_rng(seed)
    space = prereg.search_space(cfg)
    bud, cap = cfg["budget"], int(cfg["budget"]["syntheses_per_day"])
    dev, reserved = list(cfg["batches"]["development"]), list(cfg["batches"]["reserved"])
    ref = reference_recipe(space)
    slots = []

    def add(stage, day, batch, recipe=None, rnd="", control="none", note="", arm=""):
        red = ""
        if recipe:
            red = recipe.get("reductant_mM", round(recipe["reductant_to_Au_ratio"] * recipe["HAuCl4_mM"], 4)
                             if "reductant_to_Au_ratio" in recipe and "HAuCl4_mM" in recipe else "")
        slots.append({"stage": stage, "day": day, "round": rnd, "arm": arm, "go_batch_id": batch, "is_control": control,
                      **({k: recipe.get(k, "") for k in space} if recipe else {k: "" for k in space}),
                      "reductant_mM": red, "notes": note})

    # piloto: 4 no L1 + o restante dividido entre os outros lotes de desenvolvimento
    n_p = int(bud["pilot"])
    n_l1 = min(n_p, max(1, n_p // 2))
    pilot_batches = [dev[0]] * n_l1 + [dev[1 + i % (len(dev) - 1)] for i in range(n_p - n_l1)] if len(dev) > 1 \
        else [dev[0]] * n_p
    day = 0
    for chunk in [pilot_batches[i:i + cap] for i in range(0, len(pilot_batches), cap)]:
        day += 1
        for b in chunk:
            add("pilot", day, b, ref, note="receita de referência; preparação independente; UV-Vis em duplicata")
    # inicialização: receitas maximin × lotes de desenvolvimento, dias balanceados
    n_rec = int(bud["initialization"]) // len(dev)
    recipes, dmin = maximin_lhs(space, n_rec, seed)
    cells = [(r, b) for r in range(n_rec) for b in dev]
    for d in _balanced_days(cells, cap, rng):
        day += 1
        for r, b in d:
            add("initialization", day, b, recipes.iloc[r].to_dict(), note=f"receita de preenchimento R{r + 1}")
    # adaptativas: rodadas PAREADAS (uma síntese de cada braço prospectivo, mesmo lote e mesmo dia; a ordem dentro do
    # dia é sorteada abaixo) — a comparação entre braços fica bloqueada por lote e dia e o teste de randomização
    # (code/campaign/analysis.py) vale pelo próprio desenho. Uma rodada por dia: cada braço precisa do resultado anterior.
    arms_ = prereg.arms(cfg)["prospective"]
    n_rounds = int(bud["adaptive"]) // len(arms_)
    for r in range(1, n_rounds + 1):
        day += 1
        for arm in arms_:
            add("adaptive", day, dev[(r - 1) % len(dev)], rnd=r, arm=arm,
                note=f"receita = designer.py propose --arm {arm} --batch {dev[(r - 1) % len(dev)]} --q 1")
    # confirmação: lotes reservados, dias balanceados
    n_c = int(bud["confirmation"])
    conf_batches = [reserved[i % len(reserved)] for i in range(n_c)]
    for d in _balanced_days([(i, b) for i, b in enumerate(conf_batches)], cap, rng):
        day += 1
        for _, b in d:
            add("confirmation", day, b, note="receita = modelo congelado (plan.py confirm)")
    # controles
    plan = pd.DataFrame(slots)
    ctl = cfg.get("controls", {}) or {}
    every = int(ctl.get("no_GO_every_n_days", 0))
    if every > 0:
        for d in sorted(plan["day"].unique()):
            if (int(d) - 1) % every == 0:
                add("control", int(d), "", {**ref, "GO_mg_mL": 0.0}, control="no_GO", note="controle sem GO (§4.17)")
    first_day = plan[plan["go_batch_id"] != ""].groupby("go_batch_id")["day"].min()
    red_ref = round(ref["reductant_to_Au_ratio"] * ref["HAuCl4_mM"], 4) if "reductant_to_Au_ratio" in ref else 0.0
    for b, d in first_day.items():
        for _ in range(int(ctl.get("GO_blank_per_batch", 0))):
            add("control", int(d), b, {**ref, "HAuCl4_mM": 0.0, "reductant_mM": red_ref}, control="GO_blank",
                note="branco de GO tratado: mesmo redutor, sem Au (fundo óptico, §4.17)")
    plan = pd.DataFrame(slots)
    plan["tem"] = _tem_subset(plan, cfg.get("tem_subset") or {}, rng)
    # ordem aleatória dentro do dia e identificadores
    plan["run_order"] = 0
    for d, idx in plan.groupby("day").groups.items():
        plan.loc[idx, "run_order"] = rng.permutation(len(idx)) + 1
    plan = plan.sort_values(["day", "run_order"]).reset_index(drop=True)
    plan.insert(0, "slot_id", [f"D{int(d):02d}-{int(o):02d}" for d, o in zip(plan["day"], plan["run_order"])])
    plan["block"] = [f"DAY{int(d):02d}" for d in plan["day"]]
    vols = [volumes({**{k: float(r[k]) for k in space if r[k] != ""},
                     **({"reductant_mM": float(r["reductant_mM"])} if r["reductant_mM"] != "" else {})},
                    cfg["stock_solutions"]) if r[list(space)[0]] != "" else {} for _, r in plan.iterrows()]
    plan = pd.concat([plan, pd.DataFrame(vols)], axis=1)
    counted = plan[plan["stage"] != "control"]
    diag = {"total_syntheses": int(len(counted)), "controls": int((plan["stage"] == "control").sum()),
            "days": int(plan["day"].max()), "per_stage": counted["stage"].value_counts().to_dict(),
            "init_maximin_distance": dmin,
            "batch_day_balance": counted[counted["stage"] == "initialization"].groupby(["day", "go_batch_id"]).size()
            .unstack(fill_value=0).to_dict(orient="index"),
            "adaptive_per_arm": counted[counted["stage"] == "adaptive"]["arm"].value_counts().to_dict(),
            "tem_per_stage": counted[counted["tem"] == "sim"]["stage"].value_counts().to_dict(),
            "adaptive_rounds": int(n_rounds),
            "prereg_sha256": prereg.sha256(cfg), "prereg_state": prereg.check()["state"], "seed": seed}
    expected = sum(int(bud[s]) for s in prereg.STAGES)
    if diag["total_syntheses"] != expected:
        raise prereg.PreregError(f"plano com {diag['total_syntheses']} sínteses; orçamento = {expected}")
    return {"plan": plan, "diagnostics": diag, "space": space}


def _tem_subset(plan: pd.DataFrame, spec: dict, rng: np.random.Generator) -> list[str]:
    """Marca as sínteses que vão para TEM (§4.12): espalhadas por etapa, receita, lote e rodada, não escolhidas pelo
    resultado (a escolha é feita no plano, antes dos dados)."""
    mark = pd.Series("", index=plan.index)
    if not spec:
        return mark.tolist()
    pil = plan.index[plan["stage"] == "pilot"]
    mark[pil[:int(spec.get("pilot", 0))]] = "sim"
    ini = plan[plan["stage"] == "initialization"]
    if len(ini):                            # alterna receitas e lotes (cobre todos antes de repetir)
        order = ini.assign(rec=ini["notes"].str.extract(r"R(\d+)")[0]).sample(frac=1, random_state=int(rng.integers(1e9)))
        chosen, seen_r, seen_b = [], set(), set()
        for idx, r in order.iterrows():
            if len(chosen) >= int(spec.get("initialization", 0)):
                break
            if r["rec"] in seen_r and r["go_batch_id"] in seen_b and len(seen_r) < order["rec"].nunique():
                continue
            chosen.append(idx)
            seen_r.add(r["rec"])
            seen_b.add(r["go_batch_id"])
        mark[chosen] = "sim"
    ad = plan[plan["stage"] == "adaptive"]
    k = int(spec.get("adaptive_rounds", 0))
    if k and len(ad):
        rounds = sorted(ad["round"].unique())
        pick = [rounds[int(round(i))] for i in np.linspace(len(rounds) / k - 1, len(rounds) - 1, k)]
        mark[ad.index[ad["round"].isin(pick)]] = "sim"
    co = plan[plan["stage"] == "confirmation"]
    n = int(spec.get("confirmation", 0))
    if n and len(co):
        per = co.groupby("go_batch_id", group_keys=False).apply(lambda g: g.head(int(np.ceil(n / co["go_batch_id"].nunique()))))
        mark[per.index[:n]] = "sim"
    return mark.tolist()


LOT_COLUMNS = {"gold": "gold_precursor_lot_id", "reductant": "reductant_lot_id", "stabilizer": "stabilizer_lot_id"}


def to_syntheses(plan: pd.DataFrame, space: dict, campaign_prefix: str = "", lots: dict | None = None) -> pd.DataFrame:
    """Linhas concretas (piloto, inicialização, controles) no formato de aunp_syntheses, status=planned.
    `lots` = {papel: lot_id} (gold é obrigatório no modelo de dados; sem ele as linhas ficam por completar)."""
    cols = _syn_columns()
    rows = []
    concrete = plan[plan[list(space)[0]].astype(str) != ""]
    for _, r in concrete.iterrows():
        row = {c: "" for c in cols}
        stage = r["stage"].upper()
        row.update({"synthesis_id": f"{campaign_prefix}{stage[:4]}-{r['slot_id']}", "go_batch_id": r["go_batch_id"],
                    "method": "in_situ_reduction_on_GO" if r["go_batch_id"] else "one_pot",
                    "campaign_id": stage if r["stage"] != "control" else "CONTROL", "design_id": r["slot_id"],
                    "fidelity": "high", "is_control": r["is_control"], "block": r["block"],
                    "run_order": int(r["run_order"]), "status": "planned",
                    "preparation_id": f"PREP-{r['slot_id']}",
                    "notes": r["notes"] + (" | TEM planejada (§4.12)" if r.get("tem") == "sim" else "")})
        for role, lot in (lots or {}).items():
            row[LOT_COLUMNS[role]] = lot
        for v in space:
            if v in row:
                row[v] = r[v]
        if "reductant_mM" in row and r.get("reductant_mM", "") != "":
            row["reductant_mM"] = r["reductant_mM"]
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def bench_sheets(plan: pd.DataFrame, space: dict, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    files = []
    vcols = [c for c in plan.columns if c.startswith("V_")]
    for d, g in plan.groupby("day"):
        lines = [f"# Ficha de bancada — dia {int(d):02d} (bloco DAY{int(d):02d})", "",
                 "Operador: ________  Data: ____/____/______  Lote(s) de reagente: ____________", "",
                 "Execute na ordem abaixo (aleatorizada). Registre falhas — elas ficam no registro (§4.17).", "",
                 "| ✓ | vaga | etapa | lote GO | controle | " + " | ".join(space) + " | " + " | ".join(vcols) +
                 " | obs. |", "|" + "---|" * (6 + len(space) + len(vcols))]
        for _, r in g.iterrows():
            vals = [str(r[k]) if r[k] != "" else "Designer" for k in space]
            vv = [str(r.get(c, "")) if pd.notna(r.get(c, "")) else "" for c in vcols]
            stg = f"{r['stage']} ({r['arm']}, rodada {r['round']})" if r.get("arm") else r["stage"]
            if r.get("tem") == "sim":
                stg += " **+TEM**"
            lines.append(f"| ☐ | {r['slot_id']} | {stg} | {r['go_batch_id'] or '—'} | {r['is_control']} | "
                         + " | ".join(vals) + " | " + " | ".join(vv) + f" | {r.get('volume_warnings', '') or ''} |")
        f = os.path.join(out_dir, f"dia_{int(d):02d}.md")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        files.append(f)
    return files


def confirm(lab: str, representation: str = "go", acq: str | None = None, seed: int = 0) -> tuple[pd.DataFrame, dict]:
    """Receitas de confirmação para os lotes reservados com um modelo CONGELADO (só dados de desenvolvimento)."""
    sys.path.insert(0, os.path.join(ROOT, "code", "aunp_designer"))
    import designer
    cfg = prereg.load()
    prereg.guard("plan.py confirm")
    space = prereg.search_space(cfg)
    camp = designer.load_campaign(lab, space, representation, prereg.log_objectives(cfg), prereg.epsilon(cfg),
                                  constraints=prereg.constraints(cfg))
    reserved = list(cfg["batches"]["reserved"])
    leak = set(camp.batches.astype(str)) & set(reserved)
    if leak:
        raise prereg.PreregError(f"lotes reservados {sorted(leak)} já aparecem no treino — a confirmação perderia a "
                                 f"independência")
    n = int(cfg["budget"]["confirmation"])
    per = {b: n // len(reserved) + (1 if i < n % len(reserved) else 0) for i, b in enumerate(reserved)}
    rows = []
    for b, k in per.items():
        try:
            fixed = designer.fixed_context(lab, camp, b, {})
        except ValueError as err:
            raise prereg.PreregError(f"lote reservado {b}: {err}. Caracterize os lotes reservados (go_characterization "
                                     f"→ go_descriptors) antes da confirmação, ou use --representation hierarchical "
                                     f"(não exige descritores)") from err
        cands = designer.propose(camp, space, q=k, fixed=fixed, acq=acq or cfg["acquisition"]["default"],
                                 seed=seed, lab=lab)
        rows.append(designer.proposals_to_syntheses(cands, space, b, CONFIRMATION_CAMPAIGN, 99, seed=seed))
    syn = pd.concat(rows, ignore_index=True)
    tables = {f: hashlib.sha256(open(os.path.join(lab, f), "rb").read()).hexdigest()
              for f in sorted(os.listdir(lab)) if f.endswith(".csv")}
    manifest = {"frozen_model": {"representation": representation, "n_training_syntheses": int(len(camp.X)),
                                 "training_batches": sorted(set(camp.batches.astype(str))), "tables_sha256": tables},
                "prereg_sha256": prereg.sha256(cfg),
                "rule": "resultados destas sínteses NÃO entram no treino (designer.usable_syntheses exclui "
                        f"campaign_id={CONFIRMATION_CAMPAIGN})"}
    return syn, manifest


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--out", default=os.path.join(ROOT, "outputs", "plano"))
    g.add_argument("--seed", type=int)
    g.add_argument("--lot", action="append", default=[], help="papel=lote_id (gold|reductant|stabilizer)")
    c = sub.add_parser("confirm")
    c.add_argument("lab")
    c.add_argument("--representation", default="go")
    c.add_argument("--out", default=os.path.join(ROOT, "outputs", "plano"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.cmd == "generate":
        prereg.guard("plan.py generate")
        res = generate(a.seed)
        plan, space = res["plan"], res["space"]
        plan.to_csv(os.path.join(a.out, "plano_experimental.csv"), index=False)
        lots = {}
        for x in a.lot:
            role, sep, lot = x.partition("=")
            if not sep or role not in LOT_COLUMNS:
                ap.error(f"--lot {x!r}: use papel=lote, papel ∈ {sorted(LOT_COLUMNS)}")
            lots[role] = lot
        if "gold" not in lots:
            print("AVISO: sem --lot gold=<lote de HAuCl4> as linhas planejadas ficam incompletas para o validador",
                  file=sys.stderr)
        to_syntheses(plan, space, lots=lots).to_csv(os.path.join(a.out, "aunp_syntheses_planejadas.csv"), index=False)
        sheets = bench_sheets(plan, space, os.path.join(a.out, "fichas"))
        json.dump(res["diagnostics"], open(os.path.join(a.out, "plano_manifest.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False, default=str)
        d = res["diagnostics"]
        print(f"{d['total_syntheses']} sínteses ({d['per_stage']}) + {d['controls']} controles em {d['days']} dias; "
              f"distância maximin da inicialização {d['init_maximin_distance']:.3f}; pré-registro: {d['prereg_state']}")
        print(f"-> {os.path.relpath(a.out, ROOT)}/ (plano_experimental.csv, aunp_syntheses_planejadas.csv, "
              f"{len(sheets)} fichas, plano_manifest.json)")
    else:
        syn, man = confirm(a.lab, a.representation)
        syn.to_csv(os.path.join(a.out, "confirmacao_planejada.csv"), index=False)
        json.dump(man, open(os.path.join(a.out, "confirmacao_manifest.json"), "w"), indent=1)
        print(syn[["synthesis_id", "go_batch_id"] + [c for c in prereg.search_space() if c in syn]].to_string(index=False))


if __name__ == "__main__":
    main()
