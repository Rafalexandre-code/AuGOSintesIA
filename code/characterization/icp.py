#!/usr/bin/env python3
"""Balanço de Au por ICP-OES/ICP-MS (§4.12: "ICP-OES poderá auxiliar no balanço de Au").

Medidas (mg/L de Au, com diluição): dispersão TOTAL digerida e SOBRENADANTE após centrifugação (Au não reduzido ou
partículas que não sedimentam). Com o volume e as massas adicionadas:
    Au_adicionado   = c(HAuCl4) · V · M(Au)
    recuperação     = Au_total_medido / Au_adicionado          (fecha o balanço? 0,9–1,1 é o aceitável usual)
    conversão (%)   = 100 · (1 − Au_sobrenadante / Au_total)
    carga de Au (%) = 100 · Au_no_sólido / (Au_no_sólido + massa de GO)
Incertezas por propagação de primeira ordem das incertezas relativas das concentrações.

Uso:
    python code/characterization/icp.py --total 96.2 --supernatant 4.1 --dilution 10 --volume-mL 10 \\
           --HAuCl4-mM 0.5 --GO-mg-mL 0.2 [--rel-unc 0.03] --synthesis SYN-0001 --out icp.csv
"""
from __future__ import annotations

import argparse
import csv

import numpy as np

M_AU = 196.96657


def balance(total_mg_L: float, supernatant_mg_L: float, volume_mL: float, HAuCl4_mM: float, GO_mg_mL: float,
            dilution: float = 1.0, rel_unc: float = 0.03) -> dict:
    tot = total_mg_L * dilution
    sup = supernatant_mg_L * dilution
    added = HAuCl4_mM * M_AU                                   # mg/L
    solid = max(tot - sup, 0.0)
    au_solid_mg = solid * volume_mL / 1000
    go_mg = GO_mg_mL * volume_mL
    conv = 1 - sup / tot if tot > 0 else float("nan")
    conv_u = (sup / tot) * np.sqrt(2) * rel_unc if tot > 0 else float("nan")
    load = au_solid_mg / (au_solid_mg + go_mg) if au_solid_mg + go_mg > 0 else float("nan")
    load_u = load * (1 - load) * rel_unc * np.sqrt(2) * (tot / max(solid, 1e-12)) if np.isfinite(load) else float("nan")
    return {"recovery": (tot / added if added > 0 else float("nan"), rel_unc * tot / added if added > 0 else float("nan")),
            "yield_pct": (100 * conv, 100 * conv_u), "Au_loading_wt": (100 * load, 100 * load_u),
            "Au_supernatant_mg_L": (sup, rel_unc * sup), "balance_closes": bool(0.9 <= tot / added <= 1.1)
            if added > 0 else False}


def to_rows(b: dict, synthesis_id: str, technique: str = "ICP-OES", files: str = "") -> list[dict]:
    units = {"recovery": "fraction", "yield_pct": "%", "Au_loading_wt": "wt%", "Au_supernatant_mg_L": "mg/L"}
    rows = []
    for i, q in enumerate(units, 1):
        v, u = b[q]
        rows.append({"measurement_id": f"M-ICP-{synthesis_id}-{i:02d}", "synthesis_id": synthesis_id,
                     "technique": technique, "quantity": q, "value": round(v, 4), "uncertainty": round(u, 4),
                     "uncertainty_type": "instrument", "n_replicates": 1, "unit": units[q],
                     "method_details": "balanço de Au: total digerido × sobrenadante (code/characterization/icp.py)",
                     "raw_data_file": files,
                     "notes": "" if q != "recovery" or b["balance_closes"] else "balanço NÃO fecha (0,9–1,1): revisar"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--total", "--supernatant", "--volume-mL", "--HAuCl4-mM", "--GO-mg-mL"):
        ap.add_argument(k, type=float, required=True)
    ap.add_argument("--dilution", type=float, default=1.0)
    ap.add_argument("--rel-unc", type=float, default=0.03)
    ap.add_argument("--technique", choices=["ICP-OES", "ICP-MS"], default="ICP-OES")
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    b = balance(a.total, a.supernatant, a.volume_mL, a.HAuCl4_mM, a.GO_mg_mL, a.dilution, a.rel_unc)
    print({k: v for k, v in b.items()})
    if a.out:
        rows = to_rows(b, a.synthesis, a.technique)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
