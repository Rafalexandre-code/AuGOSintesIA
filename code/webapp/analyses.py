"""Análises da proposta FAPESP feitas SÓ com dados experimentais (expdata.py) → dicionários para o site.

Cada função corresponde a uma seção da proposta e devolve números prontos para gráficos (listas, não DataFrames).
Modelos (GP, RF, Mie) são marcados como modelo; pontos medidos, como medida. Nenhum dado do simulador entra.
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE] + [os.path.join(ROOT, "code", d) for d in ("spectral", "campaign", "transfer_learning",
                                                                  "aunp_designer")]
import expdata  # noqa: E402

R = np.random.default_rng(20261004)


def _r(x, nd=4):
    """Arredonda para o JSON (listas aninhadas, NaN → None)."""
    a = np.asarray(x, float)
    out = np.round(a, nd).astype(object)
    out[~np.isfinite(a)] = None
    return out.tolist()


# ---------------------------------------------------------------------------------------------- §4.1 literatura

def literature() -> dict:
    L = expdata.literature()
    src = {s: i for i, s in enumerate(expdata.SOURCES)}
    rec = {
        "source": L["source"].map(src).tolist(), "year": _r(L["year"], 0), "size": _r(L["size_nm"], 2),
        "peak": _r(L["peak_nm"], 1), "T": _r(L["T_C"], 1), "seed": L["seed"].tolist(),
        "red": L["reductant"].tolist(), "cap": L["capping"].tolist(), "morph": L["morph"].tolist(),
        "go": L["go"].tolist(),
    }
    g = expdata.go_subset()
    g = g.assign(size_nm=pd.to_numeric(g["size_nm"], errors="coerce"),
                 T=pd.to_numeric(g["temperature_C"], errors="coerce"), year=pd.to_numeric(g["year"], errors="coerce"))
    def txt(v):
        return "" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)

    go_rows = []
    for _, r in g.iterrows():
        go_rows.append({"doi": txt(r["doi"]), "title": txt(r.get("title"))[:140],
                        "year": None if pd.isna(r["year"]) else int(r["year"]),
                        "reductants": txt(r["reductants"]), "supports": txt(r["supports"]),
                        "morph": txt(r["morphology_class"]),
                        "size": None if pd.isna(r["size_nm"]) else round(float(r["size_nm"]), 1),
                        "T": None if pd.isna(r["T"]) else round(float(r["T"]), 1),
                        "source": expdata.SOURCES.get(r["source"], txt(r["source"]))})
    by_year = (L.dropna(subset=["year"]).assign(red=lambda x: x["reductant"])
               .groupby(["year", "red"]).size().unstack(fill_value=0))
    return {"records": rec, "n": int(len(L)), "n_doi": int(L.loc[L["doi"] != "", "doi"].nunique()),
            "sources": list(expdata.SOURCES.values()), "reductants": expdata.REDUCTANTS, "capping": expdata.CAPPING,
            "morph": expdata.MORPH, "go_rows": go_rows, "n_go": int(len(g)),
            "n_go_doi": int(g["doi"].dropna().nunique()),
            "reductant_by_year": {"years": by_year.index.astype(int).tolist(),
                                  "series": {expdata.REDUCTANTS[c] if c >= 0 else "outro/não citado":
                                             by_year[c].tolist() for c in by_year.columns}}}


# ---------------------------------------------------------------------------------------------- §4.4/§4.6 óptica

def _peak(wl: np.ndarray, e: np.ndarray, lo: float = 480.0) -> float:
    """λ do máximo acima de `lo`, refinado por uma parábola nos 3 pontos em torno do máximo da grade."""
    sel = np.flatnonzero(wl >= lo)
    i = sel[np.argmax(e[sel])]
    if i in (sel[0], len(wl) - 1):
        return float(wl[i])
    y0, y1, y2 = e[i - 1], e[i], e[i + 1]
    den = y0 - 2 * y1 + y2
    return float(wl[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (wl[i + 1] - wl[i]))


def optics() -> dict:
    """Mie com as constantes ópticas MEDIDAS do Au (Johnson & Christy) + validação contra LSPR medidos na literatura
    + perda J do pré-registro."""
    import mie
    import prereg
    import uvvis
    wl = np.arange(400.0, 901.0, 2.0)                     # mesma grade de 2 nm da perda J (com 4 nm, J no alvo ≈ 3)
    d = np.exp(np.linspace(np.log(2.0), np.log(200.0), 120))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        C = np.array([mie.extinction_cross_section(wl, x) for x in d])           # nm² por partícula
    vol = np.pi * d ** 3 / 6
    # ensemble log-normal de média dc sobre a grade de diâmetros (o mesmo cálculo que app.js faz no navegador);
    # σ ≈ 0: interpolação em log d entre os dois diâmetros vizinhos
    def ens(dc, sig):
        if sig <= 0.005:
            j = int(np.clip(np.searchsorted(np.log(d), np.log(dc)) - 1, 0, len(d) - 2))
            f = (np.log(dc) - np.log(d[j])) / (np.log(d[j + 1]) - np.log(d[j]))
            return (1 - f) * C[j] + f * C[j + 1]
        s = np.sqrt(np.log(1 + sig ** 2))
        mu = np.log(dc) - s ** 2 / 2
        w = np.exp(-0.5 * ((np.log(d) - mu) / s) ** 2)
        return (w / w.sum()) @ C
    # λ_LSPR de Mie para ensemble com σ = 0,1 — curva de referência
    lam = np.array([_peak(wl, ens(x, 0.10)) for x in d])
    # literatura: esferas (ou partículas sem outra forma) com tamanho e pico medidos no mesmo registro
    L = expdata.literature()
    sph = L[L["morph"].isin([expdata.MORPH.index("sphere"), expdata.MORPH.index("particle")])
            & L["size_nm"].between(3, 150) & L["peak_nm"].between(490, 620)]
    pred = np.interp(np.log(sph["size_nm"]), np.log(d), lam)
    res = sph["peak_nm"].to_numpy() - pred
    bins = [3, 10, 20, 40, 80, 150]
    by_bin = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = sph["size_nm"].between(lo, hi, inclusive="left").to_numpy()
        if m.sum():
            by_bin.append({"range": f"{lo}–{hi} nm", "n": int(m.sum()), "median_residual": float(np.median(res[m])),
                           "mad": float(np.median(np.abs(res[m] - np.median(res[m]))))})
    # alvo e perda J do pré-registro (Eq. 1)
    cfg = prereg.load()
    tw, te = prereg.target_spectrum(cfg)
    norm = cfg["target_spectrum"].get("normalization", "max")
    sm = float(np.mean(prereg.s_m(cfg)))
    grid = prereg.grid(cfg)
    dd, ss = np.exp(np.linspace(np.log(5), np.log(80), 46)), np.linspace(0.02, 0.40, 20)
    Jg = np.empty((len(ss), len(dd)))
    for j, sg in enumerate(ss):
        for i, x in enumerate(dd):
            e = ens(x, sg)
            Jg[j, i] = uvvis.spectral_loss_J(wl, e, tw, te, s=sm, grid=grid, norm=None if norm == "none" else norm)
    return {"wl": _r(wl, 0), "d": _r(d, 3), "C_ext": _r(C / C.max(axis=1, keepdims=True), 4),
            "C_ext_max": _r(C.max(axis=1), 2), "per_volume_max": _r(C.max(axis=1) / vol, 5),
            "lspr_curve": {"d": _r(d, 3), "lambda": _r(lam, 1), "sigma": 0.10},
            "lit_spheres": {"size": _r(sph["size_nm"], 2), "peak": _r(sph["peak_nm"], 1),
                            "source": sph["source"].map(expdata.SOURCES).tolist(), "doi": sph["doi"].tolist(),
                            "n": int(len(sph)), "median_abs_residual": float(np.median(np.abs(res))),
                            "within_5nm": float(np.mean(np.abs(res) <= 5)), "by_bin": by_bin},
            "target": {"wl": _r(tw, 0), "E": _r(te / te.max(), 4), "diameter": cfg["target_spectrum"]["diameter_nm"],
                       "sigma": cfg["target_spectrum"]["relative_dispersion"], "normalization": norm, "s_m": sm,
                       "grid": [float(grid[0]), float(grid[-1]), float(grid[1] - grid[0])]},
            "J_surface": {"d": _r(dd, 2), "sigma": _r(ss, 3), "log10J": _r(np.log10(Jg), 3)}}


# ---------------------------------------------------------------------------------------------- §4.5 Designer (AgNP)

def _gp_fit(Xn: np.ndarray, y: np.ndarray):
    """GP do AuNP Designer: Matérn-5/2 + ARD com prior de comprimento (hierarchical.matern52), saída padronizada."""
    import torch
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Standardize
    from gpytorch.kernels import ScaleKernel
    from gpytorch.mlls import ExactMarginalLogLikelihood
    import hierarchical
    tx = torch.tensor(Xn, dtype=torch.double)
    ty = torch.tensor(y[:, None], dtype=torch.double)
    m = SingleTaskGP(tx, ty, covar_module=ScaleKernel(hierarchical.matern52(Xn.shape[1])),
                     outcome_transform=Standardize(1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit_gpytorch_mll(ExactMarginalLogLikelihood(m.likelihood, m))
    return m


def _gp_export(m, Xn: np.ndarray) -> dict:
    """Parâmetros para a previsão em JavaScript (mesma conta do GPyTorch): μ = c + k*ᵀα, σ² = s² − ‖L⁻¹k*‖²."""
    import torch
    ls = m.covar_module.base_kernel.lengthscale.detach().numpy().ravel()
    os_ = float(m.covar_module.outputscale.detach())
    noise = float(m.likelihood.noise.detach().ravel()[0])
    c = float(m.mean_module.constant.detach())
    tf = m.outcome_transform
    ymu, ysd = float(tf.means.detach().ravel()[0]), float(tf.stdvs.detach().ravel()[0])
    ys = m.train_targets.detach().numpy()                         # já padronizado
    K = os_ * _matern52(Xn, Xn, ls) + noise * np.eye(len(Xn))
    Lc = np.linalg.cholesky(K)
    alpha = np.linalg.solve(Lc.T, np.linalg.solve(Lc, ys - c))
    # conferência com o posterior do GPyTorch
    with torch.no_grad():
        p = m.posterior(torch.tensor(Xn[:5], dtype=torch.double))
    mu_np = ymu + ysd * (c + (os_ * _matern52(Xn[:5], Xn, ls)) @ alpha)
    assert np.allclose(mu_np, p.mean.numpy().ravel(), atol=1e-6 * max(1.0, abs(ysd))), "export do GP diverge"
    return {"ls": ls.tolist(), "outputscale": os_, "noise": noise, "const": c, "y_mean": ymu, "y_std": ysd,
            "X": np.round(Xn, 6).tolist(), "alpha": alpha.tolist(), "L": np.round(Lc, 10).tolist()}


def _matern52(A: np.ndarray, B: np.ndarray, ls: np.ndarray) -> np.ndarray:
    r = np.sqrt(np.maximum(((A[:, None, :] - B[None, :, :]) / ls) ** 2, 0).sum(-1))
    s5 = np.sqrt(5.0) * r
    return (1 + s5 + 5.0 / 3.0 * r ** 2) * np.exp(-s5)


def gp_predict(gp: dict, Xn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mesma conta do site (JS), em numpy — usada nos testes e no SHAP."""
    X, ls = np.asarray(gp["X"]), np.asarray(gp["ls"])
    k = gp["outputscale"] * _matern52(np.atleast_2d(Xn), X, ls)
    mu = gp["const"] + k @ np.asarray(gp["alpha"])
    v = np.linalg.solve(np.asarray(gp["L"]), k.T)
    var = np.maximum(gp["outputscale"] - (v ** 2).sum(0), 1e-12)
    return gp["y_mean"] + gp["y_std"] * mu, gp["y_std"] * np.sqrt(var)


def designer_agnp() -> dict:
    """AuNP Designer (§4.5) aplicado a uma campanha REAL de nanopartículas (AgNP, perda espectral contra alvo):
    GP Matérn-5/2 + ARD em ln(perda), validação cruzada, aquisição EI e sugestões."""
    from scipy.stats import norm, qmc
    raw, u = expdata.agnp()
    cols = list(raw.columns[:-1])
    X = u[cols].to_numpy(float)
    lo, hi = X.min(0), X.max(0)
    Xn = (X - lo) / (hi - lo)
    y = np.log(u["mean"].to_numpy(float))
    m = _gp_fit(Xn, y)
    gp = _gp_export(m, Xn)
    # validação cruzada em 10 dobras (hiperparâmetros reajustados em cada dobra)
    idx = R.permutation(len(Xn))
    folds = np.array_split(idx, 10)
    cv_mu, cv_sd = np.empty(len(y)), np.empty(len(y))
    for f in folds:
        tr = np.setdiff1d(idx, f)
        mf = _gp_fit(Xn[tr], y[tr])
        g = _gp_export(mf, Xn[tr])
        cv_mu[f], cv_sd[f] = gp_predict(g, Xn[f])
    resid = y - cv_mu
    r2 = 1 - np.sum(resid ** 2) / np.sum((y - y.mean()) ** 2)
    # ruído total previsto (latente + ruído do GP) para a cobertura
    sd_tot = np.sqrt(cv_sd ** 2 + gp["noise"] * gp["y_std"] ** 2)
    cover = float(np.mean(np.abs(resid) <= 1.96 * sd_tot))
    # EI (minimizar ln perda) num conjunto Sobol e 5 sugestões diversas
    cand = qmc.Sobol(len(cols), seed=7).random(4096)
    mu, sd = gp_predict(gp, cand)
    best = y.min()
    z = (best - mu) / sd
    ei = (best - mu) * norm.cdf(z) + sd * norm.pdf(z)
    order, chosen = np.argsort(-ei), []
    for i in order:
        if all(np.linalg.norm(cand[i] - cand[j]) > 0.15 for j in chosen):
            chosen.append(i)
        if len(chosen) == 5:
            break
    sugg = [{"x": _r(lo + cand[i] * (hi - lo), 3), "pred_loss": float(np.exp(mu[i])),
             "lo": float(np.exp(mu[i] - 1.96 * sd[i])), "hi": float(np.exp(mu[i] + 1.96 * sd[i])),
             "ei": float(ei[i])} for i in chosen]
    ib = int(np.argmin(u["mean"]))
    return {"columns": cols, "labels": [expdata.AGNP_LABELS[c] for c in cols], "lo": lo.tolist(), "hi": hi.tolist(),
            "points": {"X": _r(X, 3), "mean": _r(u["mean"], 4), "sd": _r(u["std"], 4), "n": u["count"].tolist()},
            "n_measurements": int(len(raw)), "n_conditions": int(len(u)), "gp": gp,
            "cv": {"obs": _r(y, 4), "pred": _r(cv_mu, 4), "sd": _r(sd_tot, 4), "r2": float(r2),
                   "rmse": float(np.sqrt(np.mean(resid ** 2))), "coverage95": cover},
            "best_measured": {"x": _r(X[ib], 3), "loss": float(u["mean"].iloc[ib]), "sd": float(u["std"].iloc[ib])},
            "suggestions": sugg, "ei_note": "EI sobre ln(perda), 4096 candidatos Sobol, 5 escolhas a ≥ 0,15 entre si"}


# ---------------------------------------------------------------------------------------------- §4.15 benchmark

def _bo_run(X, y, minimize, arm, seed, n_init=5, budget=60):
    """Uma campanha retrospectiva: o "laboratório" devolve a medida REAL (média das réplicas) da condição escolhida."""
    from scipy.stats import norm
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    rng = np.random.default_rng(seed)
    s = -1.0 if minimize else 1.0                     # internamente: maximizar s·y
    ys = s * y
    chosen = list(rng.choice(len(X), n_init, replace=False))
    best = [float(np.max(ys[chosen]))] * n_init
    budget = min(budget, len(X))
    while len(chosen) < budget:
        rest = np.setdiff1d(np.arange(len(X)), chosen)
        if arm == "Aleatório":
            k = int(rng.choice(rest))
        else:
            Xt, yt = X[chosen], ys[chosen]
            mu_y, sd_y = yt.mean(), yt.std() or 1.0
            yz = (yt - mu_y) / sd_y
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if arm.startswith("GP"):
                    kern = ConstantKernel(1.0, (1e-2, 1e2)) * Matern(np.full(X.shape[1], 0.3), (1e-2, 1e2), nu=2.5) \
                        + WhiteKernel(1e-2, (1e-6, 1.0))
                    m = GaussianProcessRegressor(kern, normalize_y=False, n_restarts_optimizer=1,
                                                 random_state=int(rng.integers(1e9))).fit(Xt, yz)
                    mu, sd = m.predict(X[rest], return_std=True)
                else:
                    m = RandomForestRegressor(60, min_samples_leaf=2, random_state=int(rng.integers(1e9))).fit(Xt, yz)
                    P = np.stack([t.predict(X[rest]) for t in m.estimators_])
                    mu, sd = P.mean(0), P.std(0)
            sd = np.maximum(sd, 1e-9)
            if arm.endswith("UCB"):
                a = mu + 2.0 * sd
            else:
                f = yz.max()
                z = (mu - f) / sd
                a = (mu - f) * norm.cdf(z) + sd * norm.pdf(z)
            k = int(rest[np.argmax(a)])
        chosen.append(k)
        best.append(max(best[-1], float(ys[k])))
    return np.array(best)


def benchmark(seeds: int = 20, budget: int = 60, workers: int = 4) -> dict:
    """§4.15: estratégias de aprendizado ativo reexecutadas em 5 campanhas EXPERIMENTAIS publicadas."""
    from joblib import Parallel, delayed
    arms = ["Aleatório", "GP-EI", "GP-UCB", "RF-EI"]
    out = {"arms": arms, "datasets": {}, "seeds": seeds}
    for name, (f, _, minimize, label, ref) in expdata.BENCHMARKS.items():
        X, y, feats, minimize, label = expdata.benchmark(name)
        B = min(budget, len(X))
        jobs = [(arm, s) for arm in arms for s in range(seeds)]
        res = Parallel(n_jobs=workers)(delayed(_bo_run)(X, y, minimize, arm, 1000 + s, 5, B) for arm, s in jobs)
        sgn = -1.0 if minimize else 1.0
        opt, worst = np.max(sgn * y), np.min(sgn * y)
        top = np.quantile(sgn * y, 0.95)
        curves, reach = {}, {}
        for arm in arms:
            M = np.array([r for (a, _), r in zip(jobs, res) if a == arm])
            Nn = (M - worst) / (opt - worst)
            curves[arm] = {"median": _r(np.median(Nn, 0), 4), "q25": _r(np.quantile(Nn, 0.25, 0), 4),
                           "q75": _r(np.quantile(Nn, 0.75, 0), 4)}
            hit = [int(np.argmax(r >= top)) + 1 if np.any(r >= top) else None for r in M]
            reach[arm] = {"fraction": float(np.mean([h is not None for h in hit])),
                          "median_experiments": float(np.median([h for h in hit if h])) if any(hit) else None,
                          "per_seed": hit}
        out["datasets"][name] = {"n_pool": int(len(X)), "features": feats, "objective": label, "minimize": minimize,
                                 "reference": ref, "budget": B, "curves": curves, "reach_top5": reach}
    return out


# ---------------------------------------------------------------------------------------------- §4.13 SHAP

def interpretability(designer: dict) -> dict:
    """SHAP (valores de Shapley exatos) do GP da campanha AgNP; árvores (TreeSHAP) para AuNC e literatura;
    interações pela estatística H² de Friedman no GP."""
    import shap
    from sklearn.ensemble import HistGradientBoostingRegressor
    gp = designer["gp"]
    lo, hi = np.array(designer["lo"]), np.array(designer["hi"])
    Xn = np.asarray(gp["X"])
    f = lambda Z: gp_predict(gp, Z)[0]                                        # noqa: E731
    bg = Xn[R.choice(len(Xn), 40, replace=False)]
    ex = shap.ExactExplainer(f, shap.maskers.Independent(bg, max_samples=40))
    sv = ex(Xn).values
    # H² de Friedman entre pares (dependência parcial em 60 pontos)
    S = Xn[R.choice(len(Xn), 60, replace=False)]
    p = Xn.shape[1]

    def pd_fun(cols, vals):
        Z = np.repeat(S[None], len(vals), 0).copy()
        for j, c in enumerate(cols):
            Z[:, :, c] = vals[:, j][:, None]
        return np.array([f(z).mean() for z in Z])
    H = np.zeros((p, p))
    for i in range(p):
        for j in range(i + 1, p):
            pij = pd_fun([i, j], S[:, [i, j]])
            pi, pj = pd_fun([i], S[:, [i]]), pd_fun([j], S[:, [j]])
            a, b, c = pij - pij.mean(), pi - pi.mean(), pj - pj.mean()
            H[i, j] = H[j, i] = float(np.sum((a - b - c) ** 2) / max(np.sum(a ** 2), 1e-12))
    out = {"agnp": {"features": designer["labels"], "values": _r(sv, 4), "X": _r(lo + Xn * (hi - lo), 3),
                    "H2": _r(H, 3), "target": "ln(perda espectral) prevista pelo GP"}}
    # AuNC: λ de emissão
    c = expdata.aunc()
    feats = ["size_nm", "exc_nm", "T_C", "time_h", "pH"]
    c = c.assign(GSH=(c["ligand"].str.upper() == "GSH").astype(float),
                 water=(c["solvent"] == "water").astype(float))
    F = feats + ["GSH", "water"]
    m = HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0).fit(c[F], c["em_nm"])
    from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
    pred_cv = cross_val_predict(HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0), c[F], c["em_nm"],
                                cv=KFold(5, shuffle=True, random_state=0))
    tsv = shap.TreeExplainer(m).shap_values(c[F])
    out["aunc"] = {"features": ["tamanho (nm)", "λ exc (nm)", "T síntese (°C)", "tempo (h)", "pH", "ligante GSH",
                                "solvente água"], "values": _r(tsv, 3), "X": _r(c[F].to_numpy(float), 2),
                   "target": "λ de emissão (nm)", "cv_r2": float(1 - np.sum((c["em_nm"] - pred_cv) ** 2)
                                                               / np.sum((c["em_nm"] - c["em_nm"].mean()) ** 2))}
    # literatura: ln(tamanho) de esferas/partículas
    L = expdata.literature()
    L = L[L["size_nm"].between(1, 300) & L["reductant"].ge(0)].copy()
    Fl = {"citrato": L["reductant"].eq(0), "NaBH4": L["reductant"].eq(1), "ácido ascórbico": L["reductant"].eq(2),
          "mediada por sementes": L["seed"].eq(1), "CTAB": L["capping"].eq(0), "PVP": L["capping"].eq(1),
          "tiol (GSH/dodecanotiol)": L["capping"].isin([4, 8]), "temperatura (°C)": L["T_C"],
          "forma não esférica": ~L["morph"].isin([0, 2, 14, -1])}
    Xl = pd.DataFrame({k: v.astype(float) for k, v in Fl.items()})
    yl = np.log(L["size_nm"].to_numpy(float))
    gl = HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0)
    groups = L["doi"].where(L["doi"] != "", L.index.astype(str)).to_numpy()
    pcv = cross_val_predict(gl, Xl, yl, cv=GroupKFold(5), groups=groups)
    gl.fit(Xl, yl)
    samp = R.choice(len(Xl), min(1500, len(Xl)), replace=False)
    lsv = shap.TreeExplainer(gl).shap_values(Xl.iloc[samp])
    out["literature"] = {"features": list(Fl), "values": _r(lsv, 3), "X": _r(Xl.iloc[samp].to_numpy(float), 1),
                         "target": "ln(tamanho, nm)", "n": int(len(Xl)),
                         "cv_r2_by_paper": float(1 - np.sum((yl - pcv) ** 2) / np.sum((yl - yl.mean()) ** 2))}
    return out


# ---------------------------------------------------------------------------------------------- §4.17/§4.18 ruído e variabilidade multi-fonte

def variability() -> dict:
    from scipy import stats
    raw, u = expdata.agnp()
    cols = list(raw.columns[:-1])
    groups = [g["loss"].to_numpy() for _, g in raw.groupby(cols, sort=False)]
    lev = stats.levene(*groups, center="median")
    slope = np.polyfit(np.log(u["mean"]), np.log(u["std"].clip(lower=1e-6)), 1)[0]
    within = np.mean([g.var(ddof=1) for g in groups])
    between = np.var(u["mean"], ddof=1)
    # literatura: Turkevich (citrato, sem sementes, esfera/partícula) — variação entre artigos × dentro do artigo
    L = expdata.literature()
    t = L[L["reductant"].eq(0) & L["seed"].eq(0) & L["morph"].isin([0, 14]) & L["size_nm"].between(3, 120)
          & (L["doi"] != "")].copy()
    per_paper = t.groupby("doi")["size_nm"].median()             # Cruse: tamanho é do ARTIGO (repete nos parágrafos)
    ly = np.log(per_paper.to_numpy())
    # AuNC: generalização para artigo novo (GroupKFold por DOI) × divisão aleatória
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
    c = expdata.aunc()
    c = c.assign(GSH=(c["ligand"].str.upper() == "GSH").astype(float), water=(c["solvent"] == "water").astype(float))
    F = ["size_nm", "exc_nm", "T_C", "time_h", "pH", "GSH", "water"]
    g = HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0)
    rnd = cross_val_predict(g, c[F], c["em_nm"], cv=KFold(5, shuffle=True, random_state=0))
    loso = cross_val_predict(g, c[F], c["em_nm"], cv=GroupKFold(5), groups=c["doi"])
    rm = lambda p: float(np.sqrt(np.mean((c["em_nm"] - p) ** 2)))                # noqa: E731
    r2 = lambda p: float(1 - np.sum((c["em_nm"] - p) ** 2) / np.sum((c["em_nm"] - c["em_nm"].mean()) ** 2))  # noqa: E731
    return {"agnp": {"mean": _r(u["mean"], 4), "sd": _r(u["std"], 4), "n": u["count"].tolist(),
                     "levene_W": float(lev.statistic), "levene_p": float(lev.pvalue), "loglog_slope": float(slope),
                     "icc": float(between / (between + within)), "median_cv": float(np.median(u["std"] / u["mean"])),
                     "n_measurements": int(len(raw))},
            "turkevich": {"n_records": int(len(t)), "n_papers": int(len(per_paper)),
                          "sizes_per_paper": _r(per_paper, 1), "median": float(np.median(per_paper)),
                          "q10_q90": [float(np.quantile(per_paper, 0.1)), float(np.quantile(per_paper, 0.9))],
                          "sd_log": float(np.std(ly, ddof=1)), "fold_1sd": float(np.exp(np.std(ly, ddof=1))),
                          "frac_10_20nm": float(np.mean(per_paper.between(10, 20)))},
            "aunc_generalization": {"rmse_random": rm(rnd), "rmse_new_paper": rm(loso), "r2_random": r2(rnd),
                                    "r2_new_paper": r2(loso), "sd_em": float(c["em_nm"].std()), "obs": _r(c["em_nm"], 0),
                                    "pred_random": _r(rnd, 1), "pred_new_paper": _r(loso, 1),
                                    "n_papers": int(c["doi"].nunique())}}


# ---------------------------------------------------------------------------------------------- §4.9 causal

def causal() -> dict:
    """Efeito do redutor forte (NaBH4) × citrato sobre ln(tamanho), por IPW com escore de propensão, nos registros
    da literatura; balanço (SMD), sobreposição, bootstrap e E-value."""
    from sklearn.linear_model import LogisticRegression
    L = expdata.literature()
    d = L[L["reductant"].isin([0, 1]) & L["size_nm"].between(1, 300)].copy()
    d["treat"] = (d["reductant"] == 1).astype(int)
    d["y"] = np.log(d["size_nm"])
    cov = pd.DataFrame({
        "mediada por sementes": d["seed"].astype(float),
        "aquecida (T > 40 °C)": (d["T_C"] > 40).astype(float),
        "T não informada": d["T_C"].isna().astype(float),
        "CTAB/CTAC": d["capping"].isin([0, 3]).astype(float),
        "tiol (GSH/dodecanotiol/TOAB)": d["capping"].isin([4, 5, 8]).astype(float),
        "polímero (PVP/PEG)": d["capping"].isin([1, 2]).astype(float),
        "fonte NSP": (d["source"] == "nsp2026").astype(float),
    })
    Xc, t, y = cov.to_numpy(), d["treat"].to_numpy(), d["y"].to_numpy()

    def ipw(idx):
        lr = LogisticRegression(max_iter=1000).fit(Xc[idx], t[idx])
        e = np.clip(lr.predict_proba(Xc[idx])[:, 1], 0.02, 0.98)
        w = np.where(t[idx] == 1, 1 / e, 1 / (1 - e))
        m1 = np.sum(w * t[idx] * y[idx]) / np.sum(w * t[idx])
        m0 = np.sum(w * (1 - t[idx]) * y[idx]) / np.sum(w * (1 - t[idx]))
        return m1 - m0, e, w
    ate, e, w = ipw(np.arange(len(d)))
    boots = [ipw(R.integers(0, len(d), len(d)))[0] for _ in range(300)]
    lo_, hi_ = np.quantile(boots, [0.025, 0.975])
    naive = y[t == 1].mean() - y[t == 0].mean()

    def smd(weights):
        out = []
        for j in range(Xc.shape[1]):
            x = Xc[:, j]
            m1 = np.average(x[t == 1], weights=weights[t == 1])
            m0 = np.average(x[t == 0], weights=weights[t == 0])
            v = (x[t == 1].var() + x[t == 0].var()) / 2
            out.append(float((m1 - m0) / np.sqrt(v)) if v > 0 else 0.0)
        return out
    rr = np.exp(abs(ate) * 1.0)                                  # razão de médias geométricas
    evalue = float(rr + np.sqrt(rr * (rr - 1)))
    return {"treatment": "NaBH4 (redutor forte)", "control": "citrato de sódio", "outcome": "ln(tamanho, nm)",
            "n": int(len(d)), "n_treated": int(t.sum()), "naive": float(naive), "ate": float(ate),
            "ci95": [float(lo_), float(hi_)], "ratio": float(np.exp(ate)),
            "ratio_ci95": [float(np.exp(lo_)), float(np.exp(hi_))], "e_value": evalue,
            "covariates": list(cov.columns), "smd_before": smd(np.ones(len(d))), "smd_after": smd(w),
            "propensity": {"treated": _r(np.sort(e[t == 1])[::max(1, int(t.sum()) // 800)], 3),
                           "control": _r(np.sort(e[t == 0])[::max(1, int((1 - t).sum()) // 800)], 3)},
            "dag": {"nodes": ["redutor", "temperatura", "sementes", "ligante", "fonte (base)", "tamanho"],
                    "edges": [["redutor", "tamanho"], ["temperatura", "tamanho"], ["sementes", "tamanho"],
                              ["ligante", "tamanho"], ["temperatura", "redutor"], ["sementes", "redutor"],
                              ["ligante", "redutor"], ["fonte (base)", "redutor"], ["fonte (base)", "tamanho"]]}}


# ---------------------------------------------------------------------------------------------- caracterização real

def xrd() -> dict:
    """Quadros reais de difração do padrão CeO2 (detector GE 2048×2048): imagem, superfície, perfil radial, indexação
    dos anéis da fluorita (N = h²+k²+l²) e geometria (λ, distância) por r = D·tan 2θ."""
    import fabio
    from scipy.signal import find_peaks
    base = os.path.join(ROOT, "datasets", "xrd-ceo2-calibration")

    def mean_frame(name):
        im = fabio.open(os.path.join(base, name))
        fr = [im.getframe(i).data.astype(float) for i in range(im.nframes)]
        return np.mean(fr, 0), im.nframes
    img, nf = mean_frame("CeO2_1s_000012.ge3")
    dark, _ = mean_frame("dark_1s_000014.ge3")
    img_c = np.clip(img - dark, 0, None)
    n = img_c.shape[0]
    yy, xx = np.indices(img_c.shape)

    def profile(cy, cx, step=2):
        r = np.hypot(yy[::step, ::step] - cy, xx[::step, ::step] - cx).ravel().astype(int)
        v = img_c[::step, ::step].ravel()
        return np.bincount(r, v) / np.maximum(np.bincount(r), 1)

    def contrast(pr, lo=150, hi=950):
        seg = pr[lo:hi]
        return float(np.sum((seg - np.convolve(seg, np.ones(31) / 31, mode="same")) ** 2))
    # centro: anéis concêntricos ficam mais estreitos (maior contraste do perfil radial) quando o centro está certo;
    # o raio fica entre 150 e 950 px para excluir o beamstop e a borda
    cy, cx = n / 2, n / 2
    for span, num, stp in ((160, 9, 4), (24, 7, 2), (4, 9, 1)):
        cands = [(a_, b_) for a_ in np.linspace(cy - span, cy + span, num) for b_ in np.linspace(cx - span, cx + span, num)]
        cy, cx = max(cands, key=lambda c: contrast(profile(c[0], c[1], stp)))
    r = np.hypot(yy - cy, xx - cx).ravel()
    rb = r.astype(int)
    cnt = np.bincount(rb)
    prof = np.bincount(rb, img_c.ravel()) / np.maximum(cnt, 1)
    rmax = int(min(cy, cx, n - cy, n - cx))                      # anéis completos dentro do detector
    prof = prof[:rmax]
    base_line = np.convolve(prof, np.ones(41) / 41, mode="same")
    sig = prof - base_line
    pk, _ = find_peaks(sig, prominence=np.std(sig[150:]) * 1.5, distance=6)
    pk = pk[pk > 120]
    pk = np.sort(pk[np.argsort(-sig[pk])[:10]])
    # 1) semente: os 4 primeiros anéis pela razão de ângulo pequeno r/r111 ≈ √(N/3)
    # 2) geometria: r = D·tan(2θ), sen θ = λ·√N/(2a), a(CeO2) = 5,4116 Å (NIST SRM 674b) → λ e D por mínimos quadrados
    # 3) todos os reflexos da fluorita (hkl todos pares ou todos ímpares) dentro do detector: busca do pico perto do raio
    #    previsto, posição subpixel por parábola, e novo ajuste — duas iterações
    from scipy.optimize import least_squares
    A_CEO2 = 5.4116
    hkls = {}
    for h in range(0, 8):
        for k in range(0, h + 1):
            for m_ in range(0, k + 1):
                if (h % 2 == k % 2 == m_ % 2) and h > 0:
                    hkls.setdefault(h * h + k * k + m_ * m_, []).append(f"{h}{k}{m_}")
    Ns = sorted(hkls)
    noise = 1.4826 * np.median(np.abs(sig[150:] - np.median(sig[150:])))

    def subpix(i):
        y0, y1, y2 = prof[i - 1], prof[i], prof[i + 1]
        den = y0 - 2 * y1 + y2
        return i + (0.5 * (y0 - y2) / den if den else 0.0)

    def fit(pairs):
        rr, NN = np.array([q[0] for q in pairs]), np.array([q[1] for q in pairs], float)

        def resid(p_):
            D, lam = p_
            th = np.arcsin(np.clip(lam * np.sqrt(NN) / (2 * A_CEO2), -1, 1))
            return D * np.tan(2 * th) - rr
        sol = least_squares(resid, [2000.0, 0.2], bounds=([100, 0.01], [50000, 2.0]))
        return sol.x, sol.fun

    def r_of(N, D, lam):
        return D * np.tan(2 * np.arcsin(lam * np.sqrt(N) / (2 * A_CEO2)))
    seed = []
    if len(pk) >= 4:
        obs = pk / pk[0]
        for N in (3, 4, 8, 11):
            j = int(np.argmin(np.abs(obs - np.sqrt(N / 3))))
            if abs(obs[j] - np.sqrt(N / 3)) / np.sqrt(N / 3) < 0.03:
                seed.append((subpix(int(pk[j])), N))
    geom, match = None, []
    if len(seed) >= 3:
        (D, lam), _ = fit(seed)
        for _ in range(2):
            pairs = []
            for N in Ns:
                rp = r_of(N, D, lam)
                if not np.isfinite(rp) or rp > rmax - 6:
                    break
                w = np.arange(int(rp) - 5, int(rp) + 6)
                i = int(w[np.argmax(sig[w])])
                if sig[i] > 4 * noise and sig[i] >= sig[i - 1] and sig[i] >= sig[i + 1]:
                    pairs.append((subpix(i), N))
            (D, lam), res = fit(pairs)
        r111 = next(q[0] for q in pairs if q[1] == 3)
        for N in Ns:
            rp = float(r_of(N, D, lam))
            if not np.isfinite(rp) or rp > rmax - 6:
                break
            got = next((q[0] for q in pairs if q[1] == N), None)
            match.append({"hkl": "/".join(sorted(hkls[N])), "N": N, "two_theta": float(np.degrees(2 * np.arcsin(lam * np.sqrt(N) / (2 * A_CEO2)))),
                          "r_pred": rp, "r_obs": None if got is None else float(got),
                          "resid_px": None if got is None else float(got - rp),
                          "ratio_small_angle": float(np.sqrt(N / 3)), "ratio_obs": None if got is None else float(got / r111)})
        geom = {"wavelength_A": float(lam), "energy_keV": float(12.3984 / lam), "distance_px": float(D),
                "distance_mm_if_200um": float(D * 0.2), "rms_residual_px": float(np.sqrt(np.mean(res ** 2))),
                "a_ceo2_A": A_CEO2, "n_rings": int(len(pairs)), "n_predicted": int(len(match))}
    step = n // 256
    small = img_c[: step * 256, : step * 256].reshape(256, step, 256, step).mean((1, 3))
    s3 = n // 128
    sm3 = img_c[: s3 * 128, : s3 * 128].reshape(128, s3, 128, s3).mean((1, 3))
    return {"n_frames": int(nf), "shape": list(img_c.shape), "center": [float(cy), float(cx)],
            "image_log10": _r(np.log10(small + 1), 3), "surface_log10": _r(np.log10(sm3 + 1), 3),
            "profile": _r(prof, 2), "baseline": _r(base_line, 2), "peaks": pk.tolist(), "rings": match,
            "geometry": geom}


def aunc_section() -> dict:
    c = expdata.aunc()
    lig = np.where(c["ligand"].str.upper() == "GSH", "GSH",
                   np.where(c["ligand"].str.lower().str.contains("thiol"), "outros tióis", "outros"))
    return {"size": _r(c["size_nm"], 2), "exc": _r(c["exc_nm"], 0), "em": _r(c["em_nm"], 0), "T": _r(c["T_C"], 1),
            "pH": _r(c["pH"], 2), "time": _r(c["time_h"], 2), "ligand": lig.tolist(), "solvent": c["solvent"].tolist(),
            "doi": c["doi"].tolist(), "n": int(len(c)), "n_doi": int(c["doi"].nunique())}
