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
    rows = np.array([[float(x) for x in l.split()] for l in d["DATA"][0]["data"].strip().splitlines()])
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
