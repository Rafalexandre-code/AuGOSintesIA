#!/usr/bin/env python3
"""Laço fechado de aprendizado ativo e ponto de integração com self-driving lab / cloud lab (§4.16, condicional).

Uma rodada (`step`) faz, em ordem: ingestão dos brutos (code/campaign/ingest.py derive --write) e conferência
(`check`), QC (code/qc/qc_check.py → qc_results.csv), proposta do AuNP Designer (braço, lote-alvo e lotes de
reagente da rodada) e a FILA DE TRABALHOS — um JSON neutro em relação ao instrumento, com receita, volumes de
pipetagem (estoques do pré-registro), ordem de adição e medidas pedidas. As propostas entram em aunp_syntheses.csv
com status `planned` (o Designer as ignora até virarem `done`).

Executores (quem transforma a fila em sínteses e devolve ARQUIVOS BRUTOS — nunca desfechos prontos):
  * manual    — a bancada: grava a fila e a ficha (Markdown) e para; o operador sintetiza, registra spectra.csv e
                as saídas de tem.py/dls.py, muda o status para `done` e roda `step` de novo;
  * simulated — o laboratório SIMULADO (code/benchmarking/sim_lab.py) executa a fila e devolve só os espectros
                brutos e a TEM das sínteses marcadas; serve para testar o laço inteiro sem bancada (`demo`).
Um robô de pipetagem ou um cloud lab entra como outro executor: lê a fila (`jobs[*].volumes_uL`, `steps`) e grava
os brutos no mesmo formato. Nada aqui depende de um fabricante.

Uso:
    python code/sdl/loop.py step datasets/lab --batch L2 --arm go+impurities --q 1 --lot reductant=RED-A
    python code/sdl/loop.py demo --rounds 4          # laço autônomo no laboratório SIMULADO
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "code", d) for d in ("campaign", "aunp_designer", "qc", "benchmarking", "spectral")]
import designer  # noqa: E402
import ingest  # noqa: E402
import plan as plan_mod  # noqa: E402
import prereg  # noqa: E402
import qc_check  # noqa: E402

SCHEMA = "augosintesia-job-queue/1"
STEPS = ("água", "dispersão de GO (sonicada, SOP-GO-DISP-01)", "HAuCl4", "ajuste de pH", "temperatura de reação",
         "redutor (adição conforme addition_order/addition_rate)", "agitação pelo tempo da receita",
         "UV-Vis em duplicata (SOP-UVVIS-01)")


# ---------------------------------------------------------------------------------------------- executores

class ManualExecutor:
    """Bancada: grava fila + ficha e devolve False (resultados chegam quando o operador registrar)."""
    name = "manual"

    def __init__(self, out_dir: str):
        self.out_dir = out_dir

    def submit(self, queue: dict) -> str:
        os.makedirs(self.out_dir, exist_ok=True)
        stem = os.path.join(self.out_dir, f"{queue['campaign']}_r{queue['round']:02d}")
        with open(stem + ".json", "w", encoding="utf-8") as fh:
            json.dump(queue, fh, indent=1, ensure_ascii=False)
        lines = [f"# Ficha — {queue['campaign']}, rodada {queue['round']} ({queue['created']})", "",
                 f"Braço: {queue['arm'] or '—'} | lote de GO: {queue['go_batch_id']} | aquisição: {queue['acquisition']}",
                 "", "| síntese | " + " | ".join(queue["variables"]) + " | volumes (µL) | medidas |",
                 "|---|" + "---|" * (len(queue["variables"]) + 2)]
        for j in queue["jobs"]:
            vol = ", ".join(f"{k[2:-3]} {v}" for k, v in j["volumes_uL"].items())
            vol += f" ⚠ {j['warnings']}" if j["warnings"] else ""
            lines.append(f"| {j['job_id']} | " + " | ".join(f"{j['recipe'][v]:.3g}" for v in queue["variables"])
                         + f" | {vol} | {', '.join(j['measure'])} |")
        lines += ["", "Ordem: " + " → ".join(STEPS), "",
                  "Depois: registrar spectra.csv (arquivos em raw_data/), `ingest.py add` as saídas de tem.py, mudar o "
                  "status para done e rodar `loop.py step` de novo."]
        with open(stem + ".md", "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return stem + ".json"

    def collect(self, lab: str, queue: dict) -> bool:
        return False


class SimulatedExecutor:
    """Laboratório SIMULADO: executa a fila e devolve só brutos (espectros) e a TEM pedida — como a bancada."""
    name = "simulated"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def submit(self, queue: dict) -> str:
        self.pending = queue
        return "(simulado)"

    def collect(self, lab: str, queue: dict) -> bool:
        import sim_lab
        syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
        ids = [j["job_id"] for j in queue["jobs"]]
        todo = syn[syn["synthesis_id"].isin(ids)].assign(status="done")
        sim_lab.run_syntheses(lab, todo, self.rng)
        _keep_only_raw(lab, ids, tem={j["job_id"] for j in queue["jobs"] if "TEM" in j["measure"]})
        syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
        syn = syn[~(syn["synthesis_id"].isin(ids) & (syn["status"] == "planned"))]   # a linha executada substitui
        syn.to_csv(os.path.join(lab, "aunp_syntheses.csv"), index=False)
        return True


def _keep_only_raw(lab: str, ids: list[str], tem: set) -> None:
    """Remove o que o simulador grava pronto (desfechos, descritores do UV-Vis) e a TEM não pedida."""
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    out[~out["synthesis_id"].isin(ids)].to_csv(os.path.join(lab, "outcomes.csv"), index=False)
    ch = pd.read_csv(os.path.join(lab, "aunp_characterization.csv"))
    new = ch["synthesis_id"].isin(ids)
    keep = ~new | ((ch["technique"] == "TEM") & ch["synthesis_id"].isin(tem))
    ch[keep].to_csv(os.path.join(lab, "aunp_characterization.csv"), index=False)


# ---------------------------------------------------------------------------------------------- rodada

def job_queue(cands: pd.DataFrame, syn: pd.DataFrame, space: dict, meta: dict, tem: bool) -> dict:
    stocks = prereg.load().get("stock_solutions", {})
    jobs = []
    for (_, c), (_, s) in zip(cands.iterrows(), syn.iterrows()):
        recipe = {k: float(c[k]) for k in space}
        vols = plan_mod.volumes(recipe, stocks) if stocks else {}
        vol_warn = vols.pop("volume_warnings", "")
        jobs.append({"job_id": s["synthesis_id"], "go_batch_id": s["go_batch_id"], "warnings": vol_warn,
                     "lots": {r: s[col] for r, col in designer.LOT_ROLES.items() if str(s.get(col, "")) not in ("", "nan")},
                     "recipe": recipe, "volumes_uL": vols, "steps": list(STEPS),
                     "measure": ["UV-Vis x2"] + (["TEM"] if tem else []),
                     "prediction": {k: float(c[k]) for k in c.index if k.startswith(("pred_", "p_feasible"))}})
    return {"schema": SCHEMA, "created": dt.datetime.now().isoformat(timespec="seconds"),
            "prereg_sha256": prereg.sha256(prereg.load()), "variables": list(space), "jobs": jobs, **meta}


def step(lab: str, batch: str, arm: str | None, q: int, lots: dict, rnd: int, campaign: str, executor, seed: int = 0,
         tem: bool = False) -> dict:
    """Uma rodada do laço: ingestão → conferência → QC → proposta → fila → executor."""
    space = designer.DEFAULT_SPACE
    res = ingest.derive(lab)
    ingest.write(lab, res)
    diff = ingest.compare(lab, ingest.derive(lab)["outcomes"])
    if not diff.empty:
        raise SystemExit(f"outcomes.csv diverge dos brutos depois da ingestão:\n{diff.to_string(index=False)}")
    qc, _ = qc_check.run(lab)
    qc.to_csv(os.path.join(lab, "qc_results.csv"), index=False)
    rep = arm if arm in designer.REPRESENTATIONS else (arm.split(designer.ARM_SEP)[0] if arm else "go")
    camp = designer.load_campaign(lab, space, rep, designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints(), arm=arm)
    fixed = designer.fixed_context(lab, camp, batch, lots)
    cands = designer.propose(camp, space, q=q, fixed=fixed, seed=seed, lab=lab)
    syn = designer.proposals_to_syntheses(cands, space, batch, campaign, rnd, lots=lots, seed=seed, arm=arm)
    syn = syn.assign(status="planned")
    old = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    pd.concat([old, syn], ignore_index=True).to_csv(os.path.join(lab, "aunp_syntheses.csv"), index=False)
    queue = job_queue(cands, syn, space, {"campaign": campaign, "round": rnd, "arm": arm, "go_batch_id": batch,
                                          "acquisition": designer.default_acq(), "executor": executor.name,
                                          "n_training": int(len(camp.X))}, tem)
    where = executor.submit(queue)
    done = executor.collect(lab, queue)
    return {"queue": queue, "written": where, "executed": done, "qc_fail": int((qc["status"] == "fail").sum()),
            "warnings": res["warnings"]}


def demo(rounds: int = 4, q: int = 2, seed: int = 0, lab: str | None = None) -> pd.DataFrame:
    """Laço autônomo no laboratório SIMULADO: piloto + inicialização e `rounds` rodadas pelo executor simulado."""
    import sim_lab
    from campaign_sim import _lhs
    lab = lab or os.path.join(ROOT, "outputs", "sdl_demo", "lab")
    space = designer.DEFAULT_SPACE
    sim_lab.init_lab(lab, ("L1", "L2", "L3"), seed=seed)
    rng = np.random.default_rng(seed)
    ref = pd.DataFrame([plan_mod.reference_recipe(space)])
    seed_ids = []
    for b, n in zip(("L1", "L2", "L3"), (4, 2, 2)):
        s = designer.proposals_to_syntheses(pd.concat([ref] * n, ignore_index=True), space, b, f"PILOT-{b}", 0,
                                            seed=seed).assign(status="done")
        sim_lab.run_syntheses(lab, s, rng)
        seed_ids += list(s["synthesis_id"])
    for b in ("L1", "L2", "L3"):
        s = designer.proposals_to_syntheses(_lhs(space, 4, seed), space, b, f"INIT-{b}", 0, seed=seed)
        sim_lab.run_syntheses(lab, s.assign(status="done"), rng)
        seed_ids += list(s["synthesis_id"])
    _keep_only_raw(lab, seed_ids, tem=set(seed_ids[::2]))                 # TEM em metade, como no plano
    ex = SimulatedExecutor(seed)
    hist = []
    for r in range(1, rounds + 1):
        batch = ("L1", "L2", "L3")[(r - 1) % 3]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = step(lab, batch, "go+impurities", q, {"reductant": ("RED-A", "RED-B")[r % 2]}, r, "SDL-DEMO", ex,
                       seed=seed + r, tem=r % 2 == 1)
        o = pd.read_csv(os.path.join(lab, "outcomes.csv"))
        hist.append({"round": r, "batch": batch, "n_training": out["queue"]["n_training"],
                     "best_J_so_far": float(o.loc[o["objective"] == "spectral_loss_J", "value"].min()),
                     "qc_fail": out["qc_fail"]})
    # a última rodada executada ainda não foi ingerida
    ingest.write(lab, ingest.derive(lab))
    return pd.DataFrame(hist)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("step", help="uma rodada na bancada (executor manual)")
    s.add_argument("lab")
    s.add_argument("--batch", required=True)
    s.add_argument("--arm")
    s.add_argument("--q", type=int, default=1)
    s.add_argument("--lot", action="append", default=[], help="papel=lote (gold|reductant|stabilizer)")
    s.add_argument("--round", type=int, default=1)
    s.add_argument("--campaign", default="ADAPTIVE")
    s.add_argument("--tem", action="store_true", help="pede TEM para as sínteses desta rodada")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", default=os.path.join(ROOT, "outputs", "sdl"))
    d = sub.add_parser("demo", help="laço autônomo no laboratório SIMULADO")
    d.add_argument("--rounds", type=int, default=4)
    d.add_argument("--q", type=int, default=2)
    d.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "demo":
        print("SIMULADO —", demo(a.rounds, a.q, a.seed).to_string(index=False))
        return
    prereg.guard("loop.py step")
    lots = dict(x.split("=", 1) for x in a.lot)
    out = step(a.lab, a.batch, a.arm, a.q, lots, a.round, a.campaign, ManualExecutor(a.out), a.seed, a.tem)
    for w in out["warnings"]:
        print("AVISO:", w)
    print(f"QC: {out['qc_fail']} síntese(s) reprovada(s) (fora do treino); {out['queue']['n_training']} no treino")
    print(f"fila: {out['written']} (+ ficha .md); propostas em aunp_syntheses.csv com status planned")


if __name__ == "__main__":
    main()
