#!/usr/bin/env python3
"""AuNP Designer — próxima rodada de sínteses GO–AuNP por otimização bayesiana multiobjetivo.

Modelo da proposta: um GP por objetivo com kernel Matérn-5/2 + ARD (BoTorch), aquisição qLogNEHVI. A transferência
entre lotes de GO é feita por **contexto**: os descritores padronizados de cada lote (C/O, ID/IG… — GO Navigator,
code/go_navigator) entram como entradas do GP e ficam fixos no lote-alvo durante a otimização da aquisição.

Entrada e saída usam o modelo de dados do laboratório (datasets/data-model/): lê aunp_syntheses.csv + outcomes.csv
(+ go_descriptors / go_characterization) de uma pasta como datasets/lab/ e grava as propostas no formato de
aunp_syntheses.csv (com campaign_id/design_id), prontas para o operador completar os lotes de reagentes.

Uso:
    python code/aunp_designer/designer.py propose datasets/lab --batch GO-B02 --q 4            # próxima rodada
    python code/aunp_designer/designer.py propose datasets/lab --space espaco.json            # espaço de busca próprio
    python code/aunp_designer/designer.py literature                                           # faixas da literatura (semente)
    python code/aunp_designer/designer.py demo                                                 # laço completo SIMULADO
Ambiente: tools/setup_env.sh core && source .venvs/core/bin/activate
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "go_navigator"))
sys.path.insert(0, os.path.join(ROOT, "tools", "data_sources"))
from batch_descriptors import standardized_context  # noqa: E402

# variáveis de projeto (colunas de aunp_syntheses.csv) e limites padrão; troque com --space arquivo.json
DEFAULT_SPACE = {
    "HAuCl4_mM": [0.1, 1.0],              # concentração final de Au(III) (Turkevich típico: 0,25 mM)
    "reductant_to_Au_ratio": [1.0, 10.0],
    "GO_mg_mL": [0.0, 0.5],
    "pH": [3.0, 11.0],
    "temperature_C": [20.0, 90.0],
}
SYN_COLUMNS = None  # carregado do modelo de dados


def _syn_columns() -> list[str]:
    with open(os.path.join(ROOT, "datasets", "data-model", "templates", "aunp_syntheses.csv"), encoding="utf-8") as fh:
        return next(csv.reader(fh))


# ---------------------------------------------------------------------------------------------- dados

def load_campaign(lab_dir: str, space: dict, context: bool = True):
    """-> X (DataFrame: variáveis + contexto), Y (n×m, convenção de maximização), nomes/direções dos objetivos, colunas de contexto."""
    syn = pd.read_csv(os.path.join(lab_dir, "aunp_syntheses.csv"))
    out = pd.read_csv(os.path.join(lab_dir, "outcomes.csv"))
    objs = out.drop_duplicates("objective").set_index("objective")[["direction", "target_value"]]
    objs = objs[objs["direction"] != "constraint"]
    wide = out.pivot_table(index="synthesis_id", columns="objective", values="value")[list(objs.index)]
    df = syn.set_index("synthesis_id").join(wide, how="inner").dropna(subset=list(space) + list(objs.index))
    ctx_cols: list[str] = []
    if context:
        z = standardized_context(lab_dir)
        if not z.empty and z.shape[0] > 1:
            ctx_cols = [f"ctx_{c}" for c in z.columns]
            zc = z.add_prefix("ctx_")
            df = df.join(zc, on="go_batch_id")
            df[ctx_cols] = df[ctx_cols].fillna(0.0)
    Y = []
    for name, row in objs.iterrows():
        v = df[name].to_numpy(float)
        if row["direction"] == "minimize":
            v = -v
        elif row["direction"] == "target":
            v = -np.abs(v - float(row["target_value"]))
        Y.append(v)
    return df[list(space) + ctx_cols], np.column_stack(Y), objs, ctx_cols


def hypervolume(Y: np.ndarray, ref: np.ndarray) -> float:
    import torch
    from botorch.utils.multi_objective.box_decompositions.dominated import DominatedPartitioning
    bd = DominatedPartitioning(ref_point=torch.tensor(ref, dtype=torch.double), Y=torch.tensor(Y, dtype=torch.double))
    return float(bd.compute_hypervolume())


# ---------------------------------------------------------------------------------------------- modelo + aquisição

def propose(X: pd.DataFrame, Y: np.ndarray, space: dict, q: int = 4, context_values: dict | None = None,
            seed: int = 0) -> pd.DataFrame:
    import torch
    from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import ModelListGP, SingleTaskGP
    from botorch.models.transforms import Normalize, Standardize
    from botorch.optim import optimize_acqf
    from gpytorch.kernels import MaternKernel, ScaleKernel
    from gpytorch.mlls import SumMarginalLogLikelihood

    torch.manual_seed(seed)
    cols = list(X.columns)
    d = len(cols)
    lo = [space[c][0] if c in space else float(X[c].min()) - 1.0 for c in cols]
    hi = [space[c][1] if c in space else float(X[c].max()) + 1.0 for c in cols]
    bounds = torch.tensor([lo, hi], dtype=torch.double)
    tx = torch.tensor(X.to_numpy(float), dtype=torch.double)
    ty = torch.tensor(Y, dtype=torch.double)
    models = [SingleTaskGP(tx, ty[:, i:i + 1],
                           covar_module=ScaleKernel(MaternKernel(nu=2.5, ard_num_dims=d)),   # Matérn-5/2 + ARD
                           input_transform=Normalize(d, bounds=bounds), outcome_transform=Standardize(1))
              for i in range(ty.shape[1])]
    model = ModelListGP(*models)
    fit_gpytorch_mll(SumMarginalLogLikelihood(model.likelihood, model))
    span = (ty.max(0).values - ty.min(0).values).clamp_min(1e-6)
    ref = ty.min(0).values - 0.1 * span
    acq = qLogNoisyExpectedHypervolumeImprovement(model, ref_point=ref, X_baseline=tx, prune_baseline=True)
    fixed = {cols.index(k): float(v) for k, v in (context_values or {}).items() if k in cols}
    cand, _ = optimize_acqf(acq, bounds, q=q, num_restarts=8, raw_samples=256, fixed_features=fixed or None,
                            sequential=True)
    with torch.no_grad():
        post = model.posterior(cand)
    res = pd.DataFrame(cand.numpy(), columns=cols)
    for i in range(ty.shape[1]):
        res[f"pred_{i}"] = post.mean[:, i].numpy()
        res[f"pred_sd_{i}"] = post.variance[:, i].clamp_min(0).sqrt().numpy()
    res.attrs["ref_point"] = ref.numpy()
    return res


def proposals_to_syntheses(cands: pd.DataFrame, space: dict, batch: str | None, campaign: str, iteration: int,
                           method: str = "in_situ_reduction_on_GO") -> pd.DataFrame:
    cols = _syn_columns()
    rows = []
    for k, r in cands.reset_index(drop=True).iterrows():
        row = {c: "" for c in cols}
        row.update({"synthesis_id": f"{campaign}-it{iteration:02d}-{k + 1:02d}", "go_batch_id": batch or "",
                    "method": method, "campaign_id": campaign, "design_id": f"it{iteration:02d}-q{k + 1}",
                    "fidelity": "high", "notes": "proposta do AuNP Designer (qLogNEHVI)"})
        for v in space:
            row[v] = round(float(r[v]), 4)
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


# ---------------------------------------------------------------------------------------------- literatura

def literature_summary() -> None:
    """Faixas de condições na semente da literatura (datasets/literature-seed) para calibrar o espaço de busca."""
    seed = pd.read_csv(os.path.join(ROOT, "datasets", "literature-seed", "aunp_literature_seed.csv"), dtype=str).fillna("")
    for label, df in (("todas as sínteses de Au", seed), ("subconjunto GO–AuNP", seed[seed["mentions_graphene_oxide"] == "1"])):
        mm = [float(m.group(1)) for a in df["gold_precursor_amount"] for m in re.finditer(r"([\d.]+) mM", a)]
        temps = [float(t) for s in df["temperature_C"] for t in s.split("|") if re.fullmatch(r"-?[\d.]+", t)]
        red = df["reductants"].str.split("|").explode()
        print(f"== {label}: {len(df)} registros")
        if mm:
            print("  HAuCl4 citado (mM; inclui soluções-estoque) p5/p50/p95:", np.percentile(mm, [5, 50, 95]).round(3))
        if temps:
            print("  temperatura (°C) p5/p50/p95:", np.percentile(temps, [5, 50, 95]).round(1))
        print("  redutores mais comuns:", red[red != ""].value_counts().head(5).to_dict())


# ---------------------------------------------------------------------------------------------- demonstração (SIMULADA)

DEMO_BATCHES = {"GO-B01": {"C_O_ratio": 2.1, "ID_IG": 0.95}, "GO-B02": {"C_O_ratio": 1.6, "ID_IG": 1.10}}


def simulate(cond: dict, batch: str, rng: np.random.Generator) -> dict:
    """Simulador de brinquedo (NÃO é química medida): tamanho por nucleação, LSPR pela relação empírica de
    Haiss et al. (Anal. Chem. 2007, λ = 512 + 6,53·exp(0,0216·d)) e rendimento com ótimo de pH dependente do lote."""
    co = DEMO_BATCHES[batch]["C_O_ratio"]
    sites = np.tanh(4 * cond["GO_mg_mL"]) * (2.6 - co)                      # GO mais oxidado nucleia mais
    d = 6 + 45 * np.exp(-0.3 * cond["reductant_to_Au_ratio"]) * (1 + 0.6 * cond["HAuCl4_mM"]) \
        * (1 - 0.35 * sites) * (1 - 0.004 * (cond["temperature_C"] - 20))
    d = float(np.clip(d * rng.lognormal(0, 0.05), 3, 150))
    lspr = 512 + 6.53 * np.exp(0.0216 * d) + 3 * cond["GO_mg_mL"] + rng.normal(0, 0.8)
    ph_opt = 6.0 + 1.5 * (co - 1.6)
    y = 100 * (1 - np.exp(-cond["reductant_to_Au_ratio"] / 2.5)) * np.exp(-((cond["pH"] - ph_opt) / 3.0) ** 2) \
        * (0.85 + 0.3 * sites / 2) + rng.normal(0, 2)
    return {"size_mean_nm": d, "LSPR_nm": float(lspr), "yield_pct": float(np.clip(y, 0, 100))}


def _append(lab: str, table: str, rows: list[dict]) -> None:
    path = os.path.join(lab, f"{table}.csv")
    new = pd.DataFrame(rows)
    if os.path.exists(path):
        new = pd.concat([pd.read_csv(path), new], ignore_index=True)
    new.to_csv(path, index=False)


def _run_and_record(lab: str, syn: pd.DataFrame, rng, target_lspr: float) -> None:
    char, outc = [], []
    n0 = len(pd.read_csv(os.path.join(lab, "aunp_characterization.csv"))) if os.path.exists(
        os.path.join(lab, "aunp_characterization.csv")) else 0
    for _, s in syn.iterrows():
        r = simulate({v: float(s[v]) for v in DEFAULT_SPACE}, s["go_batch_id"], rng)
        for tech, qty, unit in (("UV-Vis", "LSPR_nm", "nm"), ("TEM", "size_mean_nm", "nm"), ("ICP-OES", "yield_pct", "%")):
            n0 += 1
            char.append({"measurement_id": f"M-AU-{n0:04d}", "synthesis_id": s["synthesis_id"], "technique": tech,
                         "quantity": qty, "value": round(r[qty], 3), "unit": unit, "notes": "SIMULADO"})
        outc += [{"synthesis_id": s["synthesis_id"], "objective": "yield_pct", "value": round(r["yield_pct"], 3),
                  "direction": "maximize", "target_value": "", "notes": "SIMULADO"},
                 {"synthesis_id": s["synthesis_id"], "objective": "LSPR_nm", "value": round(r["LSPR_nm"], 3),
                  "direction": "target", "target_value": target_lspr, "notes": "SIMULADO"}]
    syn = syn.copy()
    syn["gold_precursor_lot_id"] = "LOT-HAuCl4-DEMO"
    syn["reductant_lot_id"] = "LOT-CIT-DEMO"
    _append(lab, "aunp_syntheses", syn.to_dict("records"))
    _append(lab, "aunp_characterization", char)
    _append(lab, "outcomes", outc)


def demo(out_dir: str, iterations: int, q: int, seed: int, target_lspr: float = 525.0) -> None:
    rng = np.random.default_rng(seed)
    lab = os.path.join(out_dir, "lab")
    if os.path.exists(lab):
        for f in os.listdir(lab):
            os.remove(os.path.join(lab, f))
    os.makedirs(lab, exist_ok=True)
    print(f"DEMONSTRAÇÃO com dados SIMULADOS (não medidos) em {os.path.relpath(lab, ROOT)}")
    pd.DataFrame([
        {"lot_id": "LOT-HAuCl4-DEMO", "entity_id": "HAuCl4", "chemical_name": "Gold(III) chloride trihydrate",
         "canonical_name": "hydrogen tetrachloroaurate(III)", "pubchem_cid": 28133, "supplier": "DEMO",
         "lot_number": "SIM-1", "purity": 99.9, "hydrate_form": "trihydrate"},
        {"lot_id": "LOT-CIT-DEMO", "entity_id": "trisodium_citrate", "chemical_name": "Sodium citrate tribasic dihydrate",
         "canonical_name": "trisodium citrate", "pubchem_cid": 6224, "supplier": "DEMO", "lot_number": "SIM-2",
         "purity": 99.0, "hydrate_form": "dihydrate"}]).to_csv(os.path.join(lab, "reagent_lots.csv"), index=False)
    pd.DataFrame([{"go_batch_id": b, "source_type": "lab_synthesized", "synthesis_method": "modified_Hummers",
                   "notes": "SIMULADO"} for b in DEMO_BATCHES]).to_csv(os.path.join(lab, "go_batches.csv"), index=False)
    samples, meas = [], []
    for b, desc in DEMO_BATCHES.items():
        sid = f"{b}-S01"
        samples.append({"go_sample_id": sid, "go_batch_id": b, "prep_type": "film_dropcast"})
        for qty, tech, sd in (("C_O_ratio", "XPS", 0.08), ("ID_IG", "Raman", 0.03)):
            for rep in range(3):
                meas.append({"measurement_id": f"M-GO-{len(meas) + 1:04d}", "go_sample_id": sid, "technique": tech,
                             "quantity": qty, "value": round(desc[qty] + rng.normal(0, sd), 3),
                             "uncertainty": sd, "uncertainty_type": "instrument", "unit": "a.u.", "notes": "SIMULADO"})
    pd.DataFrame(samples).to_csv(os.path.join(lab, "go_samples.csv"), index=False)
    pd.DataFrame(meas).to_csv(os.path.join(lab, "go_characterization.csv"), index=False)
    from batch_descriptors import aggregate_from_measurements
    aggregate_from_measurements(lab).to_csv(os.path.join(lab, "go_descriptors.csv"), index=False)

    # histórico: lote antigo (GO-B01) bem explorado, lote novo (GO-B02) com poucas sínteses
    from scipy.stats import qmc
    space = DEFAULT_SPACE
    lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
    for batch, n in (("GO-B01", 12), ("GO-B02", 3)):
        pts = qmc.scale(qmc.LatinHypercube(len(space), seed=seed + n).random(n), lo, hi)
        syn = proposals_to_syntheses(pd.DataFrame(pts, columns=list(space)), space, batch, f"INIT-{batch}", 0)
        _run_and_record(lab, syn, rng, target_lspr)

    ctx = standardized_context(lab)
    target_ctx = {f"ctx_{c}": float(v) for c, v in ctx.loc["GO-B02"].items()}
    ref = None
    for it in range(1, iterations + 1):
        X, Y, objs, _ = load_campaign(lab, space)
        mask = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv")).set_index("synthesis_id").loc[X.index, "go_batch_id"] == "GO-B02"
        ref = Y.min(0) - 0.1 * (Y.max(0) - Y.min(0)) if ref is None else ref
        hv = hypervolume(Y[mask.to_numpy()], ref)
        cands = propose(X, Y, space, q=q, context_values=target_ctx, seed=seed + it)
        syn = proposals_to_syntheses(cands, space, "GO-B02", "DEMO", it)
        _run_and_record(lab, syn, rng, target_lspr)
        best = Y[mask.to_numpy()]
        print(f"  iteração {it}: {mask.sum():2d} sínteses no GO-B02 | hipervolume {hv:8.2f} | melhor rendimento "
              f"{best[:, list(objs.index).index('yield_pct')].max():5.1f} % | menor |LSPR-{target_lspr:.0f}| "
              f"{-best[:, list(objs.index).index('LSPR_nm')].max():5.2f} nm")
    X, Y, objs, _ = load_campaign(lab, space)
    mask = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv")).set_index("synthesis_id").loc[X.index, "go_batch_id"] == "GO-B02"
    print(f"  final: hipervolume no GO-B02 = {hypervolume(Y[mask.to_numpy()], ref):.2f}")
    import lab_data_model
    rc = lab_data_model.validate(lab)
    if rc:
        raise SystemExit("tabelas geradas não passaram no validador")


# ---------------------------------------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose", help="próxima rodada a partir de uma pasta de dados de laboratório")
    p.add_argument("lab_dir")
    p.add_argument("--batch", help="lote de GO-alvo (contexto fixo); vazio = sem GO/sem contexto")
    p.add_argument("--q", type=int, default=4)
    p.add_argument("--space", help="JSON {variável: [mín, máx]} (padrão: DEFAULT_SPACE)")
    p.add_argument("--campaign", default="CAMP")
    p.add_argument("--iteration", type=int, default=1)
    p.add_argument("--no-context", action="store_true", help="ignora descritores de lote (sem transferência)")
    p.add_argument("--out", help="CSV de saída (padrão: outputs/aunp_designer/proposals_<data>.csv)")
    sub.add_parser("literature", help="faixas de condições na semente da literatura")
    dm = sub.add_parser("demo", help="laço completo com simulador (dados SIMULADOS)")
    dm.add_argument("--iterations", type=int, default=4)
    dm.add_argument("--q", type=int, default=2)
    dm.add_argument("--seed", type=int, default=0)
    dm.add_argument("--out", default=os.path.join(ROOT, "outputs", "aunp_designer_demo"))
    a = ap.parse_args()

    if a.cmd == "literature":
        literature_summary()
    elif a.cmd == "demo":
        demo(a.out, a.iterations, a.q, a.seed)
    else:
        space = json.load(open(a.space)) if a.space else DEFAULT_SPACE
        X, Y, objs, ctx_cols = load_campaign(a.lab_dir, space, context=not a.no_context)
        print(f"{len(X)} sínteses com desfecho; objetivos: {dict(objs['direction'])}; contexto: {ctx_cols or 'nenhum'}")
        ctx_vals = {}
        if ctx_cols and a.batch:
            z = standardized_context(a.lab_dir)
            ctx_vals = {f"ctx_{c}": float(v) for c, v in z.loc[a.batch].items()}
        cands = propose(X, Y, space, q=a.q, context_values=ctx_vals)
        syn = proposals_to_syntheses(cands, space, a.batch, a.campaign, a.iteration)
        out = a.out or os.path.join(ROOT, "outputs", "aunp_designer", f"proposals_{date.today()}.csv")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        syn.to_csv(out, index=False)
        print(syn[["synthesis_id"] + list(space)].to_string(index=False))
        print(f"-> {os.path.relpath(out, ROOT)} (complete os lotes de reagentes antes de copiar para aunp_syntheses.csv)")


if __name__ == "__main__":
    main()
