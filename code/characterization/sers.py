#!/usr/bin/env python3
"""SERS: fator de intensificação analítico e uniformidade (§4.4: "quando aplicável, resposta SERS").

    EF = (I_SERS / c_SERS) / (I_ref / c_ref)            (fator analítico; Le Ru et al., J. Phys. Chem. C 2007)
I = área da banda da molécula-sonda (ex.: R6G 1362 ou 1510 cm⁻¹; 4-ATP 1078 cm⁻¹; 4-MBA 1075 cm⁻¹) após linha de base
linear local; c = concentração da sonda na medida SERS e na referência (Raman normal, mesmo laser/potência/tempo).
Vários espectros SERS (mapa ou pontos): EF médio, RSD (uniformidade; < 20 % é o usual para substrato "uniforme") e
limite de detecção opcional pela curva de calibração (3σ do branco / inclinação).

Uso:
    python code/characterization/sers.py --sers s1.csv s2.csv s3.csv --ref ref.csv --band 1362 --window 30 \\
           --c-sers 1e-6 --c-ref 1e-2 --synthesis SYN-0001 --out sers.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))


def band_area(x: np.ndarray, y: np.ndarray, center: float, half_window: float) -> float:
    """Área da banda acima da reta que liga as bordas da janela."""
    o = np.argsort(x)
    x, y = np.asarray(x, float)[o], np.asarray(y, float)[o]
    sel = (x >= center - half_window) & (x <= center + half_window)
    xs, ys = x[sel], y[sel]
    if len(xs) < 5:
        return float("nan")
    base = np.interp(xs, [xs[0], xs[-1]], [ys[:3].mean(), ys[-3:].mean()])
    return float(np.trapezoid(np.clip(ys - base, 0, None), xs))


def enhancement(sers: list[tuple[np.ndarray, np.ndarray]], ref: tuple[np.ndarray, np.ndarray], band: float,
                window: float, c_sers: float, c_ref: float) -> dict:
    I_ref = band_area(*ref, band, window)
    I_s = np.array([band_area(x, y, band, window) for x, y in sers])
    ef = (I_s / c_sers) / (I_ref / c_ref)
    return {"SERS_EF": (float(np.mean(ef)), float(np.std(ef, ddof=1)) if len(ef) > 1 else float("nan")),
            "SERS_RSD_pct": (float(100 * np.std(I_s, ddof=1) / np.mean(I_s)) if len(I_s) > 1 else float("nan"),
                             float("nan")),
            "log10_SERS_EF": (float(np.log10(np.mean(ef))), float("nan")), "n_spectra": int(len(ef))}


def lod(conc: np.ndarray, intensity: np.ndarray, blank_sd: float) -> float:
    slope = np.polyfit(np.asarray(conc, float), np.asarray(intensity, float), 1)[0]
    return float(3 * blank_sd / slope)


def to_rows(r: dict, synthesis_id: str, band: float, files: str = "") -> list[dict]:
    rows = []
    for i, q in enumerate(("SERS_EF", "log10_SERS_EF", "SERS_RSD_pct"), 1):
        v, u = r[q]
        rows.append({"measurement_id": f"M-SERS-{synthesis_id}-{i:02d}", "synthesis_id": synthesis_id,
                     "technique": "SERS", "quantity": q, "value": float(f"{v:.5g}"),
                     "uncertainty": "" if not np.isfinite(u) else float(f"{u:.4g}"),
                     "uncertainty_type": "" if not np.isfinite(u) else "sd", "n_replicates": r["n_spectra"],
                     "unit": "%" if q.endswith("pct") else "a.u.",
                     "method_details": f"EF analítico, banda {band:g} cm-1 (code/characterization/sers.py)",
                     "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sers", nargs="+", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--band", type=float, required=True)
    ap.add_argument("--window", type=float, default=30.0, help="meia-largura da janela (cm-1)")
    ap.add_argument("--c-sers", type=float, required=True)
    ap.add_argument("--c-ref", type=float, required=True)
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    from uvvis import read_spectrum
    r = enhancement([read_spectrum(f) for f in a.sers], read_spectrum(a.ref), a.band, a.window, a.c_sers, a.c_ref)
    print(r)
    if a.out:
        rows = to_rows(r, a.synthesis, a.band, "|".join(a.sers + [a.ref]))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
