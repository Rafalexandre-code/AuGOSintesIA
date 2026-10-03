#!/usr/bin/env python3
"""Espectros de extinção de nanopartículas esféricas de Au (ou Ag) por teoria de Mie.

Constantes ópticas tabeladas (datasets/optical-constants/, refractiveindex.info, CC0) — padrão: Johnson & Christy
(1972) — com correção opcional de amortecimento por tamanho (espalhamento de elétrons na superfície, modelo de
Kreibig): ε(ω, d) = ε_bulk(ω) + ωp²/(ω² + iγ∞ω) − ωp²/(ω² + iγ(d)ω), γ(d) = γ∞ + A·vF/(d/2).
Distribuição de tamanhos log-normal opcional. Mie: miepython (external/aunp-spectral/miepython).

Uso:
    python code/spectral/mie.py 20 40 60                 # λ_LSPR de AuNP de 20, 40 e 60 nm em água
    python code/spectral/mie.py 30 --sigma 0.1 --csv s.csv   # espectro de ensemble polidisperso
"""
from __future__ import annotations

import argparse
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPTICAL = os.path.join(ROOT, "datasets", "optical-constants")
DATASETS = {"Au": "Au_Johnson-Christy_1972.yml", "Au-McPeak": "Au_McPeak_2015.yml", "Ag": "Ag_Johnson-Christy_1972.yml"}

# parâmetros de Drude para a correção de tamanho (valores usuais na literatura de plasmônica)
HBAR_EV_S = 6.582119569e-16
DRUDE = {"Au": {"wp_eV": 9.03, "gamma_eV": 0.053, "vF_m_s": 1.40e6},
         "Ag": {"wp_eV": 9.01, "gamma_eV": 0.018, "vF_m_s": 1.39e6}}


def load_nk(material: str = "Au") -> tuple[np.ndarray, np.ndarray]:
    """-> (λ em nm, n − ik complexo) do arquivo YAML do refractiveindex.info."""
    import yaml
    path = os.path.join(OPTICAL, DATASETS[material])
    d = yaml.safe_load(open(path, encoding="utf-8"))
    rows = np.array([[float(x) for x in line.split()] for line in d["DATA"][0]["data"].strip().splitlines()])
    return rows[:, 0] * 1000.0, rows[:, 1] - 1j * rows[:, 2]


def permittivity(wl_nm: np.ndarray, material: str = "Au", d_nm: float | None = None, A: float = 1.0) -> np.ndarray:
    """ε complexo (convenção ε = ε' − iε'') interpolado em wl_nm, com correção de tamanho se d_nm for dado."""
    w0, m0 = load_nk(material)
    n = np.interp(wl_nm, w0, m0.real)
    k = np.interp(wl_nm, w0, -m0.imag)
    eps = (n - 1j * k) ** 2
    if d_nm is not None and A > 0:
        p = DRUDE[material.split("-")[0]]
        E = 1239.84193 / np.asarray(wl_nm)                         # energia do fóton (eV)
        g_extra = HBAR_EV_S * A * p["vF_m_s"] / (d_nm * 1e-9 / 2)  # ħ·A·vF/R (eV)
        g0, wp = p["gamma_eV"], p["wp_eV"]
        # Drude na convenção e^{+iωt} (ε'' ≥ 0 com sinal "−i"): ε_D = 1 − ωp²/(ω² − iγω)
        drude = lambda g: -wp ** 2 / (E ** 2 - 1j * g * E)          # noqa: E731
        eps = eps - drude(g0) + drude(g0 + g_extra)
    return eps


def extinction_cross_section(wl_nm: np.ndarray, d_nm: float, material: str = "Au", n_medium: float = 1.333,
                             size_correction: bool = True) -> np.ndarray:
    """Seção de choque de extinção (nm²) de uma esfera de diâmetro d_nm em meio de índice n_medium."""
    import miepython
    wl_nm = np.asarray(wl_nm, dtype=float)
    eps = permittivity(wl_nm, material, d_nm if size_correction else None)
    m = np.sqrt(eps)
    m = m.real - 1j * np.abs(m.imag)
    qext = np.array([miepython.efficiencies(mi, d_nm, wl, n_env=n_medium)[0] for mi, wl in zip(m, wl_nm)])
    return qext * np.pi * (d_nm / 2) ** 2


def ensemble_extinction(wl_nm: np.ndarray, d_mean_nm: float, sigma_rel: float = 0.0, material: str = "Au",
                        n_medium: float = 1.333, n_sizes: int = 15) -> np.ndarray:
    """Extinção média (nm²/partícula) de uma população log-normal com média d_mean_nm e desvio relativo sigma_rel."""
    if sigma_rel <= 0:
        return extinction_cross_section(wl_nm, d_mean_nm, material, n_medium)
    s = np.sqrt(np.log(1 + sigma_rel ** 2))
    mu = np.log(d_mean_nm) - s ** 2 / 2
    z = np.linspace(-2.5, 2.5, n_sizes)
    ds = np.exp(mu + s * z)
    w = np.exp(-z ** 2 / 2)
    w /= w.sum()
    return sum(wi * extinction_cross_section(wl_nm, di, material, n_medium) for wi, di in zip(w, ds))


FIT_GRID_NM = np.arange(400.0, 801.0, 4.0)
FIT_D_NM = np.exp(np.linspace(np.log(3.0), np.log(160.0), 90))
FIT_SIGMA = (0.03, 0.06, 0.10, 0.15, 0.22, 0.30, 0.40)


def _cross_table(material: str = "Au", n_medium: float = 1.333) -> np.ndarray:
    """C_ext(d, λ) na grade de ajuste, guardada em <repo>/.cache (ignorado) para não refazer o Mie a cada chamada."""
    cache = os.path.join(ROOT, ".cache", f"mie_fit_{material}_{n_medium:.3f}.npy")
    if os.path.exists(cache):
        t = np.load(cache)
        if t.shape == (len(FIT_D_NM), len(FIT_GRID_NM)):
            return t
    t = np.array([extinction_cross_section(FIT_GRID_NM, d, material, n_medium) for d in FIT_D_NM])
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.save(cache, t)
    except OSError:
        pass
    return t


def _ensemble_from_table(table: np.ndarray, d_mean: float, sigma_rel: float) -> np.ndarray:
    s = np.sqrt(np.log(1 + sigma_rel ** 2))
    mu = np.log(d_mean) - s ** 2 / 2
    lnd = np.log(FIT_D_NM)
    w = np.exp(-0.5 * ((lnd - mu) / s) ** 2)
    w /= w.sum()
    return w @ table


def fit_size_distribution(wl_nm: np.ndarray, absorbance_: np.ndarray, material: str = "Au", n_medium: float = 1.333,
                          background: bool = True) -> dict:
    """Ajuste do espectro inteiro por Mie: A(λ) ≈ a·C_ext,ensemble(λ; d, σ) + b·(450/λ)³ + c, com a, b, c ≥ 0
    (NNLS) e busca em grade de (d, σ) log-normal. O fundo em potência cobre GO e espalhamento; c, a linha de base.
    Devolve d e σ do melhor ajuste e, em `d_post_mean_nm`/`d_post_sd_log`, a média e o dp de ln d pesados por
    exp(−Δχ²/2): perto do mínimo do LSPR (~15 nm) o tamanho é pouco identificável e o dp diz isso."""
    from scipy.optimize import nnls
    w = np.asarray(wl_nm, float)
    o = np.argsort(w)
    A = np.interp(FIT_GRID_NM, w[o], np.asarray(absorbance_, float)[o])
    table = _cross_table(material, n_medium)
    bg = [(450.0 / FIT_GRID_NM) ** 3, np.ones_like(FIT_GRID_NM)] if background else []
    res = []
    for sg in FIT_SIGMA:
        for d in FIT_D_NM[2:-2]:
            e = _ensemble_from_table(table, d, sg)
            M = np.column_stack([e / e.max(), *bg])
            coef, rn = nnls(M, A)
            res.append((rn ** 2, d, sg, coef))
    rss = np.array([r[0] for r in res])
    n, k = len(A), 3 + len(bg)
    s2 = max(rss.min() / max(n - k, 1), 1e-12)
    wt = np.exp(-(rss - rss.min()) / (2 * s2))
    wt /= wt.sum()
    lnd = np.log([r[1] for r in res])
    sig = np.array([r[2] for r in res])
    best = res[int(np.argmin(rss))]
    m = float(wt @ lnd)
    return {"d_fit_nm": float(best[1]), "sigma_fit": float(best[2]), "amplitude": float(best[3][0]),
            "background": float(best[3][1]) if background else 0.0, "rmse": float(np.sqrt(best[0] / n)),
            "d_post_mean_nm": float(np.exp(m)), "d_post_sd_log": float(np.sqrt(max(wt @ (lnd - m) ** 2, 0.0))),
            "sigma_post_mean": float(wt @ sig)}


def absorbance(wl_nm: np.ndarray, d_mean_nm: float, n_particles_per_mL: float, path_cm: float = 1.0,
               sigma_rel: float = 0.0, **kw) -> np.ndarray:
    """Absorbância (extinção) de uma suspensão: A = N·C_ext·L / ln(10)."""
    c_ext_cm2 = ensemble_extinction(wl_nm, d_mean_nm, sigma_rel, **kw) * 1e-14
    return n_particles_per_mL * c_ext_cm2 * path_cm / np.log(10)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("diameters", nargs="+", type=float)
    ap.add_argument("--material", default="Au", choices=list(DATASETS))
    ap.add_argument("--sigma", type=float, default=0.0, help="desvio relativo de tamanho (log-normal)")
    ap.add_argument("--medium", type=float, default=1.333)
    ap.add_argument("--csv", help="grava o espectro (último diâmetro) em CSV")
    a = ap.parse_args()
    wl = np.arange(400, 801, 1.0)
    for d in a.diameters:
        ext = ensemble_extinction(wl, d, a.sigma, a.material, a.medium)
        i = int(np.argmax(ext))
        print(f"d = {d:6.1f} nm: λ_LSPR = {wl[i]:.0f} nm, C_ext(máx) = {ext[i]:.3g} nm², A_LSPR/A450 = {ext[i] / ext[50]:.2f}")
    if a.csv:
        np.savetxt(a.csv, np.c_[wl, ext / ext.max()], delimiter=",", header="wavelength_nm,extinction_norm", comments="")


if __name__ == "__main__":
    main()
