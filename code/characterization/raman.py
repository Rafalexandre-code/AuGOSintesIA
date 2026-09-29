#!/usr/bin/env python3
"""Raman de óxido de grafeno: linha de base + ajuste das bandas D/G (e D*, D'', D') com incerteza.

A proposta (§4.2) prioriza **larguras de banda** e a distribuição espacial de medidas; ID/IG é reportado, mas não
deve ser usado sozinho como medida de oxidação do GO (ver Dimiev, Halbig & Talyzin 2026 em literature/;
`python tools/search_literature.py "Raman graphene oxide D band G band width"`).

Modelos:
  2band  D e G lorentzianas (rápido, comparável à maior parte da literatura)
  5band  D* (~1200, gaussiana), D (~1350, lorentziana), D'' (~1510, gaussiana, carbono amorfo),
         G (~1585, lorentziana), D' (~1615, lorentziana) — decomposição usual para GO/rGO

Uso:
    python code/characterization/raman.py espectro.csv [--model 5band] [--sample GO-B01-S01 --out medidas.csv]
Vários espectros (mapa) do mesmo ponto/amostra: passe todos; a saída traz média ± sd entre espectros.
Saída --out: linhas no formato de datasets/data-model/templates/go_characterization.csv.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))

BANDS = {
    "2band": [("D", 1350, "lorentz"), ("G", 1590, "lorentz")],
    "5band": [("Dstar", 1200, "gauss"), ("D", 1350, "lorentz"), ("D2", 1510, "gauss"), ("G", 1585, "lorentz"),
              ("Dprime", 1615, "lorentz")],
}


def read_xy(path: str) -> tuple[np.ndarray, np.ndarray]:
    from uvvis import read_spectrum
    return read_spectrum(path)


def baseline_correct(x: np.ndarray, y: np.ndarray, method: str = "arpls", lam: float = 1e8) -> np.ndarray:
    """Remove fundo de fluorescência forte com pybaselines antes do ajuste (use só se o fundo não for ~linear;
    lam alto preserva as bandas largas do GO)."""
    from pybaselines import Baseline
    b = Baseline(x_data=x)
    base = b.arpls(y, lam=lam)[0] if method == "arpls" else b.modpoly(y, poly_order=3)[0]
    return y - base


def fit(x: np.ndarray, y: np.ndarray, model: str = "2band", xrange: tuple[float, float] = (1000, 1800),
        joint_linear: bool = True) -> dict:
    """Ajuste das bandas. joint_linear: fundo linear ajustado junto com as bandas (padrão) — linhas de base
    flexíveis (arPLS, polinômios) "comem" as caudas lorentzianas largas do GO e subestimam as larguras."""
    from lmfit.models import GaussianModel, LinearModel, LorentzianModel
    sel = (x >= xrange[0]) & (x <= xrange[1])
    x, y = x[sel], y[sel]
    comp = LinearModel(prefix="bg_") if joint_linear else None
    for name, center, shape in BANDS[model]:
        m = (LorentzianModel if shape == "lorentz" else GaussianModel)(prefix=f"{name}_")
        comp = m if comp is None else comp + m
    pars = comp.make_params()
    if joint_linear:
        slope = (y[-1] - y[0]) / (x[-1] - x[0])
        pars["bg_slope"].set(value=slope)
        pars["bg_intercept"].set(value=float(min(y[0], y[-1])) - slope * x[0])
    ymax = float(np.max(y))
    for name, center, shape in BANDS[model]:
        pars[f"{name}_center"].set(value=center, min=center - 40, max=center + 40)
        pars[f"{name}_sigma"].set(value=30 if name in ("D", "G") else 40, min=3, max=150)
        pars[f"{name}_amplitude"].set(value=ymax * 60, min=0)
    res = comp.fit(y, pars, x=x)
    out = {"model": model, "r2": float(1 - np.sum(res.residual ** 2) / np.sum((y - y.mean()) ** 2))}
    for name, _c, _s in BANDS[model]:
        p = res.params
        out[f"{name}_pos_cm-1"] = (p[f"{name}_center"].value, p[f"{name}_center"].stderr)
        out[f"{name}_FWHM_cm-1"] = (p[f"{name}_fwhm"].value, p[f"{name}_fwhm"].stderr)
        out[f"{name}_height"] = (p[f"{name}_height"].value, p[f"{name}_height"].stderr)
        out[f"{name}_area"] = (p[f"{name}_amplitude"].value, p[f"{name}_amplitude"].stderr)

    def ratio(a, b):
        va, sa = out[a]
        vb, sb = out[b]
        r = va / vb
        s = r * np.sqrt(((sa or 0) / va) ** 2 + ((sb or 0) / vb) ** 2) if va and vb else None
        return (r, s)
    out["ID_IG"] = ratio("D_height", "G_height")
    out["AD_AG"] = ratio("D_area", "G_area")
    return out


KEEP = ["D_FWHM_cm-1", "G_FWHM_cm-1", "D_pos_cm-1", "G_pos_cm-1", "ID_IG", "AD_AG", "D2_FWHM_cm-1", "D2_area"]


def summarize(fits: list[dict]) -> dict:
    """Média ± sd entre espectros (réplicas/pontos do mapa); com 1 espectro, usa o erro do ajuste."""
    out = {}
    for k in KEEP:
        vals = [f[k][0] for f in fits if k in f and f[k][0] is not None]
        if not vals:
            continue
        if len(vals) > 1:
            out[k] = (float(np.mean(vals)), float(np.std(vals, ddof=1)), len(vals), "sd")
        else:
            out[k] = (vals[0], fits[0][k][1], 1, "instrument")
    return out


def to_rows(summary: dict, sample_id: str, start: int = 1, instrument: str = "", files: str = "") -> list[dict]:
    rows = []
    for i, (q, (v, s, n, t)) in enumerate(summary.items()):
        unit = "cm-1" if "cm-1" in q else "a.u."
        rows.append({"measurement_id": f"M-RAMAN-{sample_id}-{start + i:03d}", "go_sample_id": sample_id,
                     "technique": "Raman", "quantity": q.replace("_cm-1", ""), "value": round(v, 4),
                     "uncertainty": round(s, 4) if s is not None else "", "uncertainty_type": t if s is not None else "",
                     "n_replicates": n, "unit": unit, "instrument": instrument,
                     "method_details": "fundo linear conjunto; bandas lorentzianas/gaussianas (lmfit)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spectra", nargs="+")
    ap.add_argument("--model", choices=list(BANDS), default="2band")
    ap.add_argument("--baseline", choices=["joint-linear", "arpls", "modpoly"], default="joint-linear",
                    help="joint-linear: fundo linear ajustado com as bandas (padrão); arpls/modpoly: pré-correção")
    ap.add_argument("--sample", default="SAMPLE")
    ap.add_argument("--out", help="CSV no formato go_characterization")
    a = ap.parse_args()
    fits = []
    for f in a.spectra:
        x, y = read_xy(f)
        if a.baseline != "joint-linear":
            y = baseline_correct(x, y, a.baseline)
        fits.append(fit(x, y, a.model, joint_linear=a.baseline == "joint-linear"))
    summ = summarize(fits)
    for k, (v, s, n, t) in summ.items():
        print(f"{k:14} {v:10.3f} ± {s if s is not None else float('nan'):.3f} ({t}, n={n})")
    if a.out:
        rows = to_rows(summ, a.sample, files="|".join(a.spectra))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
