#!/usr/bin/env python3
"""Análise causal GO–AuNP (§4.9): DAG explícito, estimação por ajuste de backdoor (DoWhy), refutações, E-value,
ponderação por escore de propensão (IPW, com diagnóstico de balanço), mediação e descoberta exploratória (causal-learn).

O DAG abaixo codifica as hipóteses da proposta (lote/fornecedor → descritores do GO → nucleação/tamanho → espectro;
impurezas dos reagentes; receita; bloco = dia/operador; hardware → temperatura efetiva). Edite `EDGES` conforme o
conhecimento do laboratório — a estimativa só é tão boa quanto o grafo. O delineamento (randomização e blocos em
aunp_syntheses.block/run_order) é a principal proteção contra confundimento; esta análise é complementar.

Uso:
    python code/causal/causal_analysis.py datasets/lab --treatment C_O_ratio --outcome spectral_loss_J
    python code/causal/causal_analysis.py datasets/lab --treatment iodide_reductant --outcome size_mean_nm
    python code/causal/causal_analysis.py datasets/lab --ipw --treatment GO_mg_mL --outcome size_mean_nm
    python code/causal/causal_analysis.py datasets/lab --mediation --treatment C_O_ratio --mediator size_mean_nm \
           --outcome spectral_loss_J
    python code/causal/causal_analysis.py datasets/lab --discover            # PC (causal-learn), exploratório

IPW: o Designer escolhe a receita OLHANDO o lote (C/O → GO_mg_mL, pH…), então o efeito de uma variável da receita é
confundido pelo contexto. Os pesos equilibram os pais do tratamento no DAG (ou --covariates). Padrão (--weights
entropy): BALANCEAMENTO POR ENTROPIA (Hainmueller 2012; para tratamento contínuo, Tübbicke 2022) — os pesos mais
próximos do uniforme (mínima divergência KL) que zeram EXATAMENTE o desbalanço: no binário, as médias das
covariáveis de cada grupo igualam as da amostra toda (ATE); no contínuo, a correlação ponderada tratamento–covariável
é zero e a média/variância do tratamento são preservadas. Problema convexo resolvido pelo dual (w ∝ exp(λᵀg)).
Alternativa clássica (--weights propensity): escore logístico, w = P(T)/e(X) ou (1 − P(T))/(1 − e(X)); contínuo,
escore generalizado normal (Hirano & Imbens 2004), w = f(T)/f(T | X); truncados nos percentis 1/99 — com
confundimento forte o balanço fica parcial, por isso não é o padrão. Diagnóstico: diferença média padronizada (SMD)
ou correlação ponderada antes/depois (meta < 0,1) e tamanho efetivo de amostra. IC por bootstrap que reestima os
pesos em cada reamostra.
Mediação (VanderWeele 2015): M = β₀ + β₁T + β₂ᵀX;  Y = θ₀ + θ₁T + θ₂M + θ₃TM + θ₄ᵀX
    NDE = θ₁ + θ₃(β₀ + β₁t₀ + β₂ᵀE[X]),  NIE = β₁(θ₂ + θ₃(t₀ + 1))   (T: t₀ → t₀ + 1 unidade; t₀ = média)
IC por bootstrap. Efeitos NATURAIS exigem que nenhum confundidor M–Y seja descendente de T; se houver (ex.: a receita
escolhida pelo otimizador a partir do lote), a saída avisa e os efeitos passam a ser condicionais a esses
confundidores (decomposição por caminhos com a receita fixa), não naturais.
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


def parents(node: str, edges=EDGES) -> list[str]:
    return sorted({a for a, b in edges if b == node})


def descendants(node: str, edges=EDGES) -> set[str]:
    out, stack = set(), [node]
    while stack:
        n = stack.pop()
        for a, b in edges:
            if a == n and b not in out:
                out.add(b)
                stack.append(b)
    return out


def _numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[cols].apply(pd.to_numeric, errors="coerce").dropna()


def _wmean(x, w):
    return float(np.sum(w * x) / np.sum(w))


def _wcorr(x, y, w):
    mx, my = _wmean(x, w), _wmean(y, w)
    c = np.sum(w * (x - mx) * (y - my))
    return float(c / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (y - my) ** 2) + 1e-300))


def _smd(x, t, w):
    m1, m0 = _wmean(x[t == 1], w[t == 1]), _wmean(x[t == 0], w[t == 0])
    v1 = _wmean((x[t == 1] - m1) ** 2, w[t == 1])
    v0 = _wmean((x[t == 0] - m0) ** 2, w[t == 0])
    return float((m1 - m0) / np.sqrt((v1 + v0) / 2 + 1e-300))


def _entropy_dual(G: np.ndarray) -> np.ndarray:
    """Pesos w (média 1) de mínima KL ao uniforme com Σ w_i g_i = 0: w ∝ exp(Gλ), λ = argmin log Σ exp(Gλ)."""
    from scipy.optimize import minimize
    from scipy.special import logsumexp, softmax
    sd = G.std(axis=0)
    G = G[:, sd > 1e-12] / sd[sd > 1e-12]
    if G.shape[1] == 0:
        return np.ones(len(G))

    def f(lam):
        z = G @ lam
        return logsumexp(z), softmax(z) @ G
    lam = minimize(f, np.zeros(G.shape[1]), jac=True, method="BFGS", options={"gtol": 1e-10, "maxiter": 2000}).x
    return softmax(G @ lam) * len(G)


def entropy_weights(T: np.ndarray, X: np.ndarray, binary: bool) -> np.ndarray:
    if X.shape[1] == 0:
        return np.ones(len(T))
    Xc = X - X.mean(axis=0)
    if binary:                       # cada grupo reponderado para as médias (e variâncias) da amostra toda: ATE
        w = np.ones(len(T))
        Q = np.c_[Xc, Xc ** 2 - (Xc ** 2).mean(axis=0)]
        for g in (0.0, 1.0):
            k = T == g
            w[k] = _entropy_dual(Q[k]) * k.sum() / len(T) * 2
        return w
    tc = T - T.mean()
    return _entropy_dual(np.c_[Xc, tc, tc ** 2 - tc.var(), tc[:, None] * Xc])


def ipw_weights(T: np.ndarray, X: np.ndarray, binary: bool, trim=(1, 99), method: str = "entropy") -> np.ndarray:
    """Pesos de balanceamento: 'entropy' (padrão, balanço exato) ou 'propensity' (estabilizados e truncados)."""
    if method == "entropy":
        return entropy_weights(T, X, binary)
    from scipy.stats import norm
    Xc = np.c_[np.ones(len(T)), X]
    if binary:
        import statsmodels.api as sm
        try:
            e = sm.Logit(T, Xc).fit(disp=0).predict(Xc) if X.shape[1] else np.full(len(T), T.mean())
        except Exception:      # noqa: BLE001 — separação perfeita: Firth não disponível, usa regularização leve
            e = sm.Logit(T, Xc).fit_regularized(alpha=1.0, disp=0).predict(Xc)
        e = np.clip(e, 1e-3, 1 - 1e-3)
        p = T.mean()
        w = np.where(T == 1, p / e, (1 - p) / (1 - e))
    else:
        beta = np.linalg.lstsq(Xc, T, rcond=None)[0]
        r = T - Xc @ beta
        sd_c = np.sqrt(np.sum(r ** 2) / max(len(T) - Xc.shape[1], 1))
        w = norm.pdf(T, T.mean(), T.std(ddof=1)) / norm.pdf(T, Xc @ beta, sd_c)
    lo, hi = np.percentile(w, trim)
    return np.clip(w, lo, hi)


def _ipw_effect(T, Y, w, binary):
    if binary:
        return _wmean(Y[T == 1], w[T == 1]) - _wmean(Y[T == 0], w[T == 0])     # ATE (Hájek)
    mt, my = _wmean(T, w), _wmean(Y, w)
    return float(np.sum(w * (T - mt) * (Y - my)) / np.sum(w * (T - mt) ** 2))   # dE[Y]/dT no MSM linear


def ipw(lab: str, treatment: str, outcome: str, covariates: list[str] | None = None, edges=EDGES,
        binarize: str | None = None, n_boot: int = 500, seed: int = 0, df: pd.DataFrame | None = None,
        weights: str = "entropy") -> dict:
    """Efeito por ponderação de propensão com balanço antes/depois. Covariáveis padrão: pais do tratamento no DAG."""
    df = build_table(lab) if df is None else df
    cov = covariates if covariates is not None else [c for c in parents(treatment, edges) if c in df]
    data = _numeric(df, [treatment, outcome] + cov)
    if len(data) < 10:
        raise ValueError(f"só {len(data)} sínteses completas para IPW")
    T, Y, X = data[treatment].to_numpy(float), data[outcome].to_numpy(float), data[cov].to_numpy(float)
    if binarize:
        cut = float(np.median(T)) if binarize == "median" else float(binarize)
        T = (T > cut).astype(float)
    binary = set(np.unique(T)) <= {0.0, 1.0}
    w = ipw_weights(T, X, binary, method=weights)
    one = np.ones(len(T))
    bal = []
    for j, c in enumerate(cov):
        if binary:
            bal.append({"covariate": c, "smd_before": _smd(X[:, j], T, one), "smd_after": _smd(X[:, j], T, w)})
        else:
            bal.append({"covariate": c, "corr_before": _wcorr(T, X[:, j], one), "corr_after": _wcorr(T, X[:, j], w)})
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(T), len(T))
        if binary and len(set(T[i])) < 2:
            continue
        try:
            boots.append(_ipw_effect(T[i], Y[i], ipw_weights(T[i], X[i], binary, method=weights), binary))
        except (np.linalg.LinAlgError, ValueError):
            continue
    boots = [b for b in boots if np.isfinite(b)]
    naive = _ipw_effect(T, Y, one, binary)
    worst = max((abs(b.get("smd_after", b.get("corr_after", 0.0))) for b in bal), default=0.0)
    name = ("balanceamento por entropia" if weights == "entropy" else
            "IPW estabilizado, " + ("propensão logística" if binary else "escore generalizado normal"))
    return {"method": name,
            "treatment": treatment + (f" > {binarize}" if binarize else ""), "outcome": outcome, "n": len(T),
            "covariates": cov, "estimand": "ATE" if binary else "inclinação do modelo estrutural marginal (por unidade)",
            "effect": _ipw_effect(T, Y, w, binary), "effect_unadjusted": naive,
            "ci95_bootstrap": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if boots else None,
            "balance": bal, "balance_ok": worst < 0.1,       # |SMD| ou |correlação ponderada| < 0,1
            "weights": {"min": float(w.min()), "max": float(w.max()),
                        "ess": float(w.sum() ** 2 / np.sum(w ** 2)),
                        "trim_percentiles": [1, 99] if weights != "entropy" else None}}


def mediation(lab: str, treatment: str, mediator: str, outcome: str, covariates: list[str] | None = None,
              edges=EDGES, interaction: bool = True, n_boot: int = 1000, seed: int = 0,
              df: pd.DataFrame | None = None) -> dict:
    """Efeitos direto (NDE) e indireto (NIE) por modelos lineares com interação T×M; IC por bootstrap."""
    df = build_table(lab) if df is None else df
    if covariates is None:
        cand = set(parents(treatment, edges)) | set(parents(mediator, edges)) | set(parents(outcome, edges))
        covariates = sorted(c for c in cand - {treatment, mediator} if c in df)
    data = _numeric(df, [treatment, mediator, outcome] + covariates)
    if len(data) < 12:
        raise ValueError(f"só {len(data)} sínteses completas para mediação")
    T, M, Y = (data[c].to_numpy(float) for c in (treatment, mediator, outcome))
    X = data[covariates].to_numpy(float)

    def effects(i):
        t, m, y, x = T[i], M[i], Y[i], X[i]
        Xm = np.c_[np.ones(len(t)), t, x]
        b = np.linalg.lstsq(Xm, m, rcond=None)[0]
        Xy = np.c_[np.ones(len(t)), t, m, t * m if interaction else np.zeros(len(t)), x]
        th = np.linalg.lstsq(Xy, y, rcond=None)[0]
        t0 = t.mean()
        xbar = x.mean(axis=0) if x.shape[1] else np.zeros(0)
        m_t0 = b[0] + b[1] * t0 + (b[2:] @ xbar if len(xbar) else 0.0)
        nde = th[1] + th[3] * m_t0
        nie = b[1] * (th[2] + th[3] * (t0 + 1))
        return nde, nie
    nde, nie = effects(np.arange(len(T)))
    rng = np.random.default_rng(seed)
    bs = np.array([effects(rng.integers(0, len(T), len(T))) for _ in range(n_boot)])
    ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]    # noqa: E731
    tot = nde + nie
    induced = sorted(c for c in covariates if c in descendants(treatment, edges))
    return {"treatment": treatment, "mediator": mediator, "outcome": outcome, "n": len(T), "covariates": covariates,
            "interaction_TxM": interaction, "NDE": float(nde), "NIE": float(nie), "total": float(tot),
            "NDE_ci95": ci(bs[:, 0]), "NIE_ci95": ci(bs[:, 1]), "total_ci95": ci(bs.sum(axis=1)),
            "proportion_mediated": float(nie / tot) if abs(tot) > 1e-12 else None,
            "treatment_induced_confounders": induced,
            "interpretation": ("efeitos naturais (sob ausência de confundimento não medido)" if not induced else
                               f"ATENÇÃO: {induced} são afetados pelo tratamento e confundem M–Y; os efeitos acima "
                               "são condicionais a eles (caminho T→M→Y com essas variáveis fixas), não naturais")}


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
    ap.add_argument("--ipw", action="store_true", help="ponderação por escore de propensão com balanço")
    ap.add_argument("--binarize", help="IPW: dicotomiza o tratamento ('median' ou um limiar)")
    ap.add_argument("--weights", choices=["entropy", "propensity"], default="entropy")
    ap.add_argument("--mediation", action="store_true", help="efeitos direto e indireto via --mediator")
    ap.add_argument("--mediator", default="size_mean_nm")
    ap.add_argument("--covariates", nargs="*", help="substitui o conjunto de ajuste derivado do DAG")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args()
    if a.dot:
        print(dot())
        return
    if not a.lab_dir:
        ap.error("informe a pasta de dados (ex.: datasets/lab)")
    if a.discover:
        print("\n".join(discover(a.lab_dir)))
        return
    if a.ipw:
        print(json.dumps(ipw(a.lab_dir, a.treatment, a.outcome, a.covariates, binarize=a.binarize, n_boot=a.n_boot,
                             weights=a.weights),
                         indent=1, ensure_ascii=False, default=float))
        return
    if a.mediation:
        print(json.dumps(mediation(a.lab_dir, a.treatment, a.mediator, a.outcome, a.covariates, n_boot=a.n_boot),
                         indent=1, ensure_ascii=False, default=float))
        return
    print(json.dumps(estimate(a.lab_dir, a.treatment, a.outcome, refute=not a.no_refute, n_sim=a.n_sim), indent=1, default=float))


if __name__ == "__main__":
    main()
