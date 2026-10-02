#!/usr/bin/env python3
"""FTIR (ATR) de óxido de grafeno: linha de base, deconvolução e razões de grupos oxigenados com incerteza (§4.2).

Cautelas da literatura que a proposta adota (Dimiev, Halbig & Talyzin 2026; Brusko et al., Carbon 2024):
  * a banda de ~1620 cm⁻¹ NÃO é só C=C aromático: a deformação H–O–H da água adsorvida cai no mesmo lugar e muda
    com a umidade. Por isso a região 1480–1800 cm⁻¹ é DECONVOLUÍDA em C=O (~1725), H₂O (~1625) e C=C (~1580), e a
    fração de água é reportada; acima de `--max-water-fraction` o espectro é marcado como sensível à umidade
    (SOP-GO-CHAR-01 pede medir também após 24 h em dessecador);
  * o estiramento O–H (3000–3700 cm⁻¹) mistura hidroxilas, carboxilas e água: entra como descritor, com essa ressalva.
Descritores (razões de área relativas à C=C, comparáveis entre lotes medidos no mesmo instrumento):
  FTIR_CO_CC (C=O), FTIR_COC_CC (C–O–C, epóxido ~1230), FTIR_CO_alkoxy_CC (C–O, ~1050), FTIR_OH_CC, FTIR_water_frac.

Uso:
    python code/characterization/ftir.py esp1.csv esp2.csv … [--transmittance] --sample GO-B01-S01 --out m.csv
Várias réplicas: média ± sd entre espectros. Entrada: duas colunas (cm⁻¹, absorbância ou %T).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))

CARBONYL_REGION = (1480.0, 1800.0)
COMPONENTS = (("CO", 1725.0), ("H2O", 1625.0), ("CC", 1580.0))   # centros iniciais (cm⁻¹)
INTEGRALS = {"COC": (1180.0, 1280.0), "CO_alkoxy": (1000.0, 1120.0), "OH": (3000.0, 3700.0)}


def read_xy(path: str, transmittance: bool = False) -> tuple[np.ndarray, np.ndarray]:
    from uvvis import read_spectrum
    x, y = read_spectrum(path)
    if transmittance:
        y = -np.log10(np.clip(y / (100.0 if y.max() > 1.5 else 1.0), 1e-6, None))
    return x, y


def rubberband(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Linha de base 'rubberband': casca convexa inferior do espectro (padrão em FTIR de sólidos)."""
    from scipy.spatial import ConvexHull
    v = ConvexHull(np.c_[x, y]).vertices          # 2D: vértices em sentido anti-horário
    v = np.roll(v, -int(v.argmin()))               # começa no menor x (x já ordenado)
    lower = np.sort(v[: int(v.argmax()) + 1])      # do menor ao maior x pela parte de baixo da casca
    return np.interp(x, x[lower], y[lower])


def _gauss(x, a, c, w):
    return a * np.exp(-0.5 * ((x - c) / w) ** 2)


def deconvolve(x: np.ndarray, y: np.ndarray) -> dict:
    """3 gaussianas (C=O, H₂O, C=C) + fundo linear na região 1480–1800 cm⁻¹; áreas com erro do ajuste."""
    from scipy.optimize import curve_fit
    sel = (x >= CARBONYL_REGION[0]) & (x <= CARBONYL_REGION[1])
    xs, ys = x[sel], y[sel]

    def model(xx, *p):
        out = p[-2] + p[-1] * (xx - xs.mean())
        for k in range(3):
            out = out + _gauss(xx, *p[3 * k:3 * k + 3])
        return out
    p0, lo, hi = [], [], []
    amp = max(ys.max() - ys.min(), 1e-6)
    for _, c in COMPONENTS:
        p0 += [amp / 2, c, 25.0]
        lo += [0.0, c - 30, 8.0]
        hi += [10 * amp, c + 30, 70.0]
    p0 += [0.0, 0.0]
    lo += [-np.inf, -np.inf]
    hi += [np.inf, np.inf]
    p, cov = curve_fit(model, xs, ys, p0=p0, bounds=(lo, hi), maxfev=40000)
    err = np.sqrt(np.clip(np.diag(cov), 0, None))
    out = {}
    for k, (name, _) in enumerate(COMPONENTS):
        a, c, w = p[3 * k:3 * k + 3]
        sa, sw = err[3 * k], err[3 * k + 2]
        area = a * w * np.sqrt(2 * np.pi)
        out[name] = {"area": area, "area_err": area * np.hypot(sa / max(a, 1e-12), sw / max(w, 1e-12)),
                     "center": c, "fwhm": 2.3548 * w}
    return out


def integral(x: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    sel = (x >= lo) & (x <= hi)
    return float(np.trapezoid(np.clip(y[sel], 0, None), x[sel])) if sel.sum() > 2 else float("nan")


def analyze(x: np.ndarray, y: np.ndarray) -> dict:
    o = np.argsort(x)
    x, y = x[o], y[o]
    yc = y - rubberband(x, y)
    dec = deconvolve(x, yc)
    cc = dec["CC"]["area"]
    res = {"FTIR_CO_CC": dec["CO"]["area"] / cc,
           "FTIR_water_frac": dec["H2O"]["area"] / (dec["H2O"]["area"] + cc),
           "FTIR_CC_center_cm-1": dec["CC"]["center"], "FTIR_CO_center_cm-1": dec["CO"]["center"]}
    for name, (lo, hi) in INTEGRALS.items():
        res[f"FTIR_{name}_CC"] = integral(x, yc, lo, hi) / cc
    return res


def summarize(results: list[dict]) -> dict:
    keys = results[0].keys()
    return {k: (float(np.mean([r[k] for r in results])),
                float(np.std([r[k] for r in results], ddof=1)) if len(results) > 1 else float("nan"), len(results))
            for k in keys}


def to_rows(summary: dict, sample_id: str, files: str = "", max_water: float = 0.5) -> list[dict]:
    rows = []
    for i, (q, (v, s, n)) in enumerate(summary.items(), 1):
        note = ""
        if q == "FTIR_water_frac" and v > max_water:
            note = "sensível à umidade: repita após 24 h em dessecador (SOP-GO-CHAR-01)"
        rows.append({"measurement_id": f"M-FTIR-{sample_id}-{i:02d}", "go_sample_id": sample_id, "technique": "FTIR",
                     "quantity": q, "value": round(v, 5), "uncertainty": "" if np.isnan(s) else round(s, 5),
                     "uncertainty_type": "" if np.isnan(s) else "sd", "n_replicates": n,
                     "unit": "cm-1" if q.endswith("cm-1") else "a.u.",
                     "method_details": "rubberband + 3 gaussianas 1480–1800 cm-1 (C=O, H2O, C=C) (code/characterization/ftir.py)",
                     "raw_data_file": files, "notes": note})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spectra", nargs="+")
    ap.add_argument("--transmittance", action="store_true", help="entrada em %%T (convertida para absorbância)")
    ap.add_argument("--sample", default="GO-SAMPLE")
    ap.add_argument("--max-water-fraction", type=float, default=0.5)
    ap.add_argument("--out")
    a = ap.parse_args()
    s = summarize([analyze(*read_xy(f, a.transmittance)) for f in a.spectra])
    for k, (v, sd, n) in s.items():
        print(f"{k:22s} {v:9.4f} ± {sd:.4f} (n={n})")
    if a.out:
        rows = to_rows(s, a.sample, "|".join(a.spectra), a.max_water_fraction)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
