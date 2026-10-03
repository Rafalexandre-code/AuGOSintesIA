#!/usr/bin/env python3
"""XPS de óxido de grafeno: fundo de Shirley + deconvolução do C 1s e razão C/O pelo survey.

Componentes do C 1s (posições relativas ao C–C/C=C, padrão 284,8 eV; pseudo-Voigt com fração lorentziana 0,3):
  C–C/C=C 284,8 · C–O (hidroxila/epóxi) +2,0 · C=O +3,1 · O–C=O +4,2  (limites ±0,4 eV; larguras 0,7–2,2 eV; os três
componentes oxidados compartilham a mesma largura, como é usual para evitar sobreajuste)
A atribuição é propositalmente conservadora (§4.2; ver Dimiev, Halbig & Talyzin 2026): o sp2 assimétrico e o
satélite π–π* não são modelados à parte; reporte o modelo usado junto com os números.

C/O pelo survey: (A_C1s/RSF_C)/(A_O1s/RSF_O). Os RSF dependem do instrumento — o padrão (C 1s = 1,00;
O 1s = 2,93, Scofield para Al Kα) só serve se o software do equipamento não fornecer os seus.

Uso:
    python code/characterization/xps.py c1s.csv [--sample GO-B01-S01 --out medidas.csv]
    python code/characterization/xps.py c1s.csv --survey-areas 12500 8300           # também calcula C/O
Arquivos: duas colunas (energia de ligação em eV, contagens).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))

COMPONENTS = [("CC", 0.0), ("C-O", 2.0), ("C=O", 3.1), ("O-C=O", 4.2)]
RSF_DEFAULT = {"C1s": 1.00, "O1s": 2.93, "N1s": 1.80, "S2p": 1.68}   # Scofield (C 1s = 1); ajuste ao instrumento


def shirley(be: np.ndarray, y: np.ndarray, tol: float = 1e-6, max_iter: int = 100, n_end: int = 5) -> np.ndarray:
    """Fundo de Shirley iterativo (energia de ligação crescente ou decrescente). Os níveis das extremidades são a
    média de n_end pontos de cada lado (um ponto só torna o fundo sensível ao ruído)."""
    order = np.argsort(be)
    x, s = be[order], y[order]
    k = max(1, min(n_end, len(s) // 10))
    lo, hi = float(np.mean(s[:k])), float(np.mean(s[-k:]))   # lado de menor BE (fundo baixo) e de maior BE (alto)
    bg = np.full_like(s, lo, dtype=float)
    for _ in range(max_iter):
        signal = s - bg
        cum = np.concatenate([[0], np.cumsum((signal[1:] + signal[:-1]) / 2 * np.diff(x))])
        total = cum[-1] if cum[-1] != 0 else 1.0
        new = lo + (hi - lo) * cum / total
        if np.max(np.abs(new - bg)) < tol * max(abs(hi), 1):
            bg = new
            break
        bg = new
    out = np.empty_like(bg)
    out[order] = bg
    return out


def fit_c1s(be: np.ndarray, counts: np.ndarray, ref_cc: float = 284.8, window: tuple[float, float] = (281.0, 293.0)) -> dict:
    from lmfit.models import PseudoVoigtModel
    sel = (be >= window[0]) & (be <= window[1])
    x, y = be[sel], counts[sel]
    y = y - shirley(x, y)
    model, pars = None, None
    for name, shift in COMPONENTS:
        m = PseudoVoigtModel(prefix=f"{name.replace('-', '_').replace('=', 'e')}_")
        p = m.make_params()
        pre = m.prefix
        p[f"{pre}center"].set(value=ref_cc + shift, min=ref_cc + shift - 0.4, max=ref_cc + shift + 0.4)
        if name in ("C=O", "O-C=O"):                                 # oxidados compartilham a largura do C–O
            p[f"{pre}sigma"].set(expr="C_O_sigma")
        else:
            p[f"{pre}sigma"].set(value=0.6, min=0.35, max=1.1)      # FWHM ≈ 2σ: 0,7–2,2 eV
        p[f"{pre}fraction"].set(value=0.3, vary=False)
        p[f"{pre}amplitude"].set(value=float(y.max()) * 1.2, min=0)
        if model is None:
            model, pars = m, p
        else:
            model = model + m
            pars.update(p)
    res = model.fit(y, pars, x=x)
    areas = {}
    for name, _ in COMPONENTS:
        pre = f"{name.replace('-', '_').replace('=', 'e')}_"
        areas[name] = (res.params[f"{pre}amplitude"].value, res.params[f"{pre}amplitude"].stderr,
                       res.params[f"{pre}center"].value, res.params[f"{pre}fwhm"].value)
    tot = sum(v[0] for v in areas.values())
    out = {"r2": float(1 - np.sum(res.residual ** 2) / np.sum((y - y.mean()) ** 2))}
    for name, (a, s, c, w) in areas.items():
        out[f"C1s_{name}_pct"] = (100 * a / tot, 100 * s / tot if s else None)
        out[f"C1s_{name}_BE_eV"] = (c, None)
        out[f"C1s_{name}_FWHM_eV"] = (w, None)
    ox = sum(areas[n][0] for n in ("C-O", "C=O", "O-C=O"))
    out["C1s_oxidized_pct"] = (100 * ox / tot, None)
    return out


def c_over_o(area_c1s: float, area_o1s: float, rsf: dict | None = None) -> float:
    rsf = rsf or RSF_DEFAULT
    return (area_c1s / rsf["C1s"]) / (area_o1s / rsf["O1s"])


def survey_composition(areas: dict[str, float], rsf: dict | None = None) -> dict:
    """Composição atômica pelo survey: at% de cada elemento e razões ao C (O/C, S/C — enxofre/organossulfatos do
    método de Hummers, §4.2; N/C). Áreas por linha (ex.: {"C1s": …, "O1s": …, "S2p": …})."""
    rsf = {**RSF_DEFAULT, **(rsf or {})}
    n = {k: v / rsf[k] for k, v in areas.items()}
    tot = sum(n.values())
    out = {f"{k[:-2] if k[-1] in 'sp' else k}_at_pct": (100 * v / tot, None) for k, v in n.items()}
    for k, v in n.items():
        if k != "C1s" and "C1s" in n:
            out[f"{k.rstrip('spd0123456789')}_C_ratio"] = (v / n["C1s"], None)
    if "O1s" in n:
        out["C_O_ratio"] = (n["C1s"] / n["O1s"], None)
    return out


def to_rows(results: dict, sample_id: str, files: str = "") -> list[dict]:
    rows = []
    for i, (q, (v, s)) in enumerate(results.items(), 1):
        if q == "r2":
            continue
        unit = "%" if q.endswith("pct") else ("eV" if q.endswith("eV") else "a.u.")
        rows.append({"measurement_id": f"M-XPS-{sample_id}-{i:03d}", "go_sample_id": sample_id, "technique": "XPS",
                     "quantity": q.replace("_pct", "").replace("_eV", ""), "value": round(v, 4),
                     "uncertainty": round(s, 4) if s else "", "uncertainty_type": "instrument" if s else "",
                     "n_replicates": 1, "unit": unit,
                     "method_details": "Shirley; pseudo-Voigt (η=0,3); C-C 284,8 eV; C-O +2,0; C=O +3,1; O-C=O +4,2",
                     "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("c1s")
    ap.add_argument("--ref-cc", type=float, default=284.8)
    ap.add_argument("--survey-areas", nargs=2, type=float, metavar=("A_C1s", "A_O1s"))
    ap.add_argument("--rsf", nargs=2, type=float, metavar=("RSF_C", "RSF_O"))
    ap.add_argument("--survey", nargs="+", metavar="LINHA=ÁREA", help="áreas do survey (ex.: C1s=… O1s=… S2p=…): "
                                                                     "at%% e razões O/C, S/C, N/C")
    ap.add_argument("--sample", default="SAMPLE")
    ap.add_argument("--out")
    a = ap.parse_args()
    from uvvis import read_spectrum
    be, cts = read_spectrum(a.c1s)
    r = fit_c1s(be, cts, a.ref_cc)
    if a.survey:
        r.update(survey_composition({k: float(v) for k, v in (x.split("=", 1) for x in a.survey)}))
    if a.survey_areas:
        rsf = {"C1s": a.rsf[0], "O1s": a.rsf[1]} if a.rsf else None
        r["C_O_ratio"] = (c_over_o(*a.survey_areas, rsf), None)
    for k, v in r.items():
        print(f"{k:22} {v if k == 'r2' else v[0]:.3f}")
    if a.out:
        rows = to_rows(r, a.sample, a.c1s)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
