#!/usr/bin/env python3
"""SAXS de AuNP: Guinier e ajuste de esferas polidispersas (§4.4, §4.12: SAXS/WAXS como extensão condicional).

  * Guinier: ln I = ln I0 − (q·Rg)²/3, ajustado onde q·Rg < 1,3 (iterativo); para esfera, R = √(5/3)·Rg;
  * forma: esferas com distribuição gaussiana de raio (média R, σ_rel) + fundo constante, por mínimos quadrados em
    log I (o fator de forma P(q) = [3(sin qR − qR cos qR)/(qR)³]², ponderado por R⁶ — o volume ao quadrado).
Devolve size_mean_nm (= 2R), polidispersão relativa e Rg. O GO contribui com espalhamento em q baixo (lei de potência):
recorte a faixa de q (--qmin) ou subtraia o branco de GO (--blank).

Uso:
    python code/characterization/saxs.py iq.csv [--q-unit nm-1 --blank go.csv --qmin 0.1] --synthesis SYN-0001 --out m.csv
Entrada: q, I(q) (q em nm⁻¹ ou Å⁻¹).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))


def sphere_intensity(q: np.ndarray, R: float, sigma_rel: float, n: int = 41) -> np.ndarray:
    """Intensidade de esferas com raio gaussiano (média R, sd relativo sigma_rel), normalizada em q → 0."""
    Rs = R * (1 + sigma_rel * np.linspace(-3, 3, n)) if sigma_rel > 0 else np.array([R])
    Rs = Rs[Rs > 0]
    w = np.exp(-0.5 * ((Rs - R) / (sigma_rel * R)) ** 2) if sigma_rel > 0 else np.ones(1)
    qR = np.outer(q, Rs)
    with np.errstate(invalid="ignore", divide="ignore"):
        F = np.where(qR > 1e-6, 3 * (np.sin(qR) - qR * np.cos(qR)) / qR ** 3, 1.0)
    I = (F ** 2) @ (w * Rs ** 6)
    return I / (w * Rs ** 6).sum()


def guinier(q: np.ndarray, I: np.ndarray, max_qrg: float = 1.3) -> dict:
    sel = slice(0, max(5, len(q) // 5))
    Rg = None
    for _ in range(10):
        c = np.polyfit(q[sel] ** 2, np.log(I[sel]), 1)
        Rg = float(np.sqrt(max(-3 * c[0], 1e-12)))
        n = int(np.sum(q * Rg < max_qrg))
        if n < 5:
            break
        sel = slice(0, n)
    return {"Rg_nm": Rg, "R_sphere_nm": float(np.sqrt(5 / 3) * Rg)}


def fit_spheres(q: np.ndarray, I: np.ndarray, R0: float | None = None) -> dict:
    from scipy.optimize import least_squares
    R0 = R0 or guinier(q, I)["R_sphere_nm"]

    def resid(p):
        R, s, scale, bg = p
        return np.log(scale * sphere_intensity(q, R, s) + bg) - np.log(I)
    p0 = [R0, 0.1, I[0], max(I.min() * 0.1, 1e-12)]
    r = least_squares(resid, p0, bounds=([0.5, 0.0, 0.0, 0.0], [200.0, 0.5, np.inf, np.inf]))
    J = r.jac
    cov = np.linalg.pinv(J.T @ J) * np.sum(r.fun ** 2) / max(len(q) - 4, 1)
    err = np.sqrt(np.clip(np.diag(cov), 0, None))
    return {"size_mean_nm": (2 * r.x[0], 2 * err[0]), "size_cv": (r.x[1], err[1]), "background": r.x[3]}


def analyze(q: np.ndarray, I: np.ndarray, qmin: float = 0.0) -> dict:
    sel = (q >= qmin) & (I > 0)
    q, I = q[sel], I[sel]
    g = guinier(q, I)
    f = fit_spheres(q, I, g["R_sphere_nm"])
    return {"size_mean_nm": f["size_mean_nm"], "size_cv": f["size_cv"], "Rg_nm": (g["Rg_nm"], float("nan"))}


def to_rows(r: dict, synthesis_id: str, files: str = "") -> list[dict]:
    rows = []
    for i, (q, (v, u)) in enumerate(r.items(), 1):
        rows.append({"measurement_id": f"M-SAXS-{synthesis_id}-{i:02d}", "synthesis_id": synthesis_id,
                     "technique": "SAXS", "quantity": q, "value": round(float(v), 4),
                     "uncertainty": "" if not np.isfinite(u) else round(float(u), 4),
                     "uncertainty_type": "" if not np.isfinite(u) else "fit_se", "n_replicates": 1,
                     "unit": "nm" if q.endswith("nm") else "a.u.",
                     "method_details": "Guinier + esferas gaussianas (code/characterization/saxs.py)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--q-unit", choices=["nm-1", "A-1"], default="nm-1")
    ap.add_argument("--blank")
    ap.add_argument("--qmin", type=float, default=0.0)
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    from uvvis import read_spectrum
    q, I = read_spectrum(a.file)
    f = 10.0 if a.q_unit == "A-1" else 1.0
    if a.blank:
        qb, Ib = read_spectrum(a.blank)
        I = I - np.interp(q, qb, Ib)
    r = analyze(q * f, I, a.qmin)
    print(r)
    if a.out:
        rows = to_rows(r, a.synthesis, a.file)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
