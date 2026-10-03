#!/usr/bin/env python3
"""AuNP Designer — próxima rodada de sínteses GO–AuNP por otimização bayesiana multiobjetivo (§4.5, §4.7, §4.18).

Modelo: um GP por objetivo com kernel **Matérn-5/2 + ARD** (BoTorch). Os quatro braços da proposta, com a mesma
inicialização, alvos e orçamento, e o GP hierárquico (§4.7):
  recipe          só a receita
  batch           receita + identidade do lote (GP multitarefa/ICM, o lote como tarefa)
  go              receita + descritores do GO com incerteza (GO Navigator), padronizados — transferência entre lotes
  go+impurities   + descritores de impurezas dos lotes de reagentes (tabela reagent_analyses — §4.3)
  hierarchical    receita com efeitos aleatórios funcionais de fornecedor e de lote (code/transfer_learning):
                  prevê lote novo com a incerteza de "lote não visto"
Padrões (espaço de busca com tempo, objetivos, restrições, ε, aquisição) vêm do plano PRÉ-REGISTRADO
(config/preregistration.yaml, code/campaign/prereg.py); as opções de linha de comando só os substituem explicitamente.
Restrições de desfecho (Objetivo 3: "multiobjetivo sob restrições"): linhas `constraint` de outcomes.csv viram GPs
próprios e entram na aquisição como restrições (viável se lower ≤ y ≤ upper); a saída traz P(viável).
Aquisição: qNEHVI (padrão, como na proposta). qLogNEHVI só "se houver ruído heteroscedástico comprovado" (§4.5):
`--acq auto` roda o noise-check (Brown–Forsythe entre preparações repetidas + Breusch–Pagan nos resíduos) e só
então troca. Ruído medido (`uncertainty` em outcomes.csv) entra como variância de observação fixa.
Objetivos de outcomes.csv (maximize/minimize/target); log(y + ε) nos objetivos marcados `log` no pré-registro.
Seleção novelty-aware opcional: escore = w·a + (1 − w)·n (a = aquisição, n = novidade; ambos normalizados).
Confirmação (§4.11): sínteses com campaign_id=CONFIRMATION nunca entram no treino (modelo congelado).

Subcomandos:
    propose  datasets/lab --batch L2 --representation go --q 4 [--acq qnehvi] [--novelty-w 0.7] [--lot reductant=RED-A]
    validate datasets/lab                     # leave-one-batch-out (LBO) dos braços: RMSE, cobertura do IC 95 %
    noise-check datasets/lab                  # heteroscedasticidade -> qNEHVI ou qLogNEHVI (regra da proposta)
    explain  datasets/lab --representation go # SHAP sobre a média do GP + estabilidade por bootstrap (§4.13)
    literature                                # faixas de condições na semente da literatura
    demo                                      # laço completo com o laboratório SIMULADO (code/benchmarking)
Cada execução grava run_metadata.json (commit, pacotes, semente, argumentos, hash das tabelas) — §4.17.
Ambiente: tools/setup_env.sh core && source .venvs/core/bin/activate
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/go_navigator", "tools/data_sources", "code/benchmarking", "code/spectral", "code/campaign",
            "code/transfer_learning", "code/qc"):
    sys.path.insert(0, os.path.join(ROOT, sub))
from batch_descriptors import standardized_context  # noqa: E402
import prereg  # noqa: E402

warnings.filterwarnings("ignore", message=".*torch.jit.script.*")
# o BoTorch recomenda trocar qNEHVI por qLogNEHVI; a proposta fixa qNEHVI salvo heteroscedasticidade comprovada
# (noise-check) — o aviso aparece uma vez, não a cada aquisição
warnings.filterwarnings("once", message=".*qNoisyExpectedHypervolumeImprovement.*")

# variáveis de projeto (colunas de aunp_syntheses.csv): do pré-registro; esta cópia só vale se ele não puder ser lido
FALLBACK_SPACE = {
    "HAuCl4_mM": [0.1, 1.0],              # concentração final de Au(III) (Turkevich típico: 0,25 mM)
    "reductant_to_Au_ratio": [1.0, 10.0],
    "GO_mg_mL": [0.0, 0.5],
    "pH": [3.0, 11.0],
    "temperature_C": [20.0, 90.0],
    "time_min": [5.0, 120.0],
}
try:
    _PREREG = prereg.load()
    DEFAULT_SPACE = prereg.search_space(_PREREG)
except Exception as _exc:  # noqa: BLE001 — sem pyyaml/arquivo: segue com a cópia, mas avisa
    warnings.warn(f"pré-registro indisponível ({_exc}); usando FALLBACK_SPACE")
    _PREREG, DEFAULT_SPACE = None, FALLBACK_SPACE
REPRESENTATIONS = ("recipe", "batch", "go", "go+impurities", "hierarchical")
ARM_SEP = ":"                          # design_id = "<braço>:<rodada>"
CONFIRMATION_CAMPAIGN = "CONFIRMATION"
LOT_ROLES = {"gold": "gold_precursor_lot_id", "reductant": "reductant_lot_id", "stabilizer": "stabilizer_lot_id"}


def _syn_columns() -> list[str]:
    with open(os.path.join(ROOT, "datasets", "data-model", "templates", "aunp_syntheses.csv"), encoding="utf-8") as fh:
        return next(csv.reader(fh))


def _read(lab: str, table: str) -> pd.DataFrame | None:
    p = os.path.join(lab, f"{table}.csv")
    return pd.read_csv(p) if os.path.exists(p) else None


# ---------------------------------------------------------------------------------------------- dados

def arm_of(design_id) -> str:
    """Braço que propôs a síntese (design_id = "<braço>:<rodada>"; vazio = dado compartilhado: piloto, inicialização)."""
    d = "" if pd.isna(design_id) else str(design_id)
    return d.split(ARM_SEP, 1)[0] if ARM_SEP in d else ""


def usable_syntheses(lab: str, include_confirmation: bool = False, arm: str | None = None) -> pd.DataFrame:
    """Sínteses que entram no modelo: sem falhas/planejadas, sem brancos de GO (sem Au) e — salvo pedido explícito —
    sem a confirmação (o modelo que recomenda a confirmação fica congelado; §4.11). Com `arm`, cada braço da
    comparação prospectiva vê só os dados compartilhados (piloto, inicialização) e as SUAS rodadas adaptativas:
    as trajetórias ficam independentes, como exige a comparação (config/preregistration.yaml → arms)."""
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    if arm is not None and "design_id" in syn:
        owner = syn["design_id"].map(arm_of)
        syn = syn[(owner == "") | (owner == arm)]
    if "status" in syn:
        syn = syn[~syn["status"].astype(str).isin(["failed", "planned"])]
    if "is_control" in syn:
        syn = syn[syn["is_control"].astype(str) != "GO_blank"]
    if not include_confirmation and "campaign_id" in syn:
        syn = syn[syn["campaign_id"].astype(str) != CONFIRMATION_CAMPAIGN]
    from qc_check import failed_syntheses
    bad = failed_syntheses(lab)                     # QC (config/qc_criteria.yaml): `fail` não sustenta a decisão
    if bad:
        n0 = len(syn)
        syn = syn[~syn["synthesis_id"].astype(str).isin(bad)]
        if len(syn) < n0:
            warnings.warn(f"{n0 - len(syn)} síntese(s) com QC=fail excluídas (qc_results.csv)")
    return syn.reset_index(drop=True)


def default_acq() -> str:
    return (_PREREG or {}).get("acquisition", {}).get("default", "qnehvi")


def default_constraints() -> dict:
    return prereg.constraints(_PREREG) if _PREREG else {}


def default_logs() -> tuple:
    return prereg.log_objectives(_PREREG) if _PREREG else ()


def default_eps() -> float:
    return prereg.epsilon(_PREREG) if _PREREG else 1e-3


def impurity_context(lab: str, syn: pd.DataFrame) -> pd.DataFrame:
    """Descritores de impurezas por síntese: para cada papel de lote (ouro, redutor, estabilizante), o valor de cada
    analito medido naquele lote (reagent_analyses), padronizado. Índice = synthesis_id."""
    ra = _read(lab, "reagent_analyses")
    if ra is None or ra.empty:
        return pd.DataFrame(index=syn["synthesis_id"])
    per_lot = ra.pivot_table(index="lot_id", columns="analyte", values="value", aggfunc="mean")
    per_lot.index = per_lot.index.astype(str)
    cols = {}
    for role, col in LOT_ROLES.items():
        if col not in syn:
            continue
        s = syn[["synthesis_id", col]].copy()
        s[col] = s[col].astype(str)
        m = s.merge(per_lot, left_on=col, right_index=True, how="left").set_index("synthesis_id")
        for a in per_lot.columns:
            cols[f"imp_{role}_{a}"] = m[a]
    df = pd.DataFrame(cols)
    df = df.loc[:, df.notna().any() & (df.std(ddof=0).fillna(0) > 0)]
    return ((df - df.mean()) / df.std(ddof=0)).fillna(0.0)


def impurity_values_for_lots(lab: str, lots: dict[str, str], ref: pd.DataFrame) -> dict[str, float]:
    """Valores padronizados (mesma escala de impurity_context) para os lotes que serão usados na próxima rodada."""
    ra = _read(lab, "reagent_analyses")
    if ra is None or not os.path.exists(os.path.join(lab, "aunp_syntheses.csv")):
        return {}
    syn = usable_syntheses(lab)       # mesma população usada em impurity_context (mesma escala)
    per_lot = ra.pivot_table(index="lot_id", columns="analyte", values="value", aggfunc="mean")
    per_lot.index = per_lot.index.astype(str)
    raw = {}
    for role, col in LOT_ROLES.items():
        if col not in syn:
            continue
        s = syn[["synthesis_id", col]].copy()
        s[col] = s[col].astype(str)
        m = s.merge(per_lot, left_on=col, right_index=True, how="left")
        for a in per_lot.columns:
            name = f"imp_{role}_{a}"
            if name in ref.columns:
                mu, sd = m[a].mean(), m[a].std(ddof=0)
                sd = sd if np.isfinite(sd) and sd > 0 else 1.0
                v = per_lot.loc[lots[role], a] if role in lots and lots[role] in per_lot.index else mu
                raw[name] = float((v - mu) / sd)
    return raw


@dataclass
class Campaign:
    X: pd.DataFrame
    Y: np.ndarray                      # convenção de maximização, após transformações
    Yvar: list                         # por objetivo: np.ndarray (variância) ou None
    objs: pd.DataFrame
    representation: str
    batches: pd.Series
    task_col: str | None = None
    task_map: dict = field(default_factory=dict)
    logs: tuple = ()
    eps: float = 1e-3
    C: np.ndarray | None = None        # restrições (n × k), escala original
    cons: dict = field(default_factory=dict)          # {nome: (lower, upper)}
    level_cols: tuple = ()             # colunas de nível do GP hierárquico (rótulos inteiros)
    level_maps: dict = field(default_factory=dict)    # {coluna: {rótulo: id}}

    def to_original(self, name: str, mu: np.ndarray, sd: np.ndarray) -> tuple[str, np.ndarray, np.ndarray]:
        """Converte a previsão da escala do modelo (maximização, log) para as unidades do objetivo."""
        d = self.objs.loc[name, "direction"]
        if d == "maximize":
            return f"pred_{name}", mu, sd
        if d == "target":
            return f"pred_dev_{name}", -mu, sd          # distância prevista até o alvo
        v = -mu
        if name in self.logs:
            return f"pred_{name}", np.exp(v) - self.eps, np.exp(v) * sd
        return f"pred_{name}", v, sd


def _suppliers(lab: str) -> dict:
    gb = _read(lab, "go_batches")
    if gb is None or "supplier" not in gb or gb["supplier"].isna().all():
        return {}
    return dict(zip(gb["go_batch_id"].astype(str), gb["supplier"].fillna("desconhecido").astype(str)))


def load_campaign(lab: str, space: dict, representation: str = "go", log_objectives=(), eps: float = 1e-3,
                  use_noise: bool = True, constraints: dict | None = None, arm: str | None = None) -> Campaign:
    syn = usable_syntheses(lab, arm=arm)
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    allobj = out.drop_duplicates("objective").set_index("objective")[["direction", "target_value"]]
    objs = allobj[allobj["direction"] != "constraint"]
    cons = {}
    for name, (lo, hi) in (constraints or {}).items():
        if name in set(out["objective"]):
            cons[name] = (None if lo is None else float(lo), None if hi is None else float(hi))
        else:
            warnings.warn(f"restrição {name!r} sem dados em outcomes.csv: ignorada nesta rodada")
    names = list(objs.index)
    bad_target = [n for n in names if objs.loc[n, "direction"] == "target" and not np.isfinite(
        pd.to_numeric(objs.loc[n, "target_value"], errors="coerce"))]
    if bad_target:
        raise ValueError(f"objetivo(s) 'target' sem target_value em outcomes.csv: {bad_target}")
    unknown = [n for n in log_objectives if n not in names]
    if unknown:
        raise ValueError(f"--log-objectives cita objetivos inexistentes: {unknown} (disponíveis: {names})")
    val = out.pivot_table(index="synthesis_id", columns="objective", values="value")[names]
    unc = out.pivot_table(index="synthesis_id", columns="objective", values="uncertainty") \
        if "uncertainty" in out else pd.DataFrame(index=val.index)
    df = syn.set_index("synthesis_id").join(val, how="inner")
    missing_space = [c for c in space if c not in df]
    if missing_space:
        raise ValueError(f"aunp_syntheses.csv sem as variáveis do espaço {missing_space}")
    n0 = len(df)
    lacking = {n: int(df[n].isna().sum()) for n in names if df[n].isna().any()}
    df = df.dropna(subset=list(space) + names)
    if len(df) < n0:
        warnings.warn(f"{n0 - len(df)} síntese(s) excluídas por falta de objetivo {lacking or ''} — derive os valores "
                      "com code/campaign/ingest.py (tamanho do UV-Vis calibrado na TEM)")
    if cons:
        cval = out[out["objective"].isin(list(cons))].pivot_table(index="synthesis_id", columns="objective",
                                                                  values="value")
        df = df.join(cval[list(cons)], how="left")
        # restrição sem valor numa síntese NÃO a exclui: o GP daquela restrição usa só as sínteses medidas (ex.: CV
        # de tamanho só existe onde houve TEM); com menos de 4 valores, a restrição fica de fora nesta rodada
        for name in list(cons):
            n_ok = int(df[name].notna().sum())
            if n_ok < 4:
                warnings.warn(f"restrição {name!r} com só {n_ok} valor(es): ignorada nesta rodada")
                cons.pop(name)
                df = df.drop(columns=name)
            elif n_ok < len(df):
                warnings.warn(f"restrição {name!r}: modelada com {n_ok} de {len(df)} sínteses (as demais não a mediram)")
    feats = df[list(space)].astype(float).copy()
    task_col, task_map = None, {}
    if representation == "batch":
        ids = sorted(df["go_batch_id"].fillna("none").astype(str).unique())
        task_map = {b: i for i, b in enumerate(ids)}
        feats["task"] = df["go_batch_id"].fillna("none").astype(str).map(task_map).astype(float)
        task_col = "task"
    if representation in ("go", "go+impurities"):
        z = standardized_context(lab)
        if not z.empty and z.shape[0] > 1:
            ctx = df[["go_batch_id"]].join(z.add_prefix("ctx_"), on="go_batch_id").drop(columns="go_batch_id")
            feats = feats.join(ctx.fillna(0.0))
    if representation == "go+impurities":
        imp = impurity_context(lab, syn.reset_index(drop=True))
        if not imp.empty:
            feats = feats.join(imp, how="left").fillna(0.0)
    level_cols, level_maps = (), {}
    if representation == "hierarchical":
        sup = _suppliers(lab)
        batch = df["go_batch_id"].fillna("none").astype(str)
        if len(set(sup.get(b, "") for b in batch)) > 1:
            labels = batch.map(lambda b: sup.get(b, "desconhecido"))
            level_maps["lvl_supplier"] = {v: i for i, v in enumerate(sorted(labels.unique()))}
            feats["lvl_supplier"] = labels.map(level_maps["lvl_supplier"]).astype(float)
        level_maps["lvl_batch"] = {v: i for i, v in enumerate(sorted(batch.unique()))}
        feats["lvl_batch"] = batch.map(level_maps["lvl_batch"]).astype(float)
        level_cols = tuple(level_maps)
    Y, Yvar = [], []
    for name, row in objs.iterrows():
        v = df[name].to_numpy(float)
        var = None
        if use_noise and name in unc.columns:
            u = unc.reindex(df.index)[name].to_numpy(float)
            if np.isfinite(u).all():
                var = np.maximum(u ** 2, 1e-12)
        if name in log_objectives:
            if np.any(v + eps <= 0):
                raise ValueError(f"log(y + ε) indefinido para {name}: há valores ≤ −ε ({v.min():g})")
            if var is not None:
                var = var / (v + eps) ** 2
            v = np.log(v + eps)
        if row["direction"] == "minimize":
            v = -v
        elif row["direction"] == "target":
            v = -np.abs(v - float(row["target_value"]))
        Y.append(v)
        Yvar.append(var)
    C = df[list(cons)].to_numpy(float) if cons else None
    return Campaign(feats, np.column_stack(Y), Yvar, objs, representation, df["go_batch_id"].fillna("none"),
                    task_col, task_map, tuple(log_objectives), eps, C, cons, level_cols, level_maps)


# ---------------------------------------------------------------------------------------------- modelo

def _bounds(camp: Campaign, space: dict):
    import torch
    lo, hi = [], []
    for c in camp.X.columns:
        if c in space:
            a, b = space[c]
        elif c == camp.task_col:
            a, b = 0.0, float(max(camp.task_map.values(), default=0))
        elif c in camp.level_cols:
            a, b = 0.0, float(max(camp.level_maps[c].values(), default=0)) + 1.0
        else:
            a, b = float(camp.X[c].min()) - 1.0, float(camp.X[c].max()) + 1.0
        lo.append(a)
        hi.append(b)
    return torch.tensor([lo, hi], dtype=torch.double)


def _fit(model, tries: int = 6) -> bool:
    """Ajuste de hiperparâmetros robusto: o fit_gpytorch_mll pode falhar dependendo do estado aleatório; tenta de
    novo com sementes independentes (sem alterar o gerador global) e, em último caso, mantém os valores iniciais."""
    import torch
    from botorch.exceptions.errors import ModelFittingError
    from botorch.fit import fit_gpytorch_mll
    from gpytorch.mlls import ExactMarginalLogLikelihood
    mll = ExactMarginalLogLikelihood(model.likelihood, model)
    for k in range(tries):
        try:
            with torch.random.fork_rng():
                torch.manual_seed(7919 * (k + 1))
                fit_gpytorch_mll(mll)
            return True
        except ModelFittingError:
            continue
    warnings.warn("ajuste do GP falhou em todas as tentativas; usando hiperparâmetros iniciais")
    mll.eval()
    return False


def build_model(camp: Campaign, space: dict, rows=None):
    """ModelListGP: um GP por objetivo e, depois deles, um por restrição (escala original)."""
    import torch
    from botorch.models import ModelListGP, MultiTaskGP, SingleTaskGP
    from botorch.models.transforms import Normalize, Standardize
    from gpytorch.kernels import ScaleKernel
    import hierarchical

    idx = np.arange(len(camp.X)) if rows is None else np.asarray(rows)
    tx = torch.tensor(camp.X.to_numpy(float)[idx], dtype=torch.double)
    ty = torch.tensor(camp.Y[idx], dtype=torch.double)
    bounds = _bounds(camp, space)
    d = tx.shape[1]
    cols = list(camp.X.columns)
    outs = [(ty[:, i:i + 1], camp.Yvar[i], tx) for i in range(ty.shape[1])]
    if camp.C is not None:
        for j in range(camp.C.shape[1]):
            c = camp.C[idx, j]
            ok = np.isfinite(c)                          # restrição medida só em parte das sínteses (ex.: CV pela TEM)
            outs.append((torch.tensor(c[ok, None], dtype=torch.double), None, tx[torch.as_tensor(ok)]))
    models = []
    for y, var, tx_i in outs:
        yv = None if var is None else torch.tensor(var[idx], dtype=torch.double).unsqueeze(-1)
        if camp.level_cols:
            lv = [cols.index(c) for c in camp.level_cols]
            m = hierarchical.build_hierarchical_gp(tx_i, y, [j for j in range(d) if j not in lv], lv, bounds, yv)
        elif camp.task_col:
            t = list(camp.X.columns).index(camp.task_col)
            base = [j for j in range(d) if j != t]
            m = MultiTaskGP(tx_i, y, task_feature=t, train_Yvar=yv,
                            covar_module=hierarchical.matern52(d - 1),
                            input_transform=Normalize(d, indices=base, bounds=bounds),
                            outcome_transform=Standardize(1), all_tasks=list(camp.task_map.values()))
        else:
            m = SingleTaskGP(tx_i, y, train_Yvar=yv,
                             covar_module=ScaleKernel(hierarchical.matern52(d)),     # Matérn-5/2 + ARD
                             input_transform=Normalize(d, bounds=bounds), outcome_transform=Standardize(1))
        _fit(m)
        models.append(m)
    return ModelListGP(*models), tx, ty, bounds


def _constraint_callables(camp: Campaign, n_obj: int) -> list:
    """Restrições no formato do BoTorch: callable(Z) ≤ 0 ⇔ viável (Z = amostras de todos os desfechos)."""
    fs = []
    for j, (lo, hi) in enumerate(camp.cons.values()):
        k = n_obj + j
        if hi is not None:
            fs.append(lambda Z, k=k, hi=hi: Z[..., k] - hi)
        if lo is not None:
            fs.append(lambda Z, k=k, lo=lo: lo - Z[..., k])
    return fs


def _acq(model, tx, ty, name: str, camp: Campaign | None = None):
    from botorch.acquisition.multi_objective import qNoisyExpectedHypervolumeImprovement
    from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
    from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
    span = (ty.max(0).values - ty.min(0).values).clamp_min(1e-6)
    ref = ty.min(0).values - 0.1 * span
    cls = qNoisyExpectedHypervolumeImprovement if name == "qnehvi" else qLogNoisyExpectedHypervolumeImprovement
    kw = {}
    if camp is not None and camp.cons:
        n_obj = ty.shape[1]
        kw = {"objective": IdentityMCMultiOutputObjective(outcomes=list(range(n_obj))),
              "constraints": _constraint_callables(camp, n_obj)}
    return cls(model, ref_point=ref, X_baseline=tx, prune_baseline=True, **kw), ref


def propose(camp: Campaign, space: dict, q: int = 4, fixed: dict | None = None, acq: str | None = None,
            novelty_w: float | None = None, seed: int = 0, lab: str | None = None) -> pd.DataFrame:
    import torch
    from botorch.optim import optimize_acqf
    from torch.quasirandom import SobolEngine

    acq = acq or default_acq()
    if acq == "auto":
        acq = noise_check(lab, space, camp=camp)["recommended_acq"] if lab else "qnehvi"
    torch.manual_seed(seed)
    model, tx, ty, bounds = build_model(camp, space)
    af, ref = _acq(model, tx, ty, acq, camp)
    cols = list(camp.X.columns)
    fixed_idx = {cols.index(k): float(v) for k, v in (fixed or {}).items() if k in cols}
    if camp.task_col and cols.index(camp.task_col) not in fixed_idx:
        raise ValueError("braço 'batch': a tarefa (lote) precisa ser fixada — use fixed_context(..., batch=...)")
    if novelty_w is not None and not 0.0 <= novelty_w <= 1.0:
        raise ValueError("novelty_w deve estar entre 0 e 1")
    def pool_select(w: float) -> "torch.Tensor":
        """Seleção sobre 2048 candidatos Sobol: escore = w·a + (1−w)·n (novelty-aware, Aqeeli et al. 2026)."""
        pool = bounds[0] + (bounds[1] - bounds[0]) * SobolEngine(len(cols), scramble=True, seed=seed).draw(2048).double()
        for j, v in fixed_idx.items():
            pool[:, j] = v
        with torch.no_grad():
            a = torch.cat([af(pool[i:i + 256].unsqueeze(1)) for i in range(0, len(pool), 256)])
        a = torch.nan_to_num(a, nan=-1e9)
        free = [j for j in range(len(cols)) if j not in fixed_idx]
        scale = (bounds[1] - bounds[0]).clamp_min(1e-9)
        norm = lambda z: ((z - bounds[0]) / scale)[:, free]          # noqa: E731
        ref_pts, chosen = norm(tx), []
        a_n = (a - a.min()) / (a.max() - a.min() + 1e-12)
        for _ in range(q):
            nov = torch.cdist(norm(pool), ref_pts).min(1).values
            n_n = (nov - nov.min()) / (nov.max() - nov.min() + 1e-12)
            score = w * a_n + (1 - w) * n_n
            if chosen:
                score[chosen] = -np.inf
            k = int(torch.argmax(score))
            chosen.append(k)
            ref_pts = torch.cat([ref_pts, norm(pool[k:k + 1])])
        return pool[chosen]

    if novelty_w is not None:
        cand = pool_select(novelty_w)
    else:
        cand = None
        for attempt in range(3):   # gradientes NaN ocasionais na otimização da aquisição: tenta de novo
            try:
                with torch.random.fork_rng():
                    torch.manual_seed(seed + 101 * attempt)
                    cand, _ = optimize_acqf(af, bounds, q=q, num_restarts=8 + 4 * attempt, raw_samples=256,
                                            fixed_features=fixed_idx or None, sequential=True)
                break
            except (RuntimeError, ValueError) as exc:   # OptimizationGradientError é RuntimeError
                warnings.warn(f"otimização da aquisição falhou ({type(exc).__name__}); nova tentativa")
        if cand is None:
            warnings.warn("usando seleção sobre conjunto Sobol (sem gradiente)")
            cand = pool_select(0.95)
    with torch.no_grad():
        post = model.posterior(cand)
    res = pd.DataFrame(cand.numpy(), columns=cols)
    for i, name in enumerate(camp.objs.index):
        col, mu, sd = camp.to_original(name, post.mean[:, i].numpy(), post.variance[:, i].clamp_min(0).sqrt().numpy())
        res[col] = mu
        res[col.replace("pred_", "pred_sd_", 1)] = sd
    if camp.cons:
        from scipy.stats import norm
        n_obj, pf = len(camp.objs), np.ones(len(res))
        for j, (name, (lo, hi)) in enumerate(camp.cons.items()):
            mu = post.mean[:, n_obj + j].numpy()
            sd = post.variance[:, n_obj + j].clamp_min(1e-12).sqrt().numpy()
            p = norm.cdf((hi - mu) / sd) if hi is not None else np.ones_like(mu)
            p = p - (norm.cdf((lo - mu) / sd) if lo is not None else 0.0)
            res[f"pred_{name}"], res[f"pred_sd_{name}"], res[f"p_feasible_{name}"] = mu, sd, p
            pf = pf * p
        res["p_feasible"] = pf
    res.attrs["ref_point"] = ref.numpy()
    res.attrs["acq"] = acq
    return res


def hypervolume(Y: np.ndarray, ref: np.ndarray) -> float:
    import torch
    from botorch.utils.multi_objective.box_decompositions.dominated import DominatedPartitioning
    bd = DominatedPartitioning(ref_point=torch.tensor(ref, dtype=torch.double), Y=torch.tensor(Y, dtype=torch.double))
    return float(bd.compute_hypervolume())


def proposals_to_syntheses(cands: pd.DataFrame, space: dict, batch: str | None, campaign: str, iteration: int,
                           method: str = "in_situ_reduction_on_GO", lots: dict | None = None, seed: int = 0,
                           hardware: str = "", arm: str | None = None) -> pd.DataFrame:
    """Linhas de aunp_syntheses; ordem de execução aleatorizada dentro do bloco da rodada (§4.11)."""
    cols = _syn_columns()
    order = np.random.default_rng(seed + iteration).permutation(len(cands)) + 1
    rows = []
    for k, r in cands.reset_index(drop=True).iterrows():
        row = {c: "" for c in cols}
        row.update({"synthesis_id": f"{campaign}-it{iteration:02d}-{k + 1:02d}", "go_batch_id": batch or "",
                    "method": method, "campaign_id": campaign,
                    "design_id": (f"{arm}{ARM_SEP}" if arm else "") + f"it{iteration:02d}-q{k + 1}",
                    "fidelity": "high", "block": f"{campaign}-it{iteration:02d}", "run_order": int(order[k]),
                    "status": "planned", "hardware": hardware, "notes": "proposta do AuNP Designer"})
        for role, lot in (lots or {}).items():
            if role in LOT_ROLES:
                row[LOT_ROLES[role]] = lot
        for v in space:
            row[v] = round(float(r[v]), 4)
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def fixed_context(lab: str, camp: Campaign, batch: str | None, lots: dict | None) -> dict:
    """Valores de contexto fixos na otimização (lote-alvo, lotes de reagente). Erros explícitos quando o braço não
    consegue representar o lote pedido — senão a aquisição otimizaria um "lote fictício"."""
    fixed = {}
    if camp.representation == "hierarchical":
        bm = camp.level_maps["lvl_batch"]
        fixed["lvl_batch"] = float(bm.get(str(batch), max(bm.values(), default=-1) + 1))   # lote novo: id inédito
        if "lvl_supplier" in camp.level_maps:
            sm = camp.level_maps["lvl_supplier"]
            sup = _suppliers(lab).get(str(batch), "desconhecido")
            fixed["lvl_supplier"] = float(sm.get(sup, max(sm.values(), default=-1) + 1))
        return fixed
    if camp.representation == "batch":
        if batch not in camp.task_map:
            raise ValueError(f"braço 'batch' (identidade do lote) só propõe para lotes já sintetizados "
                             f"{sorted(camp.task_map)}; para um lote novo ({batch!r}) use 'go' ou 'go+impurities'")
        fixed["task"] = camp.task_map[batch]
    ctx_cols = [c for c in camp.X.columns if c.startswith("ctx_")]
    if ctx_cols:
        z = standardized_context(lab)
        if not batch or batch not in z.index:
            raise ValueError(f"informe --batch com um lote que tenha descritores ({sorted(z.index)}); "
                             f"recebido {batch!r}")
        fixed.update({f"ctx_{c}": float(v) for c, v in z.loc[batch].items() if f"ctx_{c}" in camp.X.columns})
    if camp.representation == "go+impurities":
        imp_cols = [c for c in camp.X.columns if c.startswith("imp_")]
        fixed.update(impurity_values_for_lots(lab, lots or {}, camp.X[imp_cols]))
    return fixed


# ---------------------------------------------------------------------------------------------- validação LBO

def validate_lbo(lab: str, space: dict, representations=REPRESENTATIONS, log_objectives=(), eps=1e-3) -> pd.DataFrame:
    """Leave-one-batch-out: treina sem um lote e prevê as sínteses dele (generalização para lote novo)."""
    import torch
    rows = []
    for rep in representations:
        camp = load_campaign(lab, space, rep, log_objectives, eps)
        lvl = list(camp.X.columns).index("lvl_batch") if "lvl_batch" in camp.X.columns else None
        for b in sorted(camp.batches.unique()):
            test = np.where(camp.batches.to_numpy() == b)[0]
            train = np.where(camp.batches.to_numpy() != b)[0]
            if len(test) < 2 or len(train) < 4:
                continue
            if rep == "batch":
                rows.append({"representation": rep, "held_out_batch": b, "objective": "*", "n": len(test),
                             "rmse": np.nan, "coverage95": np.nan,
                             "note": "identidade do lote não generaliza para lote não visto"})
                continue
            model, *_ = build_model(camp, space, rows=train)
            Xt = camp.X.to_numpy(float)[test].copy()
            if lvl is not None:          # o lote retirado vira um rótulo inédito (não vaza a identidade aprendida)
                Xt[:, lvl] = camp.X.iloc[:, lvl].max() + 1
            tx = torch.tensor(Xt, dtype=torch.double)
            with torch.no_grad():
                post = model.posterior(tx)
            for i, name in enumerate(camp.objs.index):
                y = camp.Y[test, i]
                mu = post.mean[:, i].numpy()
                sd = post.variance[:, i].clamp_min(0).sqrt().numpy()
                if camp.Yvar[i] is None:   # ruído inferido: está na escala padronizada do GP
                    m_i = model.models[i]
                    noise = float(m_i.likelihood.noise.detach().mean()) * float(m_i.outcome_transform.stdvs.detach() ** 2)
                else:                      # ruído medido: já na escala do objetivo
                    noise = camp.Yvar[i][test]
                sd_obs = np.sqrt(sd ** 2 + noise)
                rows.append({"representation": rep, "held_out_batch": b, "objective": name, "n": len(test),
                             "rmse": float(np.sqrt(np.mean((y - mu) ** 2))),
                             "coverage95": float(np.mean(np.abs(y - mu) <= 1.96 * sd_obs)), "note": ""})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- ruído

def noise_check(lab: str, space: dict, camp: Campaign | None = None, alpha: float | None = None,
                representation: str = "recipe") -> dict:
    """Há ruído heteroscedástico COMPROVADO? (regra da proposta para usar qLogNEHVI, §4.5)

    Dois testes por objetivo, na escala do modelo, com correção de Holm entre todos:
      * Brown–Forsythe (Levene com mediana) entre grupos de preparações repetidas (mesma receita e lote, ≥ 2 cada) —
        o piloto foi desenhado para isso;
      * Breusch–Pagan: os resíduos² do GP dependem das variáveis de entrada?
    Sem grupos repetidos suficientes, só o Breusch–Pagan entra. Recomenda qLogNEHVI se algum p ajustado < α."""
    from statsmodels.stats.diagnostic import het_breuschpagan
    from scipy.stats import levene
    import torch
    alpha = float(alpha if alpha is not None else
                  (_PREREG or {}).get("acquisition", {}).get("heteroscedasticity_alpha", 0.05))
    camp = camp or load_campaign(lab, space, representation, default_logs(), default_eps())
    syn = usable_syntheses(lab).set_index("synthesis_id").loc[camp.X.index]
    key = syn["go_batch_id"].fillna("none").astype(str) + "|" + syn[list(space)].round(4).astype(str).agg("|".join, axis=1)
    model, tx, ty, _ = build_model(camp, space)
    with torch.no_grad():
        mu = model.posterior(tx).mean.numpy()
    pv, details = {}, {}
    Xc = (camp.X[list(space)] - camp.X[list(space)].mean()) / camp.X[list(space)].std(ddof=0).replace(0, 1)
    exog = np.column_stack([np.ones(len(Xc)), Xc.to_numpy(float)])
    for i, name in enumerate(camp.objs.index):
        y = camp.Y[:, i]
        groups = [y[(key == k).to_numpy()] for k in key.unique() if (key == k).sum() >= 2]
        d = {"n_replicate_groups": len(groups)}
        if len(groups) >= 2:
            d["brown_forsythe_p"] = float(levene(*groups, center="median").pvalue)
            pv[f"{name}:brown_forsythe"] = d["brown_forsythe_p"]
        if len(y) > exog.shape[1] + 2:
            r2 = (y - mu[:, i]) ** 2
            d["breusch_pagan_p"] = float(het_breuschpagan(y - mu[:, i], exog)[1]) if np.std(r2) > 0 else 1.0
            pv[f"{name}:breusch_pagan"] = d["breusch_pagan_p"]
        if camp.Yvar[i] is not None:
            v = camp.Yvar[i]
            d["measured_variance_ratio_max_min"] = float(v.max() / max(v.min(), 1e-300))
        details[name] = d
    from stats import holm
    adj = holm(pv) if pv else {}
    hetero = any(p < alpha for p in adj.values())
    return {"alpha": alpha, "p_holm": adj, "details": details, "heteroscedastic": hetero,
            "recommended_acq": "qlognehvi" if hetero else "qnehvi",
            "rule": "qLogNEHVI só com ruído heteroscedástico comprovado (proposta, §4.5)"}


# ---------------------------------------------------------------------------------------------- SHAP

def explain(lab: str, space: dict, representation: str = "go", n_boot: int = 5, log_objectives=(), seed: int = 0):
    """Importância SHAP (média de |SHAP| sobre a média posterior do GP) e estabilidade por bootstrap (Spearman)."""
    import shap
    import torch
    from scipy.stats import spearmanr
    camp = load_campaign(lab, space, representation, log_objectives)
    rng = np.random.default_rng(seed)
    X = camp.X.to_numpy(float)

    def importances(rows):
        model, *_ = build_model(camp, space, rows=rows)
        out = {}
        for i, name in enumerate(camp.objs.index):
            f = lambda z, i=i: model.models[i].posterior(torch.tensor(z, dtype=torch.double)).mean.detach().numpy().ravel()  # noqa: E731
            bg = shap.sample(X[rows], min(10, len(rows)), random_state=seed)   # amostras reais (tarefa inteira)
            sv = shap.KernelExplainer(f, bg).shap_values(X[rows], nsamples=200, silent=True)
            out[name] = np.abs(sv).mean(0)
        return out
    full = importances(np.arange(len(X)))
    stab = {name: [] for name in full}
    for _ in range(n_boot):
        rows = rng.choice(len(X), len(X), replace=True)
        for name, imp in importances(np.unique(rows)).items():
            stab[name].append(spearmanr(full[name], imp).statistic)
    table = []
    for name, imp in full.items():
        for c, v in zip(camp.X.columns, imp):
            table.append({"objective": name, "feature": c, "mean_abs_shap": float(v)})
        table.append({"objective": name, "feature": "_estabilidade_spearman_bootstrap",
                      "mean_abs_shap": float(np.nanmean(stab[name])) if stab[name] else np.nan})
    return pd.DataFrame(table)


def h_statistic(f, X: np.ndarray, j: int, k: int) -> float:
    """H² de Friedman & Popescu (2008) para o par (j, k): fração da variância da dependência parcial conjunta que não
    é soma das dependências individuais (0 = aditivo; 1 = só interação). Médias sobre os próprios dados."""
    n = len(X)

    def pd_at(cols):
        out = np.empty(n)
        for i in range(n):
            Z = X.copy()
            Z[:, cols] = X[i, cols]
            out[i] = f(Z).mean()
        return out - out.mean()
    pj, pk, pjk = pd_at([j]), pd_at([k]), pd_at([j, k])
    den = np.sum(pjk ** 2)
    return float(np.sum((pjk - pj - pk) ** 2) / den) if den > 0 else 0.0


def interactions(lab: str, space: dict, representation: str = "go", top: int = 5, n_boot: int = 3,
                 log_objectives=(), seed: int = 0, max_rows: int = 60) -> pd.DataFrame:
    """Interações (§4.13) entre as `top` variáveis de maior efeito principal, pelo H² de Friedman na média a
    posteriori do GP de cada objetivo, com média ± sd por bootstrap (estabilidade). Explicação do MODELO, não causal."""
    import torch
    camp = load_campaign(lab, space, representation, log_objectives)
    rng = np.random.default_rng(seed)
    X = camp.X.to_numpy(float)
    cols = list(camp.X.columns)
    free = [i for i, c in enumerate(cols) if X[:, i].std() > 0]

    def run(rows):
        model, *_ = build_model(camp, space, rows=rows)
        Xs = X[rows][: max_rows]
        res = {}
        for o, name in enumerate(camp.objs.index):
            f = lambda z, o=o: model.models[o].posterior(torch.tensor(z, dtype=torch.double)).mean.detach().numpy().ravel()  # noqa: E731
            main = {j: np.var([f(np.where(np.arange(len(cols)) == j, xi, Xs)).mean() for xi in Xs[:, j]]) for j in free}
            keep = sorted(main, key=main.get, reverse=True)[:top]
            for a_, b_ in itertools.combinations(sorted(keep), 2):
                res[(name, cols[a_], cols[b_])] = h_statistic(f, Xs, a_, b_)
        return res
    full = run(np.arange(len(X)))
    boots = [run(np.unique(rng.choice(len(X), len(X), replace=True))) for _ in range(n_boot)]
    rows = []
    for key, h in full.items():
        bs = [b[key] for b in boots if key in b]
        rows.append({"objective": key[0], "feature_a": key[1], "feature_b": key[2], "H2": h,
                     "H2_boot_mean": float(np.mean(bs)) if bs else np.nan,
                     "H2_boot_sd": float(np.std(bs, ddof=1)) if len(bs) > 1 else np.nan,
                     "boot_presence": len(bs) / max(n_boot, 1)})
    return pd.DataFrame(rows).sort_values(["objective", "H2"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- proveniência

def run_metadata(args: dict, lab: str | None) -> dict:
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""
    meta = {"timestamp": datetime.now().isoformat(timespec="seconds"), "git_commit": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain", "--", "code", "tools")), "args": args,
            "python": sys.version.split()[0]}
    for pkg in ("torch", "botorch", "gpytorch", "numpy", "pandas"):
        try:
            meta[pkg] = __import__(pkg).__version__
        except Exception:  # noqa: BLE001
            pass
    if lab and os.path.isdir(lab):
        meta["input_sha256"] = {f: hashlib.sha256(open(os.path.join(lab, f), "rb").read()).hexdigest()
                                for f in sorted(os.listdir(lab)) if f.endswith(".csv")}
    return meta


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


# ---------------------------------------------------------------------------------------------- demonstração

def demo(out_dir: str, iterations: int, q: int, seed: int, representation: str = "go+impurities",
         acq: str | None = None) -> dict:
    """Laço completo com o laboratório SIMULADO: 12 sínteses iniciais (4 receitas × L1–L3, como na proposta) e
    rodadas adaptativas alternando o lote-alvo. Dados SIMULADOS, gravados em out_dir/lab."""
    from scipy.stats import qmc
    import sim_lab
    rng = np.random.default_rng(seed)
    lab = os.path.join(out_dir, "lab")
    sim_lab.init_lab(lab, seed=seed)
    acq = acq or default_acq()
    print(f"DEMONSTRAÇÃO com dados SIMULADOS em {os.path.relpath(lab, ROOT)} — braço {representation}, {acq}")
    space = DEFAULT_SPACE
    lo, hi = np.array([v[0] for v in space.values()]), np.array([v[1] for v in space.values()])
    recipes = pd.DataFrame(qmc.scale(qmc.LatinHypercube(len(space), seed=seed).random(4), lo, hi), columns=list(space))
    for b in ("L1", "L2", "L3"):
        sim_lab.run_syntheses(lab, proposals_to_syntheses(recipes, space, b, f"INIT-{b}", 0, seed=seed).assign(
            status="done"), rng)
    logs = default_logs() or ("spectral_loss_J",)
    history = []
    for it in range(1, iterations + 1):
        target = ("L1", "L2", "L3")[(it - 1) % 3]
        camp = load_campaign(lab, space, representation, logs, default_eps(), constraints=default_constraints())
        lots = {"reductant": "RED-A"}
        cands = propose(camp, space, q=q, fixed=fixed_context(lab, camp, target, lots), acq=acq, seed=seed + it,
                        lab=lab)
        syn = proposals_to_syntheses(cands, space, target, "DEMO", it, lots=lots, seed=seed).assign(status="done")
        res = sim_lab.run_syntheses(lab, syn, rng)
        allres = pd.read_csv(os.path.join(lab, "outcomes.csv")).pivot_table(index="synthesis_id", columns="objective",
                                                                            values="value")
        syn_all = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv")).set_index("synthesis_id")["go_batch_id"]
        per_batch = allres["spectral_loss_J"].groupby(syn_all.reindex(allres.index)).min()
        history.append({"iteration": it, "target": target, "best_J_target": float(per_batch[target]),
                        "best_J_mean_batches": float(per_batch.mean()), "new_J": float(res["spectral_loss_J"].min())})
        print(f"  rodada {it} (lote {target}): melhor J no lote {per_batch[target]:7.3f} | média dos lotes "
              f"{per_batch.mean():7.3f} | J da rodada {res['spectral_loss_J'].round(2).tolist()} | "
              f"tamanho {res['size_mean_nm'].round(1).tolist()} nm")
    import lab_data_model
    if lab_data_model.validate(lab):
        raise SystemExit("tabelas geradas não passaram no validador")
    json.dump(run_metadata({"cmd": "demo", "iterations": iterations, "q": q, "seed": seed,
                            "representation": representation, "acq": acq}, lab),
              open(os.path.join(out_dir, "run_metadata.json"), "w"), indent=1)
    return {"history": history}


# ---------------------------------------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("lab_dir")
        p.add_argument("--space", help="JSON {variável: [mín, máx]} (padrão: pré-registro)")
        p.add_argument("--log-objectives", nargs="*", default=None,
                       help="objetivos modelados como log(y + ε) (padrão: os marcados `log` no pré-registro)")
        p.add_argument("--eps", type=float, default=None, help="ε de log(J + ε) (padrão: pré-registro)")
        p.add_argument("--no-constraints", action="store_true", help="ignora as restrições do pré-registro")
    p = sub.add_parser("propose", help="próxima rodada a partir de uma pasta de dados de laboratório")
    common(p)
    p.add_argument("--batch", help="lote de GO-alvo (contexto fixo)")
    p.add_argument("--representation", choices=REPRESENTATIONS, default="go")
    p.add_argument("--acq", choices=["qnehvi", "qlognehvi", "auto"], default=None,
                   help="padrão: pré-registro (qnehvi); auto = qLogNEHVI só se o noise-check comprovar heteroscedasticidade")
    p.add_argument("--novelty-w", type=float, help="peso w do escore novelty-aware (0–1); omitido = só aquisição")
    p.add_argument("--lot", action="append", default=[], help="lote a usar na rodada: papel=lote (gold|reductant|stabilizer)")
    p.add_argument("--q", type=int, default=4)
    p.add_argument("--arm", help="braço da comparação prospectiva (ex.: recipe, go+impurities): treina só com os dados "
                                 "compartilhados + as rodadas desse braço e marca o design_id")
    p.add_argument("--campaign", default="CAMP")
    p.add_argument("--iteration", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", help="CSV de saída (padrão: outputs/aunp_designer/proposals_<data>.csv)")
    v = sub.add_parser("validate", help="leave-one-batch-out dos braços")
    common(v)
    v.add_argument("--representations", nargs="*", default=list(REPRESENTATIONS))
    e = sub.add_parser("explain", help="SHAP + estabilidade por bootstrap")
    common(e)
    e.add_argument("--representation", choices=REPRESENTATIONS, default="go")
    e.add_argument("--n-boot", type=int, default=5)
    e.add_argument("--interactions", action="store_true", help="também o H² de Friedman entre as variáveis principais")
    nc = sub.add_parser("noise-check", help="heteroscedasticidade comprovada? (escolha qNEHVI × qLogNEHVI)")
    common(nc)
    nc.add_argument("--representation", choices=REPRESENTATIONS, default="recipe")
    sub.add_parser("literature", help="faixas de condições na semente da literatura")
    dm = sub.add_parser("demo", help="laço completo com laboratório SIMULADO")
    dm.add_argument("--iterations", type=int, default=6)
    dm.add_argument("--q", type=int, default=2)
    dm.add_argument("--seed", type=int, default=0)
    dm.add_argument("--representation", choices=REPRESENTATIONS, default="go+impurities")
    dm.add_argument("--acq", choices=["qnehvi", "qlognehvi", "auto"], default=None)
    dm.add_argument("--out", default=os.path.join(ROOT, "outputs", "aunp_designer_demo"))
    a = ap.parse_args()

    if a.cmd == "literature":
        return literature_summary()
    if a.cmd == "demo":
        demo(a.out, a.iterations, a.q, a.seed, a.representation, a.acq)
        return
    space = json.load(open(a.space)) if a.space else DEFAULT_SPACE
    a.log_objectives = default_logs() if a.log_objectives is None else tuple(a.log_objectives)
    a.eps = default_eps() if a.eps is None else a.eps
    cons = {} if a.no_constraints else default_constraints()
    prereg.guard(f"designer.py {a.cmd}") if _PREREG else None
    outdir = os.path.join(ROOT, "outputs", "aunp_designer")
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if a.cmd == "validate":
        res = validate_lbo(a.lab_dir, space, a.representations, a.log_objectives, a.eps)
        path = os.path.join(outdir, f"lbo_{stamp}.csv")
        res.to_csv(path, index=False)
        print(res.groupby(["representation", "objective"])[["rmse", "coverage95"]].mean().round(3).to_string())
        print(f"-> {os.path.relpath(path, ROOT)}")
    elif a.cmd == "noise-check":
        res = noise_check(a.lab_dir, space, representation=a.representation)
        print(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    elif a.cmd == "explain":
        res = explain(a.lab_dir, space, a.representation, a.n_boot, a.log_objectives)
        path = os.path.join(outdir, f"shap_{stamp}.csv")
        res.to_csv(path, index=False)
        print(res.sort_values(["objective", "mean_abs_shap"], ascending=[True, False]).to_string(index=False))
        print(f"-> {os.path.relpath(path, ROOT)}")
        if a.interactions:
            it = interactions(a.lab_dir, space, a.representation, n_boot=a.n_boot, log_objectives=a.log_objectives)
            p2 = os.path.join(outdir, f"interactions_{stamp}.csv")
            it.to_csv(p2, index=False)
            print(it.round(3).to_string(index=False))
            print(f"-> {os.path.relpath(p2, ROOT)}")
    else:
        lots = {}
        for x in a.lot:
            role, sep, lot = x.partition("=")
            if not sep or role not in LOT_ROLES:
                ap.error(f"--lot {x!r}: use papel=lote, papel ∈ {sorted(LOT_ROLES)}")
            lots[role] = lot
        arm = a.arm or None
        if arm and a.representation != arm and arm in REPRESENTATIONS:
            ap.error(f"--arm {arm} usa a representação {arm}; não combine com --representation {a.representation}")
        rep = arm if arm in REPRESENTATIONS else a.representation
        camp = load_campaign(a.lab_dir, space, rep, a.log_objectives, a.eps, constraints=cons, arm=arm)
        print(f"{len(camp.X)} sínteses{f' (braço {arm}: compartilhadas + as suas)' if arm else ''}; objetivos: {dict(camp.objs['direction'])}; restrições: {camp.cons}; "
              f"entradas: {list(camp.X.columns)}; "
              f"ruído medido: {[n for n, v in zip(camp.objs.index, camp.Yvar) if v is not None] or 'nenhum'}")
        fixed = fixed_context(a.lab_dir, camp, a.batch, lots)
        cands = propose(camp, space, q=a.q, fixed=fixed, acq=a.acq, novelty_w=a.novelty_w, seed=a.seed, lab=a.lab_dir)
        print(f"aquisição: {cands.attrs.get('acq')}")
        syn = proposals_to_syntheses(cands, space, a.batch, a.campaign, a.iteration, lots=lots, seed=a.seed, arm=arm)
        out = a.out or os.path.join(outdir, f"proposals_{date.today()}.csv")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        syn.to_csv(out, index=False)
        json.dump(run_metadata(vars(a), a.lab_dir), open(os.path.splitext(out)[0] + "_run_metadata.json", "w"), indent=1)
        print(pd.concat([syn[["synthesis_id", "run_order"] + list(space)],
                         cands.filter(like="pred_").round(3)], axis=1).to_string(index=False))
        print(f"-> {os.path.relpath(out, ROOT)} (+ _run_metadata.json); complete os lotes antes de copiar para "
              f"aunp_syntheses.csv")


if __name__ == "__main__":
    main()
