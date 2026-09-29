#!/usr/bin/env python3
"""Processamento de espectros UV-Vis de AuNP e perda espectral J (Eq. 1 da proposta).

    J = (1/M) Σₘ [ (E(λₘ) − E*(λₘ)) / sₘ ]²        (sₘ = desvio experimental em λₘ)
    modelagem: log(J + ε)                           (ε fixado no piloto)

Correções padronizadas (§4.4/§4.17): subtração do branco, fator de diluição e caminho óptico (→ absorbância por
cm). Descritores: λ_LSPR (ajuste quadrático local), A_LSPR, FWHM (meia altura com interpolação; se o lado azul
não cai à metade por causa da absorção interbanda, usa 2×HWHM do lado vermelho e marca `fwhm_method`),
A_LSPR/A450 e diâmetro estimado pelas relações empíricas de Haiss et al. (Anal. Chem. 2007, 79, 4215):
    d = exp(3,00·A_LSPR/A450 − 2,20)              (≈ 5–80 nm)
    d = ln((λ_LSPR − 512)/6,53) / 0,0216          (d > 25 nm)

Uso:
    python code/spectral/uvvis.py amostra.csv [--blank branco.csv --dilution 2 --path-mm 10]
    python code/spectral/uvvis.py amostra.csv --target alvo.csv [--sd desvios.csv | --sd-const 0.01] [--normalize max]
Arquivos: CSV/TXT com duas colunas (λ em nm, absorbância), cabeçalho opcional.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

HAISS_B1, HAISS_B0 = 3.00, 2.20
HAISS_L0, HAISS_L1, HAISS_L2 = 512.0, 6.53, 0.0216


def read_spectrum(path: str) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.replace(";", ",").replace("\t", ",").split(",") if ("," in line or ";" in line or "\t" in line) \
            else line.split()
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except (ValueError, IndexError):
            continue  # cabeçalho/comentário
    a = np.array(sorted(rows))
    return a[:, 0], a[:, 1]


def correct(w: np.ndarray, a: np.ndarray, blank: tuple[np.ndarray, np.ndarray] | None = None,
            dilution: float = 1.0, path_mm: float = 10.0) -> np.ndarray:
    """Absorbância corrigida: (A − A_branco) × diluição × (10 mm / caminho)."""
    a = np.asarray(a, float).copy()
    if blank is not None:
        a = a - np.interp(w, blank[0], blank[1])
    return a * dilution * (10.0 / path_mm)


def resample(w: np.ndarray, a: np.ndarray, grid: np.ndarray) -> np.ndarray:
    return np.interp(grid, w, a, left=np.nan, right=np.nan)


def lspr(w: np.ndarray, a: np.ndarray, window: tuple[float, float] = (480.0, 800.0)) -> dict:
    """Descritores da banda plasmônica."""
    w, a = np.asarray(w, float), np.asarray(a, float)
    sel = (w >= window[0]) & (w <= window[1])
    ws, as_ = w[sel], a[sel]
    i = int(np.argmax(as_))
    lo, hi = max(i - 5, 0), min(i + 6, len(ws))
    if hi - lo >= 3:
        c = np.polyfit(ws[lo:hi], as_[lo:hi], 2)
        lam = -c[1] / (2 * c[0]) if c[0] < 0 else ws[i]
        lam = float(np.clip(lam, ws[lo], ws[hi - 1]))
        amax = float(np.polyval(c, lam)) if c[0] < 0 else float(as_[i])
    else:
        lam, amax = float(ws[i]), float(as_[i])
    half = amax / 2
    j = int(np.searchsorted(w, lam))

    def cross(idx_range):
        prev = None
        for k in idx_range:
            if prev is not None and (a[prev] - half) * (a[k] - half) <= 0 and a[prev] != a[k]:
                return w[prev] + (half - a[prev]) * (w[k] - w[prev]) / (a[k] - a[prev])
            prev = k
        return None

    right = cross(range(j, len(w)))
    left = cross(range(j - 1, -1, -1))
    if left is not None and right is not None:
        fwhm, method = right - left, "full"
    elif right is not None:
        fwhm, method = 2 * (right - lam), "2xHWHM_red"
    else:
        fwhm, method = float("nan"), "undefined"
    a450 = float(np.interp(450.0, w, a)) if w.min() <= 450 <= w.max() else float("nan")
    ratio = amax / a450 if a450 and a450 > 0 else float("nan")
    d_ratio = float(np.exp(HAISS_B1 * ratio - HAISS_B0)) if np.isfinite(ratio) else float("nan")
    d_lambda = float(np.log((lam - HAISS_L0) / HAISS_L1) / HAISS_L2) if lam > HAISS_L0 + HAISS_L1 else float("nan")
    return {"LSPR_nm": lam, "A_LSPR": amax, "LSPR_FWHM_nm": float(fwhm), "fwhm_method": method, "A450": a450,
            "A_LSPR_over_A450": ratio, "d_Haiss_ratio_nm": d_ratio,
            "d_Haiss_lambda_nm": d_lambda if d_lambda > 25 else float("nan")}


def normalize(a: np.ndarray, how: str | None, w: np.ndarray | None = None) -> np.ndarray:
    if how in (None, "none"):
        return a
    if how == "max":
        return a / np.nanmax(a)
    if how == "area":
        return a / np.trapezoid(np.nan_to_num(a), w)
    raise ValueError(how)


def spectral_loss_J(w: np.ndarray, E: np.ndarray, w_target: np.ndarray, E_target: np.ndarray,
                    s: np.ndarray | float | None = None, grid: np.ndarray | None = None,
                    norm: str | None = None) -> float:
    """J = média de ((E − E*)/s)² na grade comum (padrão: 400–800 nm a cada 2 nm)."""
    grid = np.arange(400.0, 801.0, 2.0) if grid is None else np.asarray(grid, float)
    e = normalize(resample(w, E, grid), norm, grid)
    t = normalize(resample(w_target, E_target, grid), norm, grid)
    if s is None:
        s = 1.0
    s = np.broadcast_to(np.asarray(s, float), grid.shape) if np.ndim(s) == 0 else np.asarray(s, float)
    ok = np.isfinite(e) & np.isfinite(t) & (s > 0)
    return float(np.mean(((e[ok] - t[ok]) / s[ok]) ** 2))


def log_loss(J: float, eps: float = 1e-3) -> float:
    return float(np.log(J + eps))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spectrum")
    ap.add_argument("--blank")
    ap.add_argument("--dilution", type=float, default=1.0)
    ap.add_argument("--path-mm", type=float, default=10.0)
    ap.add_argument("--target", help="espectro-alvo E*(λ)")
    ap.add_argument("--sd", help="CSV λ, s(λ) com o desvio experimental")
    ap.add_argument("--sd-const", type=float, default=None)
    ap.add_argument("--normalize", choices=["none", "max", "area"], default="none")
    ap.add_argument("--eps", type=float, default=1e-3)
    a = ap.parse_args()
    w, A = read_spectrum(a.spectrum)
    A = correct(w, A, read_spectrum(a.blank) if a.blank else None, a.dilution, a.path_mm)
    out = lspr(w, A)
    if a.target:
        wt, At = read_spectrum(a.target)
        grid = np.arange(400.0, 801.0, 2.0)
        s = np.interp(grid, *read_spectrum(a.sd)) if a.sd else a.sd_const
        J = spectral_loss_J(w, A, wt, At, s=s, grid=grid, norm=a.normalize)
        out.update({"spectral_loss_J": J, "log_J_eps": log_loss(J, a.eps)})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
