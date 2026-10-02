#!/usr/bin/env python3
"""Valor da informação: vale caracterizar um lote NOVO de GO antes de sintetizar? (EVPI/EVSI, §4.14, Objetivo 6)

Decisão: escolher a receita a (de um conjunto candidato A) para o lote novo. Utilidade U(a, θ) = média a posteriori do
objetivo primário, na escala do modelo (maximização; log se pré-registrado), prevista pelo braço 'go' do AuNP Designer
com o contexto θ (descritores do lote padronizados entre lotes: C/O, ID/IG, razões de FTIR, d001…).
Antes de caracterizar, θ é desconhecido: prior N(0, Σ₀) em z (Σ₀ = correlação empírica entre lotes encolhida para I —
com poucos lotes, Σ₀ ≈ I).

    EVPI    = E_θ[max_a U(a, θ)] − max_a E_θ[U(a, θ)]                  (teto: o que valeria saber θ exatamente)
    EVSI(T) = E_m[max_a E_{θ|m} U(a, θ)] − max_a E_θ[U(a, θ)]          (o que vale medir com o conjunto de técnicas T)
    m = θ_T + ε, ε ~ N(0, σ_T²); σ_T = desvio DENTRO do lote ÷ desvio ENTRE lotes (de go_descriptors), ou o padrão.
Monte Carlo com pesos de importância: θ_i ~ prior (N amostras) e U (|A| × N) calculado UMA vez; para cada medida
simulada m_k (θ_k novo do prior + ruído), w_i ∝ N(m_k; θ_i,T, σ_T²) e E_{θ|m}U(a, θ) ≈ Σ_i w_i U(a, θ_i). O tamanho
efetivo de amostra (ESS) médio é reportado; se ficar pequeno, aumente --prior-samples.

Decisão econômica: para cada SUBCONJUNTO de técnicas (enumeração exaustiva, 2^k), valor líquido =
EVSI(T)·v − custo(T), com v = sustainability.value_per_unit_information (pré-registrado) e custos em
value_of_information.technique_costs. Recomenda o subconjunto de maior valor líquido (pode ser "nenhuma").
A saída traz `evsi_all_techniques` e `expected_sd_reduction_all`, lidas por
`code/sustainability/metrics.py from-lab --voi` (CPU incremental da caracterização adicional).

Uso:
    python code/decision/voi.py datasets/lab [--objective spectral_loss_J] [--out outputs/voi.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
for _sub in ("aunp_designer", "campaign", "go_navigator"):
    sys.path.insert(0, os.path.join(HERE, "..", _sub))

# técnica que mede cada descritor, quando go_characterization não informa
DESCRIPTOR_TECHNIQUE = {"C_O_ratio": "XPS", "sp2_fraction": "XPS", "C-O_fraction": "XPS", "C=O_fraction": "XPS",
                        "O-C=O_fraction": "XPS", "ID_IG": "Raman", "I2D_IG": "Raman", "La_nm": "Raman",
                        "d001_nm": "XRD", "Lc_nm": "XRD", "n_layers": "XRD", "frac_graphitic": "XRD",
                        "thickness_nm": "AFM", "lateral_size_um": "AFM", "mass_loss_pct": "TGA",
                        "hydrodynamic_nm": "DLS"}


# ---------------------------------------------------------------------------------------------- núcleo (genérico)

def evpi(U: np.ndarray) -> float:
    """U: (n_ações × N amostras do prior). Estimador de diferenças: média de max_a U(a, θ_i) − U(a₀, θ_i) ≥ 0."""
    a0 = int(np.argmax(U.mean(axis=1)))
    return float((U.max(axis=0) - U[a0]).mean())


def evsi(U: np.ndarray, theta: np.ndarray, obs: list[int], noise_sd: np.ndarray, prior_sampler,
         n_outer: int = 400, rng: np.random.Generator | None = None) -> dict:
    """EVSI de medir as dimensões `obs` de θ com desvio `noise_sd[obs]`, por pesos de importância sobre as amostras
    `theta` (N × p) do prior; `prior_sampler(k)` gera k amostras NOVAS do prior (os "lotes verdadeiros")."""
    rng = rng or np.random.default_rng(0)
    mean_u = U.mean(axis=1)
    a0 = int(np.argmax(mean_u))
    sd_prior = float(U[a0].std())
    if not obs:
        return {"evsi": 0.0, "evsi_se": 0.0, "ess_mean": float(U.shape[1]), "sd_prior": sd_prior, "sd_post": sd_prior,
                "p_change_decision": 0.0}
    obs = list(obs)
    true = prior_sampler(n_outer)[:, obs]
    m = true + rng.normal(0.0, 1.0, true.shape) * noise_sd[obs]
    ll = -0.5 * (((m[:, None, :] - theta[None, :, obs]) / noise_sd[obs]) ** 2).sum(-1)   # (K × N)
    w = np.exp(ll - ll.max(axis=1, keepdims=True))
    w /= w.sum(axis=1, keepdims=True)
    post = w @ U.T                                       # (K × ações): E[U(a, θ) | m_k]
    best = post.argmax(axis=1)
    # estimador de diferenças: E_m[E[U(a₀)|m]] = E[U(a₀)] (torre), então cada termo max_a E[U|m] − E[U(a₀)|m] ≥ 0
    # estima o EVSI sem o ruído de comparar com a média a priori (variância muito menor, nunca negativo)
    gain = post.max(axis=1) - post[:, a0]
    val = float(gain.mean())
    u_best = U[best]                                     # (K × N)
    var_post = np.einsum("kn,kn->k", w, (u_best - post[np.arange(len(best)), best][:, None]) ** 2)
    return {"evsi": val, "evsi_se": float(gain.std(ddof=1) / np.sqrt(len(gain))),
            "ess_mean": float(np.mean(1.0 / (w ** 2).sum(axis=1))), "sd_prior": sd_prior,
            "sd_post": float(np.sqrt(np.maximum(var_post, 0)).mean()), "p_change_decision": float(np.mean(best != a0))}


def gaussian_prior(cov: np.ndarray, rng: np.random.Generator):
    L = np.linalg.cholesky(cov + 1e-9 * np.eye(len(cov)))
    return lambda k: rng.normal(size=(k, len(cov))) @ L.T


def best_subset(values: dict[tuple, float], costs: dict[str, float], v: float) -> list[dict]:
    """Ordena subconjuntos de técnicas por valor líquido EVSI·v − custo."""
    rows = [{"techniques": list(T), "evsi": e, "value": e * v, "cost": sum(costs.get(t, 0.0) for t in T),
             "net_value": e * v - sum(costs.get(t, 0.0) for t in T)} for T, e in values.items()]
    return sorted(rows, key=lambda r: -r["net_value"])


# ---------------------------------------------------------------------------------------------- integração com o lab

def context_structure(lab: str, ctx_cols: list[str], default_noise_z: float) -> tuple[dict, np.ndarray, np.ndarray]:
    """-> ({técnica: [índices de ctx]}, ruído em z por descritor, Σ₀ do prior em z)."""
    from batch_descriptors import batch_matrix
    desc = [c[len("ctx_"):] for c in ctx_cols]
    mean, sd = batch_matrix(lab, desc)
    between = mean.std(ddof=0).replace(0, np.nan)
    noise = (sd.median() / between).reindex(desc).fillna(default_noise_z).clip(0.02, 5.0).to_numpy(float)
    tech = dict(DESCRIPTOR_TECHNIQUE)
    p = os.path.join(lab, "go_characterization.csv")
    if os.path.exists(p):
        gc = pd.read_csv(p)
        tech.update(gc.dropna(subset=["quantity", "technique"]).groupby("quantity")["technique"].first().to_dict())
    groups: dict[str, list[int]] = {}
    for i, d in enumerate(desc):
        groups.setdefault(tech.get(d, "other"), []).append(i)
    z = ((mean - mean.mean()) / mean.std(ddof=0).replace(0, 1)).fillna(0.0).to_numpy(float)
    k = len(desc)
    if z.shape[0] > k + 1:
        alpha = min(1.0, (k + 1) / z.shape[0])
        cov = (1 - alpha) * np.corrcoef(z.T) + alpha * np.eye(k)
    else:
        cov = np.eye(k)                                  # poucos lotes: descritores independentes a priori
    return groups, noise, cov


def utility_matrix(lab: str, objective: str | None = None, n_actions: int = 128, n_prior: int = 2000,
                   seed: int = 0, representation: str = "go") -> dict:
    """Ajusta o braço 'go' e calcula U(a, θ_i) para receitas Sobol × amostras do prior do lote novo."""
    import torch
    from scipy.stats import qmc
    import designer
    import prereg
    cfg = prereg.load()
    vcfg = cfg.get("value_of_information", {})
    objective = objective or vcfg.get("objective")
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, representation, designer.default_logs(), designer.default_eps())
    ctx = [c for c in camp.X.columns if c.startswith("ctx_")]
    if not ctx:
        raise SystemExit("sem descritores de lote (go_descriptors/go_characterization com ≥ 2 lotes): "
                         "não há o que a caracterização informe")
    names = list(camp.objs.index)
    if objective not in names:
        raise SystemExit(f"objetivo {objective!r} ausente; disponíveis {names}")
    j = names.index(objective)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = designer.build_model(camp, space)[0].models[j]
    rng = np.random.default_rng(seed)
    groups, noise, cov = context_structure(lab, ctx, float(vcfg.get("default_noise_z", 0.3)))
    sampler = gaussian_prior(cov, rng)
    theta = sampler(n_prior)
    rec_cols = [c for c in camp.X.columns if c in space]
    A = qmc.Sobol(len(rec_cols), seed=seed).random(n_actions)
    lo = np.array([space[c][0] for c in rec_cols])
    hi = np.array([space[c][1] for c in rec_cols])
    A = lo + A * (hi - lo)
    other = [c for c in camp.X.columns if c not in rec_cols and c not in ctx]
    fixed = camp.X[other].median().to_numpy(float) if other else np.zeros(0)
    cols = list(camp.X.columns)
    U = np.empty((n_actions, n_prior))
    with torch.no_grad():
        for i0 in range(0, n_prior, 250):
            th = theta[i0:i0 + 250]
            X = np.empty((n_actions, len(th), len(cols)))
            X[..., [cols.index(c) for c in rec_cols]] = A[:, None, :]
            X[..., [cols.index(c) for c in ctx]] = th[None, :, :]
            if other:
                X[..., [cols.index(c) for c in other]] = fixed
            # lote de amostras do prior × q ações: a covariância fica (|A| × |A|) por amostra, não (|A|·N)²
            Xb = torch.tensor(X.transpose(1, 0, 2).copy(), dtype=torch.double)
            U[:, i0:i0 + len(th)] = model.posterior(Xb).mean.squeeze(-1).numpy().T
    return {"U": U, "theta": theta, "sampler": sampler, "groups": groups, "noise": noise, "ctx": ctx,
            "objective": objective, "actions": pd.DataFrame(A, columns=rec_cols), "cfg": cfg}


def analyze(lab: str, objective: str | None = None, n_actions: int = 128, n_prior: int = 2000, n_outer: int = 400,
            seed: int = 0) -> dict:
    import prereg
    um = utility_matrix(lab, objective, n_actions, n_prior, seed)
    U, theta, groups, noise, cfg = um["U"], um["theta"], um["groups"], um["noise"], um["cfg"]
    costs = {k: float(v) for k, v in cfg.get("value_of_information", {}).get("technique_costs", {}).items()}
    v = float(cfg["sustainability"]["value_per_unit_information"])
    rng = np.random.default_rng(seed + 1)
    techs = sorted(groups)
    per, values = {}, {}
    for r in range(0, len(techs) + 1):
        for T in itertools.combinations(techs, r):
            obs = sorted(i for t in T for i in groups[t])
            e = evsi(U, theta, obs, noise, um["sampler"], n_outer, rng)
            values[T] = e["evsi"]
            if len(T) == 1:
                per[T[0]] = {**e, "descriptors": [um["ctx"][i][4:] for i in obs], "cost": costs.get(T[0])}
            if len(T) == len(techs):
                e_all = e
    missing = [t for t in techs if t not in costs]
    if missing:
        warnings.warn(f"técnicas sem custo em value_of_information.technique_costs: {missing} (custo 0)")
    ranking = best_subset(values, costs, v)
    return {"objective": um["objective"], "prereg_sha256": prereg.sha256(cfg), "evpi": evpi(U),
            "evsi_by_technique": per, "evsi_all_techniques": e_all["evsi"],
            "expected_sd_reduction_all": e_all["sd_prior"] - e_all["sd_post"],
            "p_change_decision_all": e_all["p_change_decision"], "ess_mean_all": e_all["ess_mean"],
            "value_per_unit_information": v, "subsets": ranking, "recommended": ranking[0]["techniques"],
            "n_actions": n_actions, "n_prior": n_prior, "n_outer": n_outer,
            "note": "utilidade na escala do modelo (maximização; log se pré-registrado)"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--objective")
    ap.add_argument("--actions", type=int, default=128)
    ap.add_argument("--prior-samples", type=int)
    ap.add_argument("--measurement-samples", type=int)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    import prereg
    vc = prereg.load().get("value_of_information", {})
    res = analyze(a.lab, a.objective, a.actions, a.prior_samples or int(vc.get("prior_samples", 2000)),
                  a.measurement_samples or int(vc.get("measurement_samples", 400)), a.seed)
    print(f"EVPI = {res['evpi']:.4f}   EVSI(todas) = {res['evsi_all_techniques']:.4f}   "
          f"(escala do modelo de {res['objective']})")
    for t, e in res["evsi_by_technique"].items():
        print(f"  {t:8s} EVSI {e['evsi']:.4f} ± {e['evsi_se']:.4f}  ESS {e['ess_mean']:.0f}  P(muda a receita) {e['p_change_decision']:.2f}"
              f"  custo {e['cost']}")
    print("recomendado:", res["recommended"] or "nenhuma caracterização adicional",
          f"(valor líquido {res['subsets'][0]['net_value']:.1f})")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
