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
    # registros do gráfico 3D (tamanho, pico e temperatura relatados): título ou DOI para o detalhe ao clicar
    tri = L.dropna(subset=["size_nm", "peak_nm", "T_C"])
    tri_ref = {"idx": [int(i) for i in np.flatnonzero(L.index.isin(tri.index))],
               "title": [txt(t).replace(" _ ", " — ")[:160] for t in tri["title"]],
               "doi": [txt(d) for d in tri["doi"]]}
    by_year = (L.dropna(subset=["year"]).assign(red=lambda x: x["reductant"])
               .groupby(["year", "red"]).size().unstack(fill_value=0))
    return {"records": rec, "n": int(len(L)), "n_doi": int(L.loc[L["doi"] != "", "doi"].nunique()),
            "sources": list(expdata.SOURCES.values()), "reductants": expdata.REDUCTANTS, "capping": expdata.CAPPING,
            "morph": expdata.MORPH, "go_rows": go_rows, "n_go": int(len(g)), "tri_ref": tri_ref,
            "n_by_source": {expdata.SOURCES[k]: int(v) for k, v in L["source"].value_counts().items()},
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
    # conferência com a literatura: curva empírica de Haiss et al. (Anal. Chem. 2007, 79, 4215), λ = 512 + 6,53·e^(0,0216 d)
    # para d > 25 nm; e teste de um índice efetivo do meio (camada de ligante), ajustado em metade dos ARTIGOS e
    # avaliado na outra metade — adotado só se melhorar a validação
    hd = np.arange(25.0, 101.0, 5.0)
    haiss = 512 + 6.53 * np.exp(0.0216 * hd)
    mie_h = np.interp(np.log(hd), np.log(d), lam)
    clus = np.where(sph["doi"] != "", sph["doi"], sph["title"])
    rng = np.random.default_rng(7)
    uc = np.unique(clus)
    cal = np.isin(clus, rng.choice(uc, len(uc) // 2, replace=False))
    dsub = np.exp(np.linspace(np.log(3.0), np.log(160.0), 60))
    neff = []
    for nm in (1.333, 1.345, 1.36, 1.375, 1.39):
        Cn = np.array([mie.extinction_cross_section(wl, x, "Au", nm) for x in dsub])

        def en(dc, Cn=Cn):
            sg = np.sqrt(np.log(1 + 0.01))
            w = np.exp(-0.5 * ((np.log(dsub) - (np.log(dc) - sg ** 2 / 2)) / sg) ** 2)
            return (w / w.sum()) @ Cn
        ln_ = np.array([_peak(wl, en(x)) for x in dsub])
        rs = sph["peak_nm"].to_numpy() - np.interp(np.log(sph["size_nm"]), np.log(dsub), ln_)
        neff.append({"n": nm, "cal": float(np.median(np.abs(rs[cal]))), "val": float(np.median(np.abs(rs[~cal]))),
                     "bias_val": float(np.median(rs[~cal])),
                     "haiss_max": float(np.max(np.abs(np.interp(np.log(hd), np.log(dsub), ln_) - haiss)))})
    inversion = _peak_inversion(sph, d, lam)
    return {"inversion": inversion, "wl": _r(wl, 0), "d": _r(d, 3), "C_ext": _r(C / C.max(axis=1, keepdims=True), 4),
            "haiss": {"d": _r(hd, 1), "lambda": _r(haiss, 1), "mie": _r(mie_h, 1),
                      "max_abs_diff": float(np.max(np.abs(mie_h - haiss))), "mie_20nm": float(np.interp(np.log(20), np.log(d), lam))},
            "n_eff_test": neff,
            "C_ext_max": _r(C.max(axis=1), 2), "per_volume_max": _r(C.max(axis=1) / vol, 5),
            "lspr_curve": {"d": _r(d, 3), "lambda": _r(lam, 1), "sigma": 0.10},
            "lit_spheres": {"size": _r(sph["size_nm"], 2), "peak": _r(sph["peak_nm"], 1),
                            "source": sph["source"].map(expdata.SOURCES).tolist(), "doi": sph["doi"].tolist(),
                            "title": [str(t).replace(" _ ", " — ")[:160] if isinstance(t, str) else "" for t in sph["title"]],
                            "n": int(len(sph)), "median_abs_residual": float(np.median(np.abs(res))),
                            "within_5nm": float(np.mean(np.abs(res) <= 5)), "by_bin": by_bin},
            "target": {"wl": _r(tw, 0), "E": _r(te / te.max(), 4), "diameter": cfg["target_spectrum"]["diameter_nm"],
                       "sigma": cfg["target_spectrum"]["relative_dispersion"], "normalization": norm, "s_m": sm,
                       "grid": [float(grid[0]), float(grid[-1]), float(grid[1] - grid[0])]},
            "J_surface": {"d": _r(dd, 2), "sigma": _r(ss, 3), "log10J": _r(np.log10(Jg), 3)}}


def _inv_model(size: np.ndarray, peak: np.ndarray, gd: np.ndarray, lam_g: np.ndarray) -> dict:
    """Peças da inversão ajustadas num conjunto de registros: a priori (KDE em ln d) e o resíduo pico − Mie por faixa
    de tamanho (viés = mediana, dispersão = 1,4826·MAD, mínimo 2 nm), interpolados na grade."""
    ls = np.log(size)
    bw = 1.06 * np.std(ls) * len(ls) ** -0.2
    prior = np.exp(-0.5 * ((np.log(gd)[:, None] - ls[None]) / bw) ** 2).sum(1)
    prior /= prior.sum()
    res = peak - np.interp(ls, np.log(gd), lam_g)
    edges = np.array([2, 10, 20, 40, 80, 200.0])
    cen, bias, sd = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (size >= lo) & (size < hi)
        if m.sum() >= 8:
            r = res[m]
            cen.append(np.sqrt(lo * hi))
            bias.append(float(np.median(r)))
            sd.append(max(2.0, 1.4826 * float(np.median(np.abs(r - np.median(r))))))
    lc = np.log(cen)
    return {"prior": prior, "bias": np.interp(np.log(gd), lc, bias), "sd": np.interp(np.log(gd), lc, sd)}


def _posterior(M: dict, lam_g: np.ndarray, pk: float, uniform: bool = False, nu: float = 0) -> np.ndarray:
    z = (pk - lam_g - M["bias"]) / M["sd"]
    # nu = 0: gaussiana; nu > 0: t de Student (caudas pesadas dos relatos: pico lido no olho, tamanho por outra técnica)
    lik = (np.exp(-0.5 * z ** 2) if nu <= 0 else (1 + z ** 2 / nu) ** (-(nu + 1) / 2)) / M["sd"]
    post = lik * (1.0 if uniform else M["prior"])
    return post / post.sum()


def _peak_inversion(sph: pd.DataFrame, d: np.ndarray, lam: np.ndarray) -> dict:
    """Do pico de absorção (UV-Vis) ao tamanho, por Bayes: a priori = tamanhos de esferas relatados (KDE em ln d),
    verossimilhança = Mie + resíduo empírico por faixa (o que o relato real erra, não só a física). Intervalos de
    credibilidade de 90 % conferidos em 5 dobras por ARTIGO (a priori e o resíduo vêm só das outras dobras)."""
    from sklearn.model_selection import GroupKFold
    gd = np.exp(np.linspace(np.log(2.0), np.log(200.0), 240))
    lam_g = np.interp(np.log(gd), np.log(d), lam)
    size, peak = sph["size_nm"].to_numpy(float), sph["peak_nm"].to_numpy(float)
    groups = np.where(sph["doi"] != "", sph["doi"], sph["title"])
    # escolha da verossimilhança por critério fixado antes: cobertura do IC de 90 % mais perto de 90 % nos artigos
    # de teste (gaussiana × t de Student com ν = 10, 5, 3, 2)
    folds = list(GroupKFold(5).split(size, peak, groups))
    Ms = [(_inv_model(size[tr], peak[tr], gd, lam_g), te) for tr, te in folds]

    def check(nu, uniform=False):
        hit, width = [], []
        for M, te in Ms:
            for i in te:
                c = np.cumsum(_posterior(M, lam_g, peak[i], uniform, nu))
                lo, hi = gd[np.searchsorted(c, 0.05)], gd[min(np.searchsorted(c, 0.95), len(gd) - 1)]
                hit.append(lo <= size[i] <= hi)
                width.append(hi / lo)
        return float(np.mean(hit)), float(np.median(width))
    scan = [{"nu": nu, "coverage90": cv, "median_width": wd} for nu in (0, 10, 5, 3, 2) for cv, wd in [check(nu)]]
    best = min(scan, key=lambda r: abs(r["coverage90"] - 0.9))
    cov_u, _ = check(best["nu"], True)
    M = _inv_model(size, peak, gd, lam_g)
    return {"d": _r(gd, 3), "lam": _r(lam_g, 2), "prior": _r(M["prior"], 6), "bias": _r(M["bias"], 2), "sd": _r(M["sd"], 2),
            "nu": best["nu"], "scan": scan, "coverage90": best["coverage90"], "coverage90_uniform": cov_u,
            "median_width": best["median_width"], "n": int(len(size)), "n_articles": int(len(np.unique(groups)))}


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
    return {"model_comparison": _gp_model_comparison(Xn, y, u), "do_effects": _do_effects(m, Xn, lo, hi, cols),
            "columns": cols, "labels": [expdata.AGNP_LABELS[c] for c in cols], "lo": lo.tolist(), "hi": hi.tolist(),
            "points": {"X": _r(X, 3), "mean": _r(u["mean"], 4), "sd": _r(u["std"], 4), "n": u["count"].tolist()},
            "n_measurements": int(len(raw)), "n_conditions": int(len(u)), "gp": gp,
            "cv": {"obs": _r(y, 4), "pred": _r(cv_mu, 4), "sd": _r(sd_tot, 4), "r2": float(r2),
                   "rmse": float(np.sqrt(np.mean(resid ** 2))), "coverage95": cover},
            "best_measured": {"x": _r(X[ib], 3), "loss": float(u["mean"].iloc[ib]), "sd": float(u["std"].iloc[ib])},
            "suggestions": sugg, "ei_note": "EI sobre ln(perda), 4096 candidatos Sobol, 5 escolhas a ≥ 0,15 entre si"}


def _gp_model_comparison(Xn: np.ndarray, y: np.ndarray, u: pd.DataFrame) -> list[dict]:
    """Escolha do modelo por validação cruzada (10 dobras, mesmas dobras para todos), critério fixado antes:
    log-verossimilhança preditiva (NLPD, menor é melhor) com o ruído incluído. Candidatos: núcleos Matérn-1/2, 3/2,
    5/2 (o da proposta) e RBF, todos com ARD e o mesmo prior de comprimento; e o 5/2 com o ruído MEDIDO de cada
    condição (erro-padrão da média das réplicas, em ln) no lugar do ruído aprendido."""
    import math
    import torch
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Standardize
    from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
    from gpytorch.mlls import ExactMarginalLogLikelihood
    from gpytorch.priors import LogNormalPrior
    p_ = Xn.shape[1]
    pr = lambda: LogNormalPrior(math.sqrt(2) + math.log(p_) / 2, math.sqrt(3))  # noqa: E731
    yvar = np.maximum((u["std"].fillna(0).to_numpy() / u["mean"].to_numpy()) ** 2 / u["count"].to_numpy(), 1e-6)
    cands = [("Matérn-5/2 (proposta)", lambda: MaternKernel(nu=2.5, ard_num_dims=p_, lengthscale_prior=pr()), False),
             ("Matérn-3/2", lambda: MaternKernel(nu=1.5, ard_num_dims=p_, lengthscale_prior=pr()), False),
             ("Matérn-1/2", lambda: MaternKernel(nu=0.5, ard_num_dims=p_, lengthscale_prior=pr()), False),
             ("RBF", lambda: RBFKernel(ard_num_dims=p_, lengthscale_prior=pr()), False),
             ("Matérn-5/2 com ruído medido das réplicas", lambda: MaternKernel(nu=2.5, ard_num_dims=p_, lengthscale_prior=pr()), True)]
    idx = np.random.default_rng(20261004).permutation(len(y))
    folds = np.array_split(idx, 10)
    out = []
    for name, kern, het in cands:
        mu, var = np.empty(len(y)), np.empty(len(y))
        for f in folds:
            tr = np.setdiff1d(idx, f)
            m = SingleTaskGP(torch.tensor(Xn[tr]), torch.tensor(y[tr][:, None]),
                             train_Yvar=torch.tensor(yvar[tr][:, None]) if het else None,
                             covar_module=ScaleKernel(kern()), outcome_transform=Standardize(1))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit_gpytorch_mll(ExactMarginalLogLikelihood(m.likelihood, m))
            with torch.no_grad():
                pst = m.posterior(torch.tensor(Xn[f]), observation_noise=not het)
            mu[f] = pst.mean.detach().numpy().ravel()
            var[f] = pst.variance.detach().numpy().ravel() + (yvar[f] if het else 0)
        r = y - mu
        out.append({"model": name, "r2": float(1 - np.sum(r ** 2) / np.sum((y - y.mean()) ** 2)),
                    "rmse": float(np.sqrt(np.mean(r ** 2))), "coverage95": float(np.mean(np.abs(r) <= 1.96 * np.sqrt(var))),
                    "nlpd": float(np.mean(0.5 * np.log(2 * np.pi * var) + r ** 2 / (2 * var)))})
    out[0]["replicate_se_median"] = float(np.median(np.sqrt(yvar)))
    return out


def _do_effects(m, Xn: np.ndarray, lo: np.ndarray, hi: np.ndarray, cols: list[str]) -> list[dict]:
    """Efeito INTERVENCIONAL médio de aumentar cada vazão em 10 % da faixa, do(x_j + 0,1), sobre ln(perda), média nas
    condições medidas em que o aumento cabe na faixa. Na campanha as vazões são fixadas pelo experimentador (não há
    confundidor entre elas e o resultado), então o contraste do GP estima o efeito causal dentro do domínio medido.
    Incerteza: covariância conjunta do posterior em (x, x + δ)."""
    import torch
    out = []
    for j, c in enumerate(cols):
        ok = Xn[:, j] <= 0.9
        X0 = Xn[ok]
        X1 = X0.copy()
        X1[:, j] += 0.1
        with torch.no_grad():
            pst = m.posterior(torch.tensor(np.vstack([X0, X1])))
            mu = pst.mean.detach().numpy().ravel()
            S = pst.covariance_matrix.detach().numpy().reshape(2 * len(X0), 2 * len(X0))
        n = len(X0)
        dmu = mu[n:] - mu[:n]
        a = np.concatenate([-np.ones(n), np.ones(n)]) / n
        sd = float(np.sqrt(max(a @ S @ a, 0)))
        ace = float(dmu.mean())
        out.append({"var": expdata.AGNP_LABELS[c], "step": float(0.1 * (hi[j] - lo[j])), "ace_ln": ace, "sd": sd,
                    "ratio": float(np.exp(ace)), "ratio_ci95": [float(np.exp(ace - 1.96 * sd)), float(np.exp(ace + 1.96 * sd))],
                    "frac_improve": float(np.mean(dmu < 0)), "n": int(n)})
    return out


def add_calibration(designer: dict) -> dict:
    """Calibração probabilística do GP nas previsões fora da dobra: cobertura de cada intervalo central (curva de
    confiabilidade), histograma do PIT = Φ((y − μ)/σ) (uniforme se calibrado), CRPS gaussiano (Gneiting & Raftery
    2007) e a mesma conta para um modelo de referência com σ constante (o RMSE), para saber se a incerteza por
    condição acrescenta informação."""
    from scipy.stats import norm
    cv = designer["cv"]
    y, mu, sd = (np.asarray(cv[k], float) for k in ("obs", "pred", "sd"))
    z = (y - mu) / sd
    lv = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99])

    def crps(z_, s_):
        return float(np.mean(s_ * (z_ * (2 * norm.cdf(z_) - 1) + 2 * norm.pdf(z_) - 1 / np.sqrt(np.pi))))
    s0 = float(np.sqrt(np.mean((y - mu) ** 2)))
    pit = norm.cdf(z)
    hist = np.histogram(pit, bins=10, range=(0, 1))[0]
    from scipy.stats import kstest
    designer["calibration"] = {
        "levels": lv.tolist(), "coverage": _r([np.mean(np.abs(z) <= norm.ppf(0.5 + q / 2)) for q in lv], 4),
        "coverage_const": _r([np.mean(np.abs(y - mu) / s0 <= norm.ppf(0.5 + q / 2)) for q in lv], 4),
        "pit_hist": hist.tolist(), "pit_ks_p": float(kstest(pit, "uniform").pvalue),
        "crps": crps(z, sd), "crps_const": crps((y - mu) / s0, np.full_like(sd, s0)),
        "mean_width95": float(np.mean(2 * 1.96 * sd)), "z_sd": float(np.std(z, ddof=1))}
    return designer


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


def benchmark(seeds: int = 40, budget: int = 60, workers: int = 4) -> dict:
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


def add_paired_stats(bench: dict) -> dict:
    """Comparação PAREADA com o aleatório: a semente s sorteia as mesmas 5 condições iniciais em todos os braços.
    Campanha que não chegou ao top 5 % conta como orçamento + 1 (censura à direita, conservadora para o braço)."""
    from scipy.stats import wilcoxon
    for ds in bench["datasets"].values():
        cap = ds["budget"] + 1
        h = {a: np.array([cap if v is None else v for v in ds["reach_top5"][a]["per_seed"]], float) for a in bench["arms"]}
        ds["median_censored"] = {a: float(np.median(h[a])) for a in bench["arms"]}
        ds["paired"] = {}
        for a in bench["arms"][1:]:
            d = h[a] - h["Aleatório"]
            p = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
            ds["paired"][a] = {"wins": int(np.sum(d < 0)), "ties": int(np.sum(d == 0)), "losses": int(np.sum(d > 0)),
                               "median_diff": float(np.median(d)), "p": p}
        ds["survival"] = _survival(ds["reach_top5"], bench["arms"], ds["budget"])
    # Holm (1979) na família inteira (campanhas × estratégias): controla a chance de QUALQUER falso positivo
    fam = [(ds, a) for ds in bench["datasets"].values() for a in bench["arms"][1:]]
    order = np.argsort([ds["paired"][a]["p"] for ds, a in fam])
    m, run = len(fam), 0.0
    for rank, k in enumerate(order):
        ds, a = fam[k]
        run = max(run, min(1.0, (m - rank) * ds["paired"][a]["p"]))
        ds["paired"][a]["p_holm"] = float(run)
    return bench


def _km(times: np.ndarray, event: np.ndarray, horizon: int) -> dict:
    """Kaplan–Meier de "ainda não chegou ao top 5 %" após t experimentos (t = 0…horizonte), com IC 95 % de Greenwood
    na escala log(−log) (Kalbfleisch & Prentice)."""
    S, lo, hi, s, gw = [1.0], [1.0], [1.0], 1.0, 0.0
    for t in range(1, horizon + 1):
        n = int(np.sum(times >= t))                                   # em risco no início do passo t
        d = int(np.sum((times == t) & event))
        if n > 0 and d > 0:
            s *= 1 - d / n
            gw += d / (n * (n - d)) if n > d else 0.0
        if 0 < s < 1 and gw > 0:
            c = 1.96 * np.sqrt(gw) / abs(np.log(s))
            lo.append(float(s ** np.exp(c)))
            hi.append(float(s ** np.exp(-c)))
        else:
            lo.append(float(s))
            hi.append(float(s))
        S.append(float(s))
    return {"S": _r(S, 4), "lo": _r(lo, 4), "hi": _r(hi, 4)}


def _logrank(t1, e1, t0, e0) -> float:
    """Teste log-rank (Mantel–Haenszel) entre dois braços; p bilateral (qui-quadrado, 1 gl)."""
    from scipy.stats import chi2
    O_E, V = 0.0, 0.0
    for t in np.unique(np.concatenate([t1[e1], t0[e0]])):
        n1, n0 = np.sum(t1 >= t), np.sum(t0 >= t)
        d1, d0 = np.sum((t1 == t) & e1), np.sum((t0 == t) & e0)
        n, d = n1 + n0, d1 + d0
        if n < 2:
            continue
        O_E += d1 - d * n1 / n
        V += d * (n1 / n) * (1 - n1 / n) * (n - d) / (n - 1)
    return float(chi2.sf(O_E ** 2 / V, 1)) if V > 0 else 1.0


def _survival(reach: dict, arms: list, budget: int, seed: int = 5) -> dict:
    """Experimentos até o top 5 % como tempo até o evento: campanha que não chegou é CENSURADA no orçamento (não é
    "orçamento + 1"). Curvas de Kaplan–Meier, log-rank contra o aleatório e o tempo médio restrito (RMST =
    E[min(T, orçamento)] = área sob S) com a diferença PAREADA por semente: IC por bootstrap e P(braço < aleatório) por
    bootstrap bayesiano (pesos de Dirichlet nas sementes; Rubin 1981)."""
    rng = np.random.default_rng(seed)
    T = {a: np.array([budget if v is None else v for v in reach[a]["per_seed"]], float) for a in arms}
    E = {a: np.array([v is not None for v in reach[a]["per_seed"]]) for a in arms}
    out = {"t": list(range(budget + 1)), "km": {}, "rmst": {}, "vs_random": {}}
    for a in arms:
        out["km"][a] = _km(T[a], E[a], budget)
        out["rmst"][a] = float(np.sum(out["km"][a]["S"][:budget]))      # Σ_{t<orçamento} S(t) = E[min(T, orçamento)]
    n = len(T[arms[0]])
    W = rng.dirichlet(np.ones(n), 4000)
    idx = rng.integers(0, n, (4000, n))
    for a in arms[1:]:
        d = np.minimum(T[a], budget) - np.minimum(T[arms[0]], budget)      # mesma semente = mesma partida
        boot = d[idx].mean(1)
        post = W @ d
        out["vs_random"][a] = {"rmst_diff": float(d.mean()), "ci95": _r(np.quantile(boot, [0.025, 0.975]), 2),
                               "p_better": float(np.mean(post < 0)), "logrank_p": _logrank(T[a], E[a], T[arms[0]], E[arms[0]])}
    return out


# ---------------------------------------------------------------------------------------------- §4.13 SHAP

LIT_RED = {"trisodium_citrate": "citrato", "NaBH4": "NaBH₄", "ascorbic_acid": "ácido ascórbico", "tannic_acid": "ácido tânico",
           "H2O2": "H₂O₂", "hydroxylamine_HCl": "hidroxilamina", "hydroquinone": "hidroquinona", "hydrazine": "hidrazina",
           "THPC": "THPC", "glucose": "glicose"}
LIT_CAP = {"CTAB": ("CTAB",), "CTAC": ("CTAC",), "PVP": ("PVP",), "PEG": ("PEG",), "tiol (GSH/dodecanotiol)": ("GSH", "dodecanethiol"),
           "TOAB": ("TOAB",), "BSA": ("BSA",), "oleilamina": ("oleylamine",), "ácido oleico": ("oleic_acid",)}


def _lit_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Registros da literatura com tamanho de 1 a 300 nm e as 28 variáveis do modelo de tamanho: presença de cada
    reagente citado, rota, forma, temperatura, ano, menção a GO e base de origem."""
    L = expdata.literature()
    L = L[L["size_nm"].between(1, 300)].copy()
    has = lambda col, *ks: L[col].fillna("").str.split("|").apply(lambda xs: any(k in xs for k in ks))  # noqa: E731
    Fl = {lab: has("reductants_raw", k) for k, lab in LIT_RED.items()}
    Fl.update({lab: has("capping_raw", *ks) for lab, ks in LIT_CAP.items()})
    Fl.update({"mediada por sementes": L["seed"].eq(1), "temperatura (°C)": L["T_C"], "ano": L["year"],
               "forma não esférica": ~L["morph"].isin([0, 2, 14, -1]), "bastão": L["morph"].eq(expdata.MORPH.index("rod")),
               "aglomerado": L["morph"].eq(expdata.MORPH.index("cluster")), "menciona GO": L["go"].eq(1),
               "base NSP": L["source"].eq("nsp2026"), "base AuNC": L["source"].eq("aunc2025")})
    return L, pd.DataFrame({k: np.asarray(v, float) for k, v in Fl.items()}, index=L.index)

def _sobol(gp: dict, p: int, N: int = 4096, B: int = 400, seed: int = 3) -> dict:
    """Índices de Sobol da média do GP sobre a caixa medida (entradas uniformes e independentes em [0, 1]^p):
    primeira ordem S1 (estimador de Saltelli 2010) e total ST (Jansen 1999) com amostras de Sobol (quase Monte
    Carlo) e IC 95 % por bootstrap das linhas. ST − S1 = parte do efeito que só aparece em interação."""
    from scipy.stats import qmc
    rng = np.random.default_rng(seed)
    AB = qmc.Sobol(2 * p, scramble=True, seed=seed).random(N)
    A_, B_ = AB[:, :p], AB[:, p:]
    f = lambda Z: gp_predict(gp, Z)[0]                                         # noqa: E731
    fA, fB = f(A_), f(B_)
    fAB = []
    for i in range(p):
        Z = A_.copy()
        Z[:, i] = B_[:, i]
        fAB.append(f(Z))
    fAB = np.array(fAB)

    def est(ix):
        V = np.var(np.concatenate([fA[ix], fB[ix]]))
        s1 = np.mean(fB[ix] * (fAB[:, ix] - fA[ix]), 1) / V
        st = 0.5 * np.mean((fA[ix] - fAB[:, ix]) ** 2, 1) / V
        return s1, st
    s1, st = est(np.arange(N))
    bs = [est(rng.integers(0, N, N)) for _ in range(B)]
    q = lambda k: np.quantile(np.array([b[k] for b in bs]), [0.025, 0.975], axis=0)  # noqa: E731
    l1, lt = q(0), q(1)
    return {"S1": _r(s1, 4), "ST": _r(st, 4), "S1_ci": _r(l1.T, 4), "ST_ci": _r(lt.T, 4), "N": N,
            "sum_S1": float(np.sum(s1)), "var_explained_by_main": float(np.sum(s1))}


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
                    "H2": _r(H, 3), "target": "ln(perda espectral) prevista pelo GP", "sobol": _sobol(gp, p)}}
    # AuNC: deslocamento de Stokes (emissão − excitação); ver variability() para a comparação com o alvo direto
    from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
    c = expdata.aunc()
    c = c[c["exc_nm"].notna()].copy()
    feats = ["size_nm", "exc_nm", "T_C", "time_h", "pH"]
    c = c.assign(GSH=(c["ligand"].str.upper() == "GSH").astype(float),
                 water=(c["solvent"] == "water").astype(float))
    F = feats + ["GSH", "water"]
    ys = (c["em_nm"] - c["exc_nm"]).to_numpy(float)
    hgb = lambda: HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0)  # noqa: E731
    m = hgb().fit(c[F], ys)
    pred_cv = cross_val_predict(hgb(), c[F], ys, cv=KFold(5, shuffle=True, random_state=0)) + c["exc_nm"].to_numpy()
    tsv = shap.TreeExplainer(m).shap_values(c[F])
    em = c["em_nm"].to_numpy(float)
    out["aunc"] = {"features": ["tamanho (nm)", "λ exc (nm)", "T síntese (°C)", "tempo (h)", "pH", "ligante GSH",
                                "solvente água"], "values": _r(tsv, 3), "X": _r(c[F].to_numpy(float), 2),
                   "target": "deslocamento de Stokes (nm)",
                   "cv_r2": float(1 - np.sum((em - pred_cv) ** 2) / np.sum((em - em.mean()) ** 2))}
    # literatura: ln(tamanho) com TODOS os reagentes citados (presença/ausência), morfologia, rota, base e época;
    # validação por ARTIGO (DOI ou, no NSP, título): registros do mesmo artigo nunca ficam em treino e teste juntos
    L, Xl = _lit_features()
    yl = np.log(L["size_nm"].to_numpy(float))
    groups = np.where(L["doi"] != "", L["doi"], L["title"])
    pcv = cross_val_predict(hgb(), Xl, yl, cv=GroupKFold(5), groups=groups)
    old = pd.DataFrame({"citrato": L["reductant"].eq(0), "NaBH4": L["reductant"].eq(1), "ascórbico": L["reductant"].eq(2),
                        "sementes": L["seed"].eq(1), "CTAB": L["capping"].eq(0), "PVP": L["capping"].eq(1),
                        "tiol": L["capping"].isin([4, 8]), "T": L["T_C"], "não esférica": ~L["morph"].isin([0, 2, 14, -1])}).astype(float)
    pold = cross_val_predict(hgb(), old, yl, cv=GroupKFold(5), groups=groups)
    boot = _r2_boot(yl, {"28 variáveis": pcv, "9 variáveis": pold}, groups, B=500)
    gl = hgb().fit(Xl, yl)
    samp = R.choice(len(Xl), min(1500, len(Xl)), replace=False)
    lsv = shap.TreeExplainer(gl).shap_values(Xl.iloc[samp])
    top = np.argsort(-np.abs(lsv).mean(0))[:14]                      # as 14 mais influentes (a figura fica legível)
    out["literature"] = {"features": [Xl.columns[j] for j in top], "values": _r(lsv[:, top], 3),
                         "X": _r(Xl.iloc[samp].to_numpy(float)[:, top], 1), "target": "ln(tamanho, nm)", "n": int(len(Xl)),
                         "n_features": int(Xl.shape[1]), "n_articles": int(len(np.unique(groups))),
                         "cv_r2_by_paper": float(1 - np.sum((yl - pcv) ** 2) / np.sum((yl - yl.mean()) ** 2)),
                         "boot": boot}
    return out


# ---------------------------------------------------------------------------------------------- §4.18 preditor de síntese

def _hgb_export(m) -> dict:
    """Árvores de um HistGradientBoostingRegressor em vetores planos (o navegador soma as folhas: previsão =
    base + Σ folha; a taxa de aprendizado já está aplicada nas folhas)."""
    f, t, lft, rgt, v, ms, roots = [], [], [], [], [], [], []
    for it in m._predictors:
        nd, off = it[0].nodes, len(f)
        roots.append(off)
        for x in nd:
            leaf = bool(x["is_leaf"])
            f.append(-1 if leaf else int(x["feature_idx"]))
            thr = float(x["num_threshold"])                         # ±inf (só os ausentes vão para um lado) → ±1e300 no JSON
            t.append(0.0 if leaf else (round(thr, 6) if np.isfinite(thr) else float(np.sign(thr)) * 1e300))
            lft.append(0 if leaf else off + int(x["left"]))
            rgt.append(0 if leaf else off + int(x["right"]))
            v.append(round(float(x["value"]), 6) if leaf else 0.0)
            ms.append(int(x["missing_go_to_left"]))
    return {"base": float(np.ravel(m._baseline_prediction)[0]), "roots": roots, "f": f, "t": t, "l": lft, "r": rgt, "v": v, "m": ms}


def hgb_predict(ex: dict, X: np.ndarray) -> np.ndarray:
    """Mesma conta que o navegador faz com _hgb_export (usada no teste de equivalência)."""
    out = np.full(len(X), ex["base"])
    for i, x in enumerate(np.asarray(X, float)):
        acc = 0.0
        for r in ex["roots"]:
            k = r
            while ex["f"][k] >= 0:
                xv = x[ex["f"][k]]
                k = (ex["l"][k] if ex["m"][k] else ex["r"][k]) if np.isnan(xv) else (ex["l"][k] if xv <= ex["t"][k] else ex["r"][k])
            acc += ex["v"][k]
        out[i] += acc
    return out


def predictor() -> dict:
    """Preditor de síntese: dado o protocolo (reagentes, rota, forma, temperatura, ano, GO), a distribuição do tamanho
    relatado na literatura, por regressão quantílica com árvores (q = 5, 25, 50, 75, 95 % de ln d) CONFORMALIZADA por
    artigo (CQR; Romano et al. 2019): os escores fora da dobra (GroupKFold por artigo) recebem peso 1/nº de registros do
    artigo, então a cobertura prometida vale para um ARTIGO novo, não para um parágrafo a mais de um artigo já visto.
    A cobertura é conferida em validação cruzada aninhada. Junto vão as receitas da literatura (mesma combinação de
    reagentes, rota e forma) com mediana, faixa e exemplos, para o navegador mostrar as vizinhas."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold
    L, X = _lit_features()
    y = np.log(L["size_nm"].to_numpy(float))
    groups = np.where(L["doi"] != "", L["doi"], L["title"])
    Q = [0.05, 0.25, 0.5, 0.75, 0.95]

    def mk(q):
        return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200, max_depth=3, learning_rate=0.05,
                                             min_samples_leaf=20, random_state=0)
    oof, fold = {q: np.zeros(len(y)) for q in Q}, np.zeros(len(y), int)
    for k, (tr, te) in enumerate(GroupKFold(5).split(X, y, groups)):
        fold[te] = k
        for q in Q:
            oof[q][te] = mk(q).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    _, inv, cnt = np.unique(groups, return_inverse=True, return_counts=True)
    w = 1.0 / cnt[inv]

    def wquant(e, ww, lev):                                         # quantil ponderado (artigos com o mesmo peso)
        o = np.argsort(e)
        cw = np.cumsum(ww[o]) / ww.sum()
        return float(e[o][min(np.searchsorted(cw, lev), len(e) - 1)])
    bands = {}
    for name, lo, hi, lev in (("50", 0.25, 0.75, 0.5), ("90", 0.05, 0.95, 0.9)):
        E = np.maximum(oof[lo] - y, y - oof[hi])
        cov_rec, cov_art = [], []
        for k in range(5):                                          # aninhado: o ajuste conformal não vê a dobra k
            m = fold != k
            inside = E[~m] <= wquant(E[m], w[m], lev)
            cov_rec.append(float(inside.mean()))
            cov_art.append(float(np.average(inside, weights=w[~m])))
        qa = wquant(E, w, lev)
        bands[name] = {"q_lo": lo, "q_hi": hi, "level": lev, "Q": qa, "coverage_records": float(np.mean(cov_rec)),
                       "coverage_articles": float(np.mean(cov_art)), "coverage_uncorrected": float(np.mean((y >= oof[lo]) & (y <= oof[hi]))),
                       "median_fold_width": float(np.exp(np.median(oof[hi] - oof[lo] + 2 * qa)))}
    models = {str(q): _hgb_export(mk(q).fit(X, y)) for q in Q}
    # receitas: mesma combinação de reagentes, rota e forma
    cat = [c for c in X.columns if c not in ("temperatura (°C)", "ano", "base NSP", "base AuNC", "menciona GO")]
    sig = X[cat].astype(int).astype(str).agg("".join, axis=1).to_numpy()
    ref = np.where(L["doi"] != "", L["doi"], L["title"].fillna("").str.replace(" _ ", " — ").str.slice(0, 110))
    rec = []
    for sg in pd.unique(sig):
        ix = np.flatnonzero(sig == sg)
        d = L["size_nm"].to_numpy(float)[ix]
        arts = pd.unique(groups[ix])
        ex = list(dict.fromkeys(ref[ix]))[:3]
        rec.append({"sig": sg, "n": int(len(ix)), "n_art": int(len(arts)), "median": round(float(np.median(d)), 1),
                    "q10": round(float(np.quantile(d, 0.1)), 1), "q90": round(float(np.quantile(d, 0.9)), 1), "ex": ex})
    rec.sort(key=lambda r: -r["n"])
    return {"features": list(X.columns), "categorical": cat, "models": models, "bands": bands,
            "n": int(len(y)), "n_articles": int(len(cnt)), "recipes": rec,
            "defaults": {"temperatura (°C)": 100.0, "ano": 2020.0},
            "pinball_oof": {str(q): float(np.mean(np.maximum(q * (y - oof[q]), (q - 1) * (y - oof[q])))) for q in Q}}


# ---------------------------------------------------------------------------------------------- §4.17/§4.18 ruído e variabilidade multi-fonte

def _r2_boot(y: np.ndarray, preds: dict, groups: np.ndarray, B: int = 1000, seed: int = 11) -> dict:
    """IC 95 % do R² de cada modelo e da diferença pareada (primeiro − segundo), reamostrando ARTIGOS inteiros
    (as previsões fora da dobra são fixas; a incerteza é a da amostra de artigos)."""
    rng = np.random.default_rng(seed)
    ug, inv = np.unique(groups, return_inverse=True)
    names = list(preds)
    P = np.array([np.asarray(preds[k], float) for k in names])
    # somas por artigo: R² = 1 − SSE/SST, com SST = Σy² − (Σy)²/n — tudo somável por grupo
    def sums(v):
        return np.bincount(inv, v, minlength=len(ug))
    n_g, y_g, y2_g = sums(np.ones_like(y)), sums(y), sums(y * y)
    sse_g = np.array([sums((y - p) ** 2) for p in P])
    W = rng.multinomial(len(ug), np.full(len(ug), 1 / len(ug)), size=B).astype(float)   # nº de cópias de cada artigo
    n, sy, sy2 = W @ n_g, W @ y_g, W @ y2_g
    sst = sy2 - sy * sy / n
    r2 = 1 - (W @ sse_g.T) / sst[:, None]                                             # B × modelos
    out = {k: {"r2": float(1 - np.sum((y - P[i]) ** 2) / np.sum((y - y.mean()) ** 2)),
               "ci95": _r(np.quantile(r2[:, i], [0.025, 0.975]), 3)} for i, k in enumerate(names)}
    if len(names) == 2:
        d = r2[:, 0] - r2[:, 1]
        out["diff"] = {"value": out[names[0]]["r2"] - out[names[1]]["r2"], "ci95": _r(np.quantile(d, [0.025, 0.975]), 3),
                       "p_le_0": float(np.mean(d <= 0))}
    return out


def variability() -> dict:
    from scipy import stats
    raw, u = expdata.agnp()
    cols = list(raw.columns[:-1])
    groups = [g["loss"].to_numpy() for _, g in raw.groupby(cols, sort=False)]
    lev = stats.levene(*groups, center="median")
    slope = np.polyfit(np.log(u["mean"]), np.log(u["std"].clip(lower=1e-6)), 1)[0]
    within = np.mean([g.var(ddof=1) for g in groups])
    between = np.var(u["mean"], ddof=1)
    # literatura: Turkevich (citrato como ÚNICO redutor citado, sem sementes, esfera/partícula) — variação entre artigos;
    # "citrato citado primeiro" deixaria entrar sínteses com NaBH₄ ou ascórbico junto (outra rota, partículas menores)
    L = expdata.literature()
    only_citr = _has(L["reductants_raw"], "trisodium_citrate") & ~_has(
        L["reductants_raw"], *[r for r in expdata.REDUCTANTS if r != "trisodium_citrate"])
    t = L[only_citr & L["seed"].eq(0) & L["morph"].isin([0, 14]) & L["size_nm"].between(3, 120)
          & (L["doi"] != "")].copy()
    per_paper = t.groupby("doi")["size_nm"].median()             # Cruse: tamanho é do ARTIGO (repete nos parágrafos)
    ly = np.log(per_paper.to_numpy())
    # AuNC: generalização para artigo novo (GroupKFold por DOI) × divisão aleatória
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
    # alvo: deslocamento de Stokes (emissão − excitação), devolvido em λ de emissão; comparado com prever a emissão
    # direto, nas MESMAS sínteses (as 5 sem λ de excitação ficam fora das duas)
    c = expdata.aunc()
    c = c[c["exc_nm"].notna()].copy()
    c = c.assign(GSH=(c["ligand"].str.upper() == "GSH").astype(float), water=(c["solvent"] == "water").astype(float))
    F = ["size_nm", "exc_nm", "T_C", "time_h", "pH", "GSH", "water"]
    g = HistGradientBoostingRegressor(max_iter=300, max_depth=3, learning_rate=0.05, min_samples_leaf=5, random_state=0)
    em, exc = c["em_nm"].to_numpy(float), c["exc_nm"].to_numpy(float)
    kf, gk = KFold(5, shuffle=True, random_state=0), GroupKFold(5)
    rnd = cross_val_predict(g, c[F], em - exc, cv=kf) + exc
    loso = cross_val_predict(g, c[F], em - exc, cv=gk, groups=c["doi"]) + exc
    rnd_d = cross_val_predict(g, c[F], em, cv=kf)
    loso_d = cross_val_predict(g, c[F], em, cv=gk, groups=c["doi"])
    rm = lambda p: float(np.sqrt(np.mean((em - p) ** 2)))                # noqa: E731
    r2 = lambda p: float(1 - np.sum((em - p) ** 2) / np.sum((em - em.mean()) ** 2))  # noqa: E731
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
                                    "r2_new_paper": r2(loso), "target": "deslocamento de Stokes",
                                    "direct": {"r2_random": r2(rnd_d), "r2_new_paper": r2(loso_d)},
                                    "boot_random": _r2_boot(em, {"stokes": rnd, "direta": rnd_d}, c["doi"].to_numpy()),
                                    "boot_new_paper": _r2_boot(em, {"stokes": loso, "direta": loso_d}, c["doi"].to_numpy()),
                                    "sd_em": float(c["em_nm"].std()), "obs": _r(c["em_nm"], 0),
                                    "pred_random": _r(rnd, 1), "pred_new_paper": _r(loso, 1),
                                    "n_papers": int(c["doi"].nunique())}}


# ---------------------------------------------------------------------------------------------- §4.9 causal

def _has(series: pd.Series, *keys: str) -> np.ndarray:
    return series.fillna("").str.split("|").apply(lambda xs: any(k in xs for k in keys)).to_numpy()


def _effect(d: pd.DataFrame, t: np.ndarray, y: np.ndarray, cov: pd.DataFrame, clus: np.ndarray, binary: bool,
            B: int = 200) -> dict:
    """ATE por IPW (Hájek) e AIPW (duplamente robusto); IC por bootstrap de ARTIGOS (registros do mesmo artigo não são
    independentes); balanço (SMD), sobreposição e sensibilidade ao aparo do escore."""
    from sklearn.linear_model import LinearRegression, LogisticRegression
    Xc = cov.to_numpy(float)
    mu_, sd_ = Xc.mean(0), Xc.std(0)
    Z = (Xc - mu_) / np.where(sd_ > 0, sd_, 1)

    def fit(ix, clip=0.02):
        tt, yy, ZZ = t[ix], y[ix], Z[ix]
        e = np.clip(LogisticRegression(max_iter=2000, C=10.0).fit(ZZ, tt).predict_proba(ZZ)[:, 1], clip, 1 - clip)
        w = np.where(tt == 1, 1 / e, 1 / (1 - e))
        m1h = np.sum(w * tt * yy) / np.sum(w * tt)
        m0h = np.sum(w * (1 - tt) * yy) / np.sum(w * (1 - tt))
        if binary:
            def om(g):
                mm = LogisticRegression(max_iter=2000, C=10.0).fit(ZZ[tt == g], yy[tt == g])
                return mm.predict_proba(ZZ)[:, 1]
        else:
            def om(g):
                return LinearRegression().fit(ZZ[tt == g], yy[tt == g]).predict(ZZ)
        o1, o0 = om(1), om(0)
        a1 = np.mean(o1 + tt * (yy - o1) / e)
        a0 = np.mean(o0 + (1 - tt) * (yy - o0) / (1 - e))
        return {"ipw": (m1h, m0h), "aipw": (a1, a0), "e": e, "w": w}
    full = fit(np.arange(len(t)))

    def ebal(ix):
        """Balanceamento por entropia (Hainmueller 2012) para o ATE: pesos de cada grupo que reproduzem EXATAMENTE as
        médias das covariáveis da amostra inteira; efeito = diferença das médias ponderadas do desfecho."""
        from scipy.optimize import minimize
        ZZ, tt, yy = Z[ix], t[ix], y[ix]
        tgt = ZZ.mean(0)
        out, wts = [], np.zeros(len(ix))
        for g in (1, 0):
            Xg = ZZ[tt == g] - tgt
            obj = lambda lam: np.log(np.mean(np.exp(np.clip(Xg @ lam, -50, 50))))  # noqa: E731
            lam = minimize(obj, np.zeros(Xg.shape[1]), method="BFGS").x
            wg = np.exp(np.clip(Xg @ lam, -50, 50))
            wg /= wg.sum()
            wts[tt == g] = wg
            out.append(float(np.sum(wg * yy[tt == g])))
        return out[0], out[1], wts
    eb1, eb0, ebw = ebal(np.arange(len(t)))
    uc = np.unique(clus)
    pos = {c: np.flatnonzero(clus == c) for c in uc}
    boots = []
    for _ in range(B):
        ix = np.concatenate([pos[c] for c in R.choice(uc, len(uc))])
        if len(np.unique(t[ix])) < 2:
            continue
        f = fit(ix)
        boots.append([f["aipw"][0], f["aipw"][1], f["ipw"][0], f["ipw"][1]])
    boots = np.array(boots)
    trim = fit(np.arange(len(t)), clip=0.05)

    def smd(wts):
        out = []
        for j in range(Xc.shape[1]):
            x = Xc[:, j]
            m1 = np.average(x[t == 1], weights=wts[t == 1])
            m0 = np.average(x[t == 0], weights=wts[t == 0])
            v = (x[t == 1].var() + x[t == 0].var()) / 2
            out.append(float((m1 - m0) / np.sqrt(v)) if v > 0 else 0.0)
        return out
    e = full["e"]
    res = {"n": int(len(t)), "n_treated": int(t.sum()), "n_articles": int(len(uc)), "covariates": list(cov.columns),
           "smd_before": smd(np.ones(len(t))), "smd_after": smd(full["w"]), "smd_ebal": smd(ebw),
           "propensity": {"treated": _r(np.sort(e[t == 1])[::max(1, int(t.sum()) // 600)], 3),
                          "control": _r(np.sort(e[t == 0])[::max(1, int((1 - t).sum()) // 600)], 3)}}
    if binary:                                   # diferença de risco e razão de riscos
        a1, a0 = full["aipw"]
        rd = boots[:, 0] - boots[:, 1]
        rr = boots[:, 0] / np.maximum(boots[:, 1], 1e-9)
        res.update({"scale": "risco", "p1": float(a1), "p0": float(a0), "rd": float(a1 - a0),
                    "rd_ci95": _r(np.quantile(rd, [0.025, 0.975]), 4), "rr": float(a1 / a0),
                    "rr_ci95": _r(np.quantile(rr, [0.025, 0.975]), 4),
                    "naive_rd": float(y[t == 1].mean() - y[t == 0].mean()),
                    "ipw_rd": float(full["ipw"][0] - full["ipw"][1]),
                    "trim_rd": float(trim["aipw"][0] - trim["aipw"][1]), "ebal_rd": float(eb1 - eb0), "ebal_rr": float(eb1 / eb0)})
        est, lo_, hi_ = res["rr"], res["rr_ci95"][0], res["rr_ci95"][1]
    else:                                        # razão de médias geométricas (desfecho em ln)
        ate = full["aipw"][0] - full["aipw"][1]
        bd = boots[:, 0] - boots[:, 1]
        lo_l, hi_l = np.quantile(bd, [0.025, 0.975])
        res.update({"scale": "ln", "ate": float(ate), "ci95": [float(lo_l), float(hi_l)], "ratio": float(np.exp(ate)),
                    "ratio_ci95": [float(np.exp(lo_l)), float(np.exp(hi_l))],
                    "naive_ratio": float(np.exp(y[t == 1].mean() - y[t == 0].mean())),
                    "ipw_ratio": float(np.exp(full["ipw"][0] - full["ipw"][1])),
                    "trim_ratio": float(np.exp(trim["aipw"][0] - trim["aipw"][1])), "ebal_ratio": float(np.exp(eb1 - eb0)),
                    "sd_y": float(y.std())})
        # E-value para desfecho contínuo (VanderWeele & Ding 2017): RR ≈ exp(0,91·d), d = efeito / dp do desfecho
        est, lo_, hi_ = (np.exp(0.91 * v / y.std()) for v in (ate, lo_l, hi_l))

    def ev(rr_):
        rr_ = rr_ if rr_ >= 1 else 1 / rr_
        return float(rr_ + np.sqrt(rr_ * (rr_ - 1)))
    near = lo_ if est >= 1 else hi_
    res["e_value"] = ev(est)
    res["e_value_ci"] = 1.0 if (lo_ <= 1 <= hi_) else ev(near)
    return res


def causal() -> dict:
    """§4.9 — estrutura causal das variáveis de síntese, com base nos mecanismos estabelecidos (LaMer: nucleação e
    crescimento; Turkevich/Frens; Brust; crescimento mediado por sementes), e quatro efeitos estimados nos registros da
    literatura, cada um conferido contra a direção que a literatura prevê."""
    # a base AuNC é selecionada pelo produto (só nanoaglomerados): incluí-la condicionaria no desfecho (viés de seleção)
    # e violaria a positividade (quase todo AuNC usa tiol) — fica fora das estimativas causais
    L = expdata.literature()
    L = L[L["source"] != "aunc2025"]
    L = L.assign(nabh4=_has(L["reductants_raw"], "NaBH4"), citr=_has(L["reductants_raw"], "trisodium_citrate"),
                 ascorb=_has(L["reductants_raw"], "ascorbic_acid"), ctab=_has(L["capping_raw"], "CTAB", "CTAC"),
                 thiol=_has(L["capping_raw"], "GSH", "dodecanethiol"), poly=_has(L["capping_raw"], "PVP", "PEG"),
                 clus=np.where(L["doi"] != "", L["doi"], L["title"]))
    spheroid = L["morph"].isin([expdata.MORPH.index(m) for m in ("sphere", "particle", "cluster")]) & L["size_nm"].between(1, 300)

    def base_cov(d, *extra):
        yr = d["year"].fillna(d["year"].median())
        cols = {"base NSP": (d["source"] == "nsp2026"),
                "ano de publicação": (yr - 2010) / 10, "ano não informado": d["year"].isna(),
                "aquecida (T > 40 °C)": d["T_C"] > 40, "T não informada": d["T_C"].isna(), "menciona GO": d["go"] == 1}
        lab = {"seed": "mediada por sementes", "nabh4": "NaBH₄", "citr": "citrato", "ascorb": "ácido ascórbico",
               "ctab": "CTAB/CTAC", "thiol": "tiol (GSH/dodecanotiol)", "poly": "polímero (PVP/PEG)"}
        for e_ in extra:
            cols[lab[e_]] = d[e_] == 1 if e_ == "seed" else d[e_]
        return pd.DataFrame({k: np.asarray(v, float) for k, v in cols.items()})

    specs = []
    # E1 redutor forte × citrato, só rota direta (na rota com sementes o NaBH4 forma as sementes e o tamanho é decidido
    #    no crescimento), só partículas esferoidais (o "tamanho" de um bastão não é diâmetro)
    d = L[spheroid & (L["seed"] == 0) & (L["nabh4"] ^ L["citr"])]
    specs.append(("redutor", "NaBH₄ (redutor forte) × citrato", "rota direta, partículas esferoidais", "tamanho",
                  d, d["nabh4"].to_numpy(int), np.log(d["size_nm"].to_numpy()), base_cov(d, "ascorb", "ctab", "thiol", "poly"), False,
                  {"dir": "<1", "txt": "NaBH₄ nucleia muito mais rápido: muitos núcleos e partículas de 1–8 nm (Brust et al. 1994); "
                   "o citrato reduz devagar e dá 10–20 nm (Turkevich et al. 1951; Frens 1973). Razão esperada ≈ 0,2–0,6.", "range": [0.2, 0.6], "ref": "Brust et al. 1994; Turkevich et al. 1951; Frens 1973"}))
    # E2 rota mediada por sementes × direta (efeito total do protocolo)
    d = L[spheroid]
    specs.append(("sementes", "Rota mediada por sementes × direta", "partículas esferoidais", "tamanho",
                  d, d["seed"].to_numpy(int), np.log(d["size_nm"].to_numpy()), base_cov(d), False,
                  {"dir": ">1", "txt": "Separar nucleação (sementes) de crescimento faz o ouro novo se depositar sobre as sementes, "
                   "aumentando o tamanho de forma controlada (Jana, Gearheart & Murphy 2001).", "range": [1.2, 3.0], "ref": "Jana, Gearheart & Murphy 2001"}))
    # E3 CTAB/CTAC → forma não esférica
    d = L[L["morph"] >= 0]
    nonsph = (~d["morph"].isin([expdata.MORPH.index(m) for m in ("sphere", "particle", "cluster")])).to_numpy(int)
    specs.append(("ctab", "CTAB/CTAC × sem CTAB", "registros com morfologia informada", "forma não esférica",
                  d, d["ctab"].to_numpy(int), nonsph.astype(float), base_cov(d, "seed", "nabh4", "citr", "ascorb"), True,
                  {"dir": ">1", "txt": "O surfactante catiônico adsorve preferencialmente em certas faces e direciona o crescimento "
                   "anisotrópico (bastões, cubos, estrelas): Jana et al. 2001; Nikoobakht & El-Sayed 2003.", "range": [1.5, 5.0], "ref": "Jana et al. 2001; Nikoobakht & El-Sayed 2003"}))
    # E4 tiol forte → tamanho menor
    d = L[spheroid]
    specs.append(("tiol", "Tiol (GSH/dodecanotiol) × sem tiol", "partículas esferoidais", "tamanho",
                  d, d["thiol"].to_numpy(int), np.log(d["size_nm"].to_numpy()), base_cov(d, "seed", "nabh4", "citr", "ctab", "poly"), False,
                  {"dir": "<1", "txt": "A ligação Au–S é forte e passiva a superfície durante o crescimento: partículas de 1–3 nm e "
                   "aglomerados (Brust et al. 1994).", "range": [0.1, 0.5], "ref": "Brust et al. 1994"}))
    effects = []
    for key, name, pop, outcome, d, t, y, cov, binary, exp_ in specs:
        r = _effect(d, t, y, cov, d["clus"].to_numpy(), binary)
        est, ci = (r["rr"], r["rr_ci95"]) if binary else (r["ratio"], r["ratio_ci95"])
        sig = ci[0] > 1 or ci[1] < 1
        agree = (est < 1) == (exp_["dir"] == "<1")
        # robustez: o balanceamento por entropia precisa equilibrar as médias (|SMD| < 0,1) e os estimadores
        # (AIPW, IPW/entropia, aparo 5–95 %) precisam concordar em ±25 %; senão a magnitude é frágil (pouca sobreposição)
        alts = [r["rr"], r["ebal_rr"]] if binary else [r["ratio"], r["ipw_ratio"], r["ebal_ratio"], r["trim_ratio"]]
        robust = bool(max(abs(v) for v in r["smd_ebal"]) < 0.1 and max(alts) / min(alts) < 1.25)
        r["estimators"] = ({"AIPW": r["rr"], "entropia": r["ebal_rr"]} if binary else
                           {"AIPW": r["ratio"], "IPW": r["ipw_ratio"], "entropia": r["ebal_ratio"], "aparo 5–95 %": r["trim_ratio"], "sem ajuste": r["naive_ratio"]})
        verdict = ("confirma" if robust else "confirma a direção; magnitude frágil") if (agree and sig) else \
            ("mesma direção, sem significância" if agree else "diverge")
        in_range = exp_["range"][0] <= est <= exp_["range"][1]
        effects.append(dict(r, key=key, name=name, population=pop, outcome=outcome, binary=binary, expected=exp_,
                            estimate=float(est), estimate_ci95=[float(ci[0]), float(ci[1])], verdict=verdict, in_range=bool(in_range),
                            robust=robust, replication=_replicate(d, t, y, cov, binary)))
    chain = _chain_lspr(L, spheroid, base_cov)
    prim = effects[0]
    dag = {"nodes": [["base", "base e época"], ["temperatura", "temperatura"], ["sementes", "rota com sementes"],
                     ["redutor", "força do redutor"], ["ligante", "ligante"], ["nucleacao", "nucleação (latente)"],
                     ["tamanho", "tamanho"], ["forma", "forma"], ["lspr", "LSPR (UV-Vis)"]],
           "edges": [["base", "redutor", ""], ["base", "ligante", ""], ["base", "sementes", ""], ["base", "temperatura", ""],
                     ["temperatura", "nucleacao", "cinética"], ["redutor", "nucleacao", "supersaturação"],
                     ["nucleacao", "tamanho", "nº de núcleos"], ["sementes", "tamanho", "crescimento"],
                     ["ligante", "tamanho", "passivação"], ["ligante", "forma", "faces"], ["sementes", "forma", ""],
                     ["tamanho", "lspr", "Mie"], ["forma", "lspr", "modos"]]}
    return dict({k: prim[k] for k in ("n", "n_treated", "ate", "ci95", "ratio", "ratio_ci95", "e_value", "covariates",
                                      "smd_before", "smd_after", "propensity")},
                treatment="NaBH4 (redutor forte)", control="citrato de sódio", outcome="ln(tamanho, nm)",
                naive=float(np.log(prim["naive_ratio"])), effects=effects, dag=dag, chain=chain)


def _replicate(d: pd.DataFrame, t: np.ndarray, y: np.ndarray, cov: pd.DataFrame, binary: bool) -> dict:
    """Replicação em bases INDEPENDENTES (Cruse 2022 × NSP 2026: extrações e corpora diferentes): o mesmo AIPW em cada
    base e a heterogeneidade entre elas (Q de Cochran e I² de Higgins & Thompson 2002, na escala log, com o erro-padrão
    tirado do IC por bootstrap de artigos). Efeito que só aparece numa base é suspeito de artefato de extração."""
    from scipy.stats import chi2
    out = {"bases": []}
    for src, lab in (("cruse2022", "Cruse 2022"), ("nsp2026", "NSP 2026")):
        m = (d["source"] == src).to_numpy()
        if m.sum() < 60 or t[m].sum() < 15 or (1 - t[m]).sum() < 15:
            continue
        c = cov[m].drop(columns=["base NSP"], errors="ignore")
        c = c.loc[:, c.std() > 0]
        try:
            r = _effect(d[m], t[m], y[m], c, d["clus"].to_numpy()[m], binary, B=150)
        except Exception:                                                  # sem sobreposição suficiente na base
            continue
        est, ci = (r["rr"], r["rr_ci95"]) if binary else (r["ratio"], r["ratio_ci95"])
        if not (np.all(np.isfinite(ci)) and min(ci) > 0):
            continue
        out["bases"].append({"base": lab, "n": r["n"], "n_treated": r["n_treated"], "n_articles": r["n_articles"],
                             "estimate": float(est), "ci95": [float(ci[0]), float(ci[1])],
                             "se_log": float((np.log(ci[1]) - np.log(ci[0])) / (2 * 1.96))})
    b = out["bases"]
    if len(b) == 2:
        lg, se = np.log([x["estimate"] for x in b]), np.array([x["se_log"] for x in b])
        wt = 1 / se ** 2
        fixed = float(np.sum(wt * lg) / wt.sum())
        Qc = float(np.sum(wt * (lg - fixed) ** 2))
        # efeitos aleatórios (DerSimonian & Laird 1986): τ² entre bases entra no peso, o IC alarga com a heterogeneidade
        tau2 = max(0.0, (Qc - 1) / (wt.sum() - np.sum(wt ** 2) / wt.sum()))
        wr = 1 / (se ** 2 + tau2)
        pooled, sp = float(np.sum(wr * lg) / wr.sum()), float(1 / np.sqrt(wr.sum()))
        out.update({"pooled": float(np.exp(pooled)), "pooled_ci95": [float(np.exp(pooled - 1.96 * sp)), float(np.exp(pooled + 1.96 * sp))],
                    "tau": float(np.sqrt(tau2)), "Q": Qc, "Q_p": float(chi2.sf(Qc, 1)), "I2": float(max(0.0, (Qc - 1) / Qc)) if Qc > 0 else 0.0,
                    "same_direction": bool(np.sign(lg[0]) == np.sign(lg[1])),
                    "both_significant": bool(all(x["ci95"][1] < 1 or x["ci95"][0] > 1 for x in b))})
    return out


def _chain_lspr(L: pd.DataFrame, spheroid: pd.Series, base_cov) -> dict:
    """Coerência da cadeia redutor → tamanho → LSPR: nos registros da rota direta com tamanho E pico relatados, o
    efeito do NaBH₄ no pico (nm) deve ser o que Mie prevê a partir do efeito no tamanho (mesmo ajuste, mesmos artigos)."""
    import mie
    d = L[spheroid & (L["seed"] == 0) & (L["nabh4"] ^ L["citr"]) & L["peak_nm"].between(490, 620)]
    cov = base_cov(d, "ascorb", "ctab", "thiol", "poly")
    cov = cov.loc[:, cov.std() > 0]
    t, cl = d["nabh4"].to_numpy(int), d["clus"].to_numpy()
    rs = _effect(d, t, np.log(d["size_nm"].to_numpy()), cov, cl, False)
    rp = _effect(d, t, d["peak_nm"].to_numpy(float), cov, cl, False)          # desfecho em nm: "ate" = diferença em nm
    # λ_LSPR de Mie (constantes medidas do Au, água, ensemble σ = 0,1) na grade de diâmetros
    wl, dg = np.arange(400.0, 901.0, 2.0), np.exp(np.linspace(np.log(1.5), np.log(320.0), 90))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        C = np.array([mie.extinction_cross_section(wl, x) for x in dg])
    s_ = np.sqrt(np.log(1.01))
    lam = np.array([_peak(wl, (lambda w: (w / w.sum()) @ C)(np.exp(-0.5 * ((np.log(dg) - np.log(x) + s_ * s_ / 2) / s_) ** 2)))
                    for x in dg])
    f = lambda x: np.interp(np.log(x), np.log(dg), lam)                           # noqa: E731
    d0 = d["size_nm"].to_numpy()[t == 0]                                          # tamanhos do grupo citrato
    shift = lambda r: float(np.mean(f(d0 * r) - f(d0)))                           # noqa: E731
    pred = shift(rs["ratio"])
    sh = [shift(r) for r in np.linspace(*rs["ratio_ci95"], 21)] + [pred]          # a curva não é monótona abaixo de 5 nm
    ci = [min(sh), max(sh)]
    return {"n": rs["n"], "n_treated": rs["n_treated"], "n_articles": rs["n_articles"],
            "size_ratio": rs["ratio"], "size_ratio_ci95": rs["ratio_ci95"],
            "peak_shift": rp["ate"], "peak_shift_ci95": rp["ci95"], "peak_shift_naive": float(np.log(rp["naive_ratio"])),
            "mie_shift": pred, "mie_shift_ci95": ci, "median_size_citrate": float(np.median(d0)),
            "mie_curve": {"d": _r(dg[(dg >= 2) & (dg <= 120)], 2), "lambda": _r(lam[(dg >= 2) & (dg <= 120)], 2)},
            "consistent": bool(rp["ci95"][0] <= pred <= rp["ci95"][1])}


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


# ---------------------------------------------------------------------------------- estruturas publicadas de GO (aba 3D)

GO_MACE = os.path.join(ROOT, "projects", "atomistic", "GO-MACE-23", "structures")
GO_TYPES = ["C sp²", "C sp³", "C de borda", "O epóxi", "O hidroxila", "O éter", "O carbonila", "O carboxila", "O lactona",
            "O outro", "H"]


def _read_xyz(path: str):
    with open(path, encoding="utf-8") as fh:
        n = int(fh.readline())
        hdr = fh.readline()
        lat = np.array([float(x) for x in hdr.split('Lattice="')[1].split('"')[0].split()]).reshape(3, 3)
        rows = [fh.readline().split() for _ in range(n)]
    return np.array([r[0] for r in rows]), np.array([[float(v) for v in r[1:4]] for r in rows]), lat


def _go_classify(el: np.ndarray, pos: np.ndarray, box: np.ndarray):
    """Ligações por distância (C–C < 1,85; C–O < 1,75; C–H < 1,25; O–H < 1,20 Å; periódico em x e z) e o tipo de cada
    átomo: C sp³ (4 vizinhos), C de borda (menos de 3 vizinhos C: bordas de buracos e da folha), O por grupo funcional
    (epóxi = ponte entre dois C ligados; éter = ponte entre C não ligados; hidroxila; carbonila C=O; carboxila COOH;
    lactona/anidrido = C=O cujo carbono também tem um O em ponte) e o lado da folha de cada O."""
    from scipy.spatial import cKDTree
    cut = {("C", "C"): 1.85, ("C", "O"): 1.75, ("C", "H"): 1.25, ("O", "H"): 1.20, ("O", "O"): 0.0, ("H", "H"): 0.0}
    p = pos.copy()
    p[:, 0] %= box[0]
    p[:, 2] %= box[2]
    tree = cKDTree(np.c_[p[:, 0], p[:, 1] - p[:, 1].min(), p[:, 2]], boxsize=[box[0], 1e6, box[2]])
    pr = tree.query_pairs(1.9, output_type="ndarray")
    dv = p[pr[:, 0]] - p[pr[:, 1]]
    dv[:, 0] -= box[0] * np.round(dv[:, 0] / box[0])
    dv[:, 2] -= box[2] * np.round(dv[:, 2] / box[2])
    d = np.linalg.norm(dv, axis=1)
    ok = np.array([d[k] < cut.get((el[a], el[b]), cut.get((el[b], el[a]), 0)) for k, (a, b) in enumerate(pr)])
    nb = [[] for _ in el]
    for a, b in pr[ok]:
        nb[a].append(b)
        nb[b].append(a)
    t = np.full(len(el), 9)
    side = np.zeros(len(el), int)
    for i, e in enumerate(el):
        if e == "H":
            t[i] = 10
        elif e == "C":
            ncc = sum(el[j] == "C" for j in nb[i])
            t[i] = 1 if len(nb[i]) >= 4 else 2 if ncc < 3 else 0
    hasH = lambda j: any(el[q] == "H" for q in nb[j])                                     # noqa: E731
    for i in np.where(el == "O")[0]:
        nc = [j for j in nb[i] if el[j] == "C"]
        nh = [j for j in nb[i] if el[j] == "H"]
        if nc:
            side[i] = 1 if p[i, 1] >= np.mean(p[nc, 1]) else -1
        if len(nc) == 2 and not nh:
            if nc[1] in nb[nc[0]]:
                t[i] = 3
            else:
                carb = any(len([q for q in nb[c] if el[q] == "O" and q != i and len(nb[q]) == 1]) for c in nc)
                t[i] = 8 if carb else 5
        elif len(nc) == 1 and len(nh) == 1:
            others = [q for q in nb[nc[0]] if el[q] == "O" and q != i]
            t[i] = 7 if others else 4
        elif len(nc) == 1 and not nh:
            others = [q for q in nb[nc[0]] if el[q] == "O" and q != i]
            t[i] = 7 if any(hasH(q) for q in others) else 8 if others else 6
    return t, side, p


def go_structures(crop: float = 96.0) -> dict:
    """Modelos estruturais PUBLICADOS de óxido de grafeno (não são medidas): El-Machachi et al., Angew. Chem. Int. Ed.
    2024, e202410088 (dados: Zenodo 10.5281/zenodo.14066557) — GO recozido por 2 ns a 900, 1 200 e 1 500 K com o
    potencial GO-MACE-23 (treinado em DFT) e otimizado. Para cada um: a composição química da folha inteira (grupos
    funcionais, O/C, carbonos sp³ e de borda, ondulação) e um recorte de ~10 nm × 10 nm, o mais plano, para a cena 3D."""
    out = {"types": GO_TYPES, "source": "El-Machachi et al., Angew. Chem. Int. Ed. 2024, e202410088",
           "doi_data": "10.5281/zenodo.14066557", "structures": []}
    for T in ("900K", "1200K", "1500K"):
        el, pos, lat = _read_xyz(os.path.join(GO_MACE, T, "optimized.xyz"))
        box = np.array([lat[0, 0], 0.0, lat[2, 2]])
        t, side, p = _go_classify(el, pos, box)
        nC, nO = int((el == "C").sum()), int((el == "O").sum())
        cnt = {GO_TYPES[k]: int((t == k).sum()) for k in range(len(GO_TYPES))}
        isC = el == "C"
        # recorte mais plano (menor desvio da altura dos C) numa grade de centros, com periodicidade em x e z
        best = None
        for cx in np.arange(0, box[0], 8.0):
            for cz in np.arange(0, box[2], 8.0):
                dx = (p[:, 0] - cx + box[0] / 2) % box[0] - box[0] / 2
                dz = (p[:, 2] - cz + box[2] / 2) % box[2] - box[2] / 2
                m = (np.abs(dx) <= crop / 2) & (np.abs(dz) <= crop / 2)
                sd = float(p[m & isC, 1].std())
                if best is None or sd < best[0]:
                    best = (sd, dx, dz, m)
        sd, dx, dz, m = best
        y0 = float(np.median(p[m & isC, 1]))
        out["structures"].append({
            "T": T.replace("K", " K"), "n_atoms": int(len(el)), "n_C": nC, "n_O": nO, "n_H": int((el == "H").sum()),
            "OC": nO / nC, "sp3_frac": cnt["C sp³"] / nC, "edge_frac": cnt["C de borda"] / nC,
            "corrugation_A": float(p[isC, 1].std()), "cell_nm": [round(box[0] / 10, 2), round(box[2] / 10, 2)],
            "counts": cnt, "per100C": {k: 100 * v / nC for k, v in cnt.items() if k.startswith("O ")},
            "crop": {"L": crop, "corrugation_A": sd, "n": int(m.sum()),
                     "x": np.round(dx[m] * 100).astype(int).tolist(), "y": np.round((p[m, 1] - y0) * 100).astype(int).tolist(),
                     "z": np.round(dz[m] * 100).astype(int).tolist(), "t": t[m].astype(int).tolist(), "s": side[m].astype(int).tolist()}})
    return out
