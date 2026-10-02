#!/usr/bin/env python3
"""DLS pelo método dos cumulantes (ISO 22412:2017) a partir da função de autocorrelação g2(τ) (§4.2, §4.12).

    ln[g2(τ) − 1] = ln β − 2Γτ + μ₂τ² (− μ₃τ³/3)      Γ = D·q²,  q = 4π·n·sin(θ/2)/λ
    d_H (Z-average) = k_B·T / (3π·η·D)                 PDI = μ₂ / Γ²
O ajuste usa só a parte inicial da curva (g2 − 1 > `--cut` × intercepto), como recomenda a norma. A viscosidade da
água vem da equação de Vogel (η a T); para outro meio, informe --viscosity (mPa·s) e --refractive-index.
Para GO o diâmetro é APARENTE (folhas não são esferas): use como descritor relativo entre lotes (SOP-DLS-01).

Uso:
    python code/characterization/dls.py g2_med1.csv g2_med2.csv g2_med3.csv --angle 173 --wavelength 633 \\
           --temperature 25 [--tau-unit us] [--synthesis SYN-0001 | --sample GO-B01-S01] --out m.csv
Entrada: duas colunas (τ, g2) ou (τ, g2 − 1) — detectado automaticamente. Sem g2 exportável:
    python code/characterization/dls.py --instrument-table export_zetasizer.csv --synthesis SYN-0001 --out m.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))
KB = 1.380649e-23
TAU_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9}


def water_viscosity_mPas(T_C: float) -> float:
    """Equação de Vogel para a água (erro < 1 % entre 0 e 100 °C)."""
    T = T_C + 273.15
    return float(np.exp(-3.7188 + 578.919 / (T - 137.546)))


def q_vector(angle_deg: float, wavelength_nm: float, n: float = 1.333) -> float:
    return 4 * np.pi * n * np.sin(np.radians(angle_deg) / 2) / (wavelength_nm * 1e-9)


def cumulants(tau_s: np.ndarray, g2: np.ndarray, order: int = 2, cut: float = 0.1) -> dict:
    """Γ (1/s), μ₂ e β pelo ajuste polinomial de ln(g2 − 1) na parte inicial da curva."""
    g = np.asarray(g2, float)
    y = g - 1.0 if np.median(g[-max(5, len(g) // 20):]) > 0.5 else g   # g2 tende a 1, g2 − 1 tende a 0
    beta0 = np.max(y[:5])
    sel = (y > cut * beta0) & (tau_s > 0)
    idx = np.where(sel)[0]
    stop = idx[np.argmax(np.diff(np.r_[idx, idx[-1] + 2]) > 1)] + 1 if len(idx) else 0   # trecho inicial contínuo
    start = idx[0] if len(idx) else 0
    t, ly = tau_s[start:stop], np.log(y[start:stop])
    if len(t) < order + 3:
        raise ValueError("poucos pontos na parte inicial da correlação")
    c = np.polyfit(t, ly, order)[::-1]                 # ln β, −2Γ, μ₂, …
    gamma = -c[1] / 2
    mu2 = c[2] if order >= 2 else 0.0
    return {"Gamma_s-1": gamma, "mu2": mu2, "beta": float(np.exp(c[0])), "n_points": len(t)}


def z_average_nm(gamma: float, angle_deg: float, wavelength_nm: float, T_C: float, n: float = 1.333,
                 viscosity_mPas: float | None = None) -> float:
    eta = (viscosity_mPas if viscosity_mPas else water_viscosity_mPas(T_C)) * 1e-3
    D = gamma / q_vector(angle_deg, wavelength_nm, n) ** 2
    return KB * (T_C + 273.15) / (3 * np.pi * eta * D) * 1e9


def analyze(tau_s, g2, angle=173.0, wavelength=633.0, T_C=25.0, n=1.333, viscosity=None, cut=0.1) -> dict:
    c = cumulants(np.asarray(tau_s, float), np.asarray(g2, float), cut=cut)
    return {"hydrodynamic_nm": z_average_nm(c["Gamma_s-1"], angle, wavelength, T_C, n, viscosity),
            "PDI": max(0.0, c["mu2"] / c["Gamma_s-1"] ** 2), "intercept_beta": c["beta"]}


def read_corr(path: str, tau_unit: str = "us"):
    from uvvis import read_spectrum
    t, g = read_spectrum(path)
    return t * TAU_UNITS[tau_unit], g


def from_instrument_table(path: str) -> list[dict]:
    """Repasse de tabelas exportadas pelo instrumento (ex.: Zetasizer: colunas 'Z-Ave' e 'PdI'), uma linha por
    medida. Use quando o g2(τ) bruto não for exportável; o método fica registrado em method_details."""
    import pandas as pd
    df = pd.read_csv(path, sep=None, engine="python", encoding_errors="replace")
    norm = {c: re.sub(r"[^a-z0-9]", "", str(c).lower()) for c in df.columns}
    z = next((c for c, n in norm.items() if n.startswith(("zave", "zaverage"))), None)
    p = next((c for c, n in norm.items() if n in ("pdi", "pdl", "polydispersityindex")), None)
    if z is None or p is None:
        raise ValueError(f"{path}: colunas Z-average e PDI não encontradas ({list(df.columns)})")
    return [{"hydrodynamic_nm": float(a), "PDI": float(b), "intercept_beta": float("nan")}
            for a, b in zip(pd.to_numeric(df[z], errors="coerce"), pd.to_numeric(df[p], errors="coerce"))
            if np.isfinite(a) and np.isfinite(b)]


def to_rows(results: list[dict], sample_id: str = "", synthesis_id: str = "", files: str = "",
            method: str = "cumulantes ISO 22412 sobre g2(τ) (code/characterization/dls.py)") -> list[dict]:
    rows = []
    for i, q in enumerate(("hydrodynamic_nm", "PDI"), 1):
        v = [r[q] for r in results]
        r = {"measurement_id": f"M-DLS-{sample_id or synthesis_id}-{i:02d}", "technique": "DLS", "quantity": q,
             "value": round(float(np.mean(v)), 4),
             "uncertainty": round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else "",
             "uncertainty_type": "sd" if len(v) > 1 else "", "n_replicates": len(v),
             "unit": "nm" if q.endswith("nm") else "a.u.",
             "method_details": method, "raw_data_file": files}
        r["go_sample_id" if sample_id else "synthesis_id"] = sample_id or synthesis_id
        rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--instrument-table", help="CSV exportado pelo instrumento (Z-Ave, PdI) em vez de g2(τ)")
    ap.add_argument("--angle", type=float, default=173.0)
    ap.add_argument("--wavelength", type=float, default=633.0, help="nm")
    ap.add_argument("--temperature", type=float, default=25.0, help="°C")
    ap.add_argument("--refractive-index", type=float, default=1.333)
    ap.add_argument("--viscosity", type=float, help="mPa·s (padrão: água a T)")
    ap.add_argument("--tau-unit", default="us", choices=list(TAU_UNITS))
    ap.add_argument("--cut", type=float, default=0.1)
    ap.add_argument("--sample", default="")
    ap.add_argument("--synthesis", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.instrument_table:
        res, files = from_instrument_table(a.instrument_table), [a.instrument_table]
        method = "Z-average/PDI do software do instrumento (cumulantes ISO 22412), repassados"
    elif a.files:
        res, files = [analyze(*read_corr(f, a.tau_unit), a.angle, a.wavelength, a.temperature, a.refractive_index,
                              a.viscosity, a.cut) for f in a.files], a.files
        method = (f"cumulantes ISO 22412 sobre g2(τ); θ={a.angle}°, λ={a.wavelength} nm, T={a.temperature} °C "
                  "(code/characterization/dls.py)")
    else:
        ap.error("informe arquivos g2(τ) ou --instrument-table")
    for i, r in enumerate(res):
        print(f"{i + 1}: Z-average {r['hydrodynamic_nm']:.2f} nm, PDI {r['PDI']:.3f}, β {r['intercept_beta']:.3f}")
    if a.out:
        rows = to_rows(res, a.sample, a.synthesis, "|".join(files), method)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
