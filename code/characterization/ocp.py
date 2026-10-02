#!/usr/bin/env python3
"""Potencial de circuito aberto (OCP) durante a redução (§4.3; Halford et al. 2024, 2025) — variável de PROCESSO.

A proposta trata o OCP como diagnóstico do ambiente redox, não como prova causal. Da curva E(t) extraímos:
  E0_mV (início), Efinal_mV (média dos últimos 10 %), dE_mV (variação total), t_induction_s (tempo até a taxa
  |dE/dt| passar de 10 % do máximo — início da redução), t_max_rate_s (taxa máxima) e t95_s (tempo até 95 % da
  variação total — fim do transiente). A curva é suavizada (Savitzky–Golay) antes das derivadas.

Uso:
    python code/characterization/ocp.py ocp.csv [--time-unit s] --synthesis SYN-0001 --out ocp_m.csv
Entrada: duas colunas (tempo, E em mV; ou V com --volts).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))


def features(t: np.ndarray, E: np.ndarray, window_frac: float = 0.05) -> dict:
    from scipy.signal import savgol_filter
    o = np.argsort(t)
    t, E = np.asarray(t, float)[o], np.asarray(E, float)[o]
    w = max(5, int(len(t) * window_frac) | 1)
    Es = savgol_filter(E, w, 2) if len(E) > w else E
    rate = np.gradient(Es, t)
    a = np.abs(rate)
    i_max = int(np.argmax(a))
    i_ind = int(np.argmax(a >= 0.1 * a[i_max]))
    tail = max(1, len(E) // 10)
    E0, Ef = float(np.mean(E[:max(1, len(E) // 50)])), float(np.mean(E[-tail:]))
    dE = Ef - E0
    reach = np.abs(Es - E0) >= 0.95 * abs(dE)
    i95 = int(np.argmax(reach)) if reach.any() else len(t) - 1
    return {"E0_mV": E0, "Efinal_mV": Ef, "dE_mV": dE, "t_induction_s": float(t[i_ind] - t[0]),
            "t_max_rate_s": float(t[i_max] - t[0]), "max_rate_mV_s": float(rate[i_max]), "t95_s": float(t[i95] - t[0])}


def to_rows(f: dict, synthesis_id: str, files: str = "") -> list[dict]:
    return [{"measurement_id": f"M-OCP-{synthesis_id}-{i:02d}", "synthesis_id": synthesis_id, "technique": "OCP",
             "quantity": q, "value": round(v, 4), "uncertainty": "", "uncertainty_type": "", "n_replicates": 1,
             "unit": "s" if q.endswith("_s") else ("mV/s" if q.endswith("mV_s") else "mV"),
             "method_details": "Savitzky–Golay + derivada (code/characterization/ocp.py); variável de processo",
             "raw_data_file": files} for i, (q, v) in enumerate(f.items(), 1)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--time-unit", choices=["s", "min"], default="s")
    ap.add_argument("--volts", action="store_true")
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    from uvvis import read_spectrum
    t, E = read_spectrum(a.file)
    f = features(t * (60 if a.time_unit == "min" else 1), E * (1000 if a.volts else 1))
    for k, v in f.items():
        print(f"{k:16s} {v:10.3f}")
    if a.out:
        rows = to_rows(f, a.synthesis, a.file)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
