#!/usr/bin/env python3
"""XRD de GO e de GO–AuNP: espaçamento basal, cristalito (Scherrer), nº de camadas e cristalito de Au (§4.2, §4.4).

Picos ajustados por pseudo-Voigt + fundo linear, em janelas de 2θ (Cu Kα, λ = 1,5406 Å por padrão):
  GO (001)        6–14°   -> d001_nm (Bragg), Lc_nm (Scherrer, K = 0,89), n_layers = Lc/d + 1
  grafite (002)   24–28°  -> fração grafítica residual = A(002)/(A(001) + A(002))
  Au (111)        36–40°  -> Au_crystallite_nm (Scherrer, K = 0,94): o "tamanho de cristalito" da proposta
O alargamento instrumental (--instrument-fwhm, em graus, de um padrão como LaB₆/CeO₂ — veja
datasets/xrd-ceo2-calibration) é removido em quadratura. d001 depende da umidade (água intercalada): registre a
condição da amostra (SOP-GO-CHAR-01).

Uso:
    python code/characterization/xrd.py difratograma.xy [--wavelength 1.5406 --instrument-fwhm 0.08]
           [--sample GO-B01-S01 | --synthesis SYN-0001] --out m.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))
CU_KA1 = 1.5406
WINDOWS = {"GO001": (6.0, 14.0), "G002": (24.0, 28.5), "Au111": (36.0, 40.0)}
SCHERRER_K = {"GO001": 0.89, "G002": 0.89, "Au111": 0.94}


def read_xy(path: str):
    from uvvis import read_spectrum
    return read_spectrum(path)


def pseudo_voigt(x, a, c, fwhm, eta):
    s = fwhm / 2.3548
    g = np.exp(-0.5 * ((x - c) / s) ** 2)
    lz = 1.0 / (1.0 + ((x - c) / (fwhm / 2)) ** 2)
    return a * (eta * lz + (1 - eta) * g)


def fit_peak(x: np.ndarray, y: np.ndarray, window: tuple[float, float]) -> dict | None:
    from scipy.optimize import curve_fit
    sel = (x >= window[0]) & (x <= window[1])
    xs, ys = x[sel], y[sel]
    if sel.sum() < 8:
        return None
    b0 = np.polyfit([xs[0], xs[-1]], [ys[:3].mean(), ys[-3:].mean()], 1)
    resid = ys - np.polyval(b0, xs)
    if resid.max() <= 5 * max(np.std(resid[:5]), 1e-12):   # sem pico acima do ruído das bordas
        return None
    c0 = xs[np.argmax(resid)]

    def model(xx, a, c, w, eta, m, q):
        return pseudo_voigt(xx, a, c, w, eta) + m * xx + q
    p0 = [resid.max(), c0, (window[1] - window[0]) / 8, 0.5, b0[0], b0[1]]
    lo = [0, window[0], 0.02, 0, -np.inf, -np.inf]
    hi = [np.inf, window[1], window[1] - window[0], 1, np.inf, np.inf]
    try:
        p, cov = curve_fit(model, xs, ys, p0=p0, bounds=(lo, hi), maxfev=20000)
    except RuntimeError:
        return None
    err = np.sqrt(np.clip(np.diag(cov), 0, None))
    area = p[0] * p[2] * (p[3] * np.pi / 2 + (1 - p[3]) * np.sqrt(np.pi / (4 * np.log(2))))
    return {"two_theta": p[1], "two_theta_err": err[1], "fwhm_deg": p[2], "fwhm_err": err[2], "eta": p[3],
            "area": area}


def bragg_d_nm(two_theta_deg: float, wavelength_A: float = CU_KA1) -> float:
    return wavelength_A / (2 * np.sin(np.radians(two_theta_deg) / 2)) / 10.0


def scherrer_nm(two_theta_deg: float, fwhm_deg: float, K: float, wavelength_A: float = CU_KA1,
                instrument_fwhm_deg: float = 0.0) -> float:
    beta = np.sqrt(max(fwhm_deg ** 2 - instrument_fwhm_deg ** 2, 1e-12))
    return K * wavelength_A / (np.radians(beta) * np.cos(np.radians(two_theta_deg) / 2)) / 10.0


def analyze(x: np.ndarray, y: np.ndarray, wavelength_A: float = CU_KA1, instrument_fwhm: float = 0.0) -> dict:
    o = np.argsort(x)
    x, y = x[o], y[o]
    out, peaks = {}, {k: fit_peak(x, y, w) for k, w in WINDOWS.items()}
    go = peaks["GO001"]
    if go:
        d = bragg_d_nm(go["two_theta"], wavelength_A)
        dd = abs(bragg_d_nm(go["two_theta"] + go["two_theta_err"], wavelength_A) - d)
        lc = scherrer_nm(go["two_theta"], go["fwhm_deg"], SCHERRER_K["GO001"], wavelength_A, instrument_fwhm)
        out.update({"d001_nm": (d, dd), "Lc_nm": (lc, lc * go["fwhm_err"] / go["fwhm_deg"]),
                    "n_layers": (lc / d + 1, np.nan)})
    g2 = peaks["G002"]
    if go or g2:
        a1, a2 = (go or {}).get("area", 0.0), (g2 or {}).get("area", 0.0)
        out["frac_graphitic"] = (a2 / (a1 + a2) if a1 + a2 > 0 else np.nan, np.nan)
    au = peaks["Au111"]
    if au:
        L = scherrer_nm(au["two_theta"], au["fwhm_deg"], SCHERRER_K["Au111"], wavelength_A, instrument_fwhm)
        out["Au_crystallite_nm"] = (L, L * au["fwhm_err"] / au["fwhm_deg"])
        out["Au111_two_theta_deg"] = (au["two_theta"], au["two_theta_err"])
    return out


def to_rows(res: dict, sample_id: str = "", synthesis_id: str = "", files: str = "") -> list[dict]:
    rows = []
    for i, (q, (v, s)) in enumerate(res.items(), 1):
        r = {"measurement_id": f"M-XRD-{sample_id or synthesis_id}-{i:02d}", "technique": "XRD", "quantity": q,
             "value": round(float(v), 5), "uncertainty": "" if not np.isfinite(s) else round(float(s), 5),
             "uncertainty_type": "" if not np.isfinite(s) else "fit_se", "n_replicates": 1,
             "unit": "nm" if q.endswith("_nm") else ("deg" if q.endswith("_deg") else "a.u."),
             "method_details": "pseudo-Voigt + fundo linear; Bragg; Scherrer (code/characterization/xrd.py)",
             "raw_data_file": files}
        r["go_sample_id" if sample_id else "synthesis_id"] = sample_id or synthesis_id
        rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern")
    ap.add_argument("--wavelength", type=float, default=CU_KA1, help="Å (Cu Kα1 = 1,5406)")
    ap.add_argument("--instrument-fwhm", type=float, default=0.0, help="alargamento instrumental (graus 2θ)")
    ap.add_argument("--sample", default="")
    ap.add_argument("--synthesis", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = analyze(*read_xy(a.pattern), a.wavelength, a.instrument_fwhm)
    for k, (v, s) in res.items():
        print(f"{k:22s} {v:9.4f}" + (f" ± {s:.4f}" if np.isfinite(s) else ""))
    if a.out and res:
        rows = to_rows(res, a.sample, a.synthesis, a.pattern)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
