#!/usr/bin/env python3
"""Potencial zeta a partir da mobilidade eletroforética (§4.2 GO; §4.12 produto).

    ζ = 3ημ / (2ε f(κa))      Henry, com f(κa) pela aproximação de Ohshima (1994):
    f(κa) = 1 + 1 / (2 (1 + 2.5 / (κa (1 + 2 e^(−κa))))³)      (f → 1,5: Smoluchowski; f → 1: Hückel)
κ⁻¹ (comprimento de Debye) vem da força iônica (água, T); ε da água por Malmberg & Maryott; η pela equação de Vogel.
Para GO (folhas) o raio é APARENTE: o ζ é usado como descritor comparativo entre lotes. Também aceita a tabela
exportada pelo instrumento (coluna "Zeta Potential (mV)" ou "zeta") e só faz o resumo.
Estabilidade coloidal: |ζ| ≥ 30 mV é a referência usual (classificação indicativa, não critério de QC).

Uso:
    python code/characterization/zeta.py --mobility 2.1 2.0 2.2 [--temperature 25 --ionic-strength-mM 1 --radius-nm 50]
           [--sample GO-B01-S01 | --synthesis SYN-0001] --out m.csv
    python code/characterization/zeta.py --instrument-table export.csv --synthesis SYN-0001
"""
from __future__ import annotations

import argparse
import csv
import re

import numpy as np

E0 = 8.8541878128e-12
KB, E_CHARGE, NA = 1.380649e-23, 1.602176634e-19, 6.02214076e23


def water_viscosity_mPas(T_C: float) -> float:
    return float(np.exp(-3.7188 + 578.919 / (T_C + 273.15 - 137.546)))


def water_permittivity(T_C: float) -> float:
    """ε_r da água (Malmberg & Maryott 1956)."""
    return 87.740 - 0.40008 * T_C + 9.398e-4 * T_C ** 2 - 1.410e-6 * T_C ** 3


def debye_length_nm(ionic_strength_mM: float, T_C: float = 25.0) -> float:
    eps = water_permittivity(T_C) * E0
    I = ionic_strength_mM * 1e-3 * 1e3          # mol/m³
    return float(np.sqrt(eps * KB * (T_C + 273.15) / (2 * NA * E_CHARGE ** 2 * I)) * 1e9)


def henry_f(ka: float) -> float:
    return 1.0 + 1.0 / (2.0 * (1.0 + 2.5 / (ka * (1.0 + 2.0 * np.exp(-ka)))) ** 3)


def zeta_mV(mobility_um_cm_Vs: float, T_C: float = 25.0, ionic_strength_mM: float | None = None,
            radius_nm: float | None = None) -> float:
    """Mobilidade em μm·cm/(V·s) (unidade dos instrumentos) → ζ em mV. Sem força iônica/raio: Smoluchowski."""
    mu = mobility_um_cm_Vs * 1e-8                 # m²/(V·s)
    eta = water_viscosity_mPas(T_C) * 1e-3
    eps = water_permittivity(T_C) * E0
    f = 1.5 if not (ionic_strength_mM and radius_nm) else henry_f(radius_nm / debye_length_nm(ionic_strength_mM, T_C))
    return float(3 * eta * mu / (2 * eps * f) * 1e3)


def from_instrument_table(path: str) -> list[float]:
    import pandas as pd
    df = pd.read_csv(path, sep=None, engine="python", encoding_errors="replace")
    col = next((c for c in df.columns if re.sub(r"[^a-z]", "", str(c).lower()).startswith("zeta")), None)
    if col is None:
        raise ValueError(f"{path}: coluna de zeta não encontrada ({list(df.columns)})")
    return [float(v) for v in pd.to_numeric(df[col], errors="coerce") if np.isfinite(v)]


def to_rows(zetas: list[float], sample_id: str = "", synthesis_id: str = "", method: str = "", files: str = ""):
    z = np.asarray(zetas, float)
    r = {"measurement_id": f"M-ZETA-{sample_id or synthesis_id}-01", "technique": "zeta", "quantity": "zeta_mV",
         "value": round(float(z.mean()), 3), "uncertainty": round(float(z.std(ddof=1)), 3) if len(z) > 1 else "",
         "uncertainty_type": "sd" if len(z) > 1 else "", "n_replicates": int(len(z)), "unit": "mV",
         "method_details": method, "raw_data_file": files,
         "notes": "|ζ| ≥ 30 mV: estável (indicativo)" if abs(z.mean()) >= 30 else "|ζ| < 30 mV: estabilidade limitada"}
    r["go_sample_id" if sample_id else "synthesis_id"] = sample_id or synthesis_id
    return [r]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mobility", nargs="*", type=float, help="μm·cm/(V·s), uma por medida")
    ap.add_argument("--instrument-table")
    ap.add_argument("--temperature", type=float, default=25.0)
    ap.add_argument("--ionic-strength-mM", type=float)
    ap.add_argument("--radius-nm", type=float)
    ap.add_argument("--sample", default="")
    ap.add_argument("--synthesis", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.instrument_table:
        z, method, files = from_instrument_table(a.instrument_table), "ζ do software do instrumento", a.instrument_table
    elif a.mobility:
        z = [zeta_mV(m, a.temperature, a.ionic_strength_mM, a.radius_nm) for m in a.mobility]
        model = "Henry/Ohshima" if a.ionic_strength_mM and a.radius_nm else "Smoluchowski"
        method, files = f"{model}, T={a.temperature} °C (code/characterization/zeta.py)", ""
    else:
        ap.error("informe --mobility ou --instrument-table")
    print(f"ζ = {np.mean(z):.1f} ± {np.std(z, ddof=1) if len(z) > 1 else float('nan'):.1f} mV (n={len(z)})")
    if a.out:
        rows = to_rows(z, a.sample, a.synthesis, method, files)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
