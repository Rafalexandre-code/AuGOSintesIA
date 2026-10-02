#!/usr/bin/env python3
"""Simulador de brinquedo de síntese GO–AuNP — gera dados SIMULADOS (nunca medidos) para testar o encadeamento
completo e para as simulações de poder/benchmark (§4.11, §4.15). Não é um modelo químico validado.

Mecanismo (qualitativo, inspirado na literatura, com parâmetros arbitrários):
  * tamanho médio: nucleação mais rápida (mais redutor, mais Au(III), mais sítios de O no GO — lotes de C/O menor —,
    temperatura maior) → partículas menores; iodeto no lote do estabilizante/redutor aumenta o tamanho;
    o equipamento (hardware) desloca a temperatura efetiva;
  * tempo de reação: o rendimento satura (1 − e^(−t/15 min)) e as partículas crescem devagar (amadurecimento de
    Ostwald, ~ +6 % por fator e de tempo);
  * polidispersidade: cresce longe do pH ótimo (que depende do lote) e com impurezas;
  * espectro: extinção de Mie (code/spectral/mie.py, Au de Johnson & Christy, população log-normal) × rendimento,
    somada a um fundo de GO ~λ⁻³ e a ruído de medida;
  * a perda espectral J é calculada pelo MESMO código usado nos dados reais (code/spectral/uvvis.py).
"""
from __future__ import annotations

import functools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "spectral"))
import mie  # noqa: E402
import uvvis  # noqa: E402

WL = np.arange(400.0, 801.0, 4.0)
NOISE_SD = 0.004                     # desvio de medida da absorbância (sₘ da Eq. 1)
TARGET_D, TARGET_SIGMA = 20.0, 0.08  # espectro-alvo E*: AuNP de 20 nm, 8 % de dispersão

# lotes de GO: C/O (XPS) e ID/IG (Raman). L1–L3 desenvolvimento; L4–L6 reservados (confirmação)
BATCHES = {"L1": {"C_O_ratio": 2.2, "ID_IG": 0.92}, "L2": {"C_O_ratio": 1.8, "ID_IG": 1.02},
           "L3": {"C_O_ratio": 1.5, "ID_IG": 1.12}, "L4": {"C_O_ratio": 2.0, "ID_IG": 0.97},
           "L5": {"C_O_ratio": 1.6, "ID_IG": 1.08}, "L6": {"C_O_ratio": 2.4, "ID_IG": 0.88}}
# lotes de reagente (redutor/estabilizante): impureza de iodeto (ppm)
REAGENT_LOTS = {"RED-A": {"iodide_ppm": 2.0}, "RED-B": {"iodide_ppm": 45.0}}
HARDWARE_OFFSET_C = {"hot_plate": 0.0, "water_bath": -4.0, "flow_reactor": 3.0}

SPACE = {"HAuCl4_mM": [0.1, 1.0], "reductant_to_Au_ratio": [1.0, 10.0], "GO_mg_mL": [0.0, 0.5],
         "pH": [3.0, 11.0], "temperature_C": [20.0, 90.0], "time_min": [5.0, 120.0]}
DEFAULT_TIME_MIN = 30.0


@functools.lru_cache(maxsize=4096)
def _ext(d_key: int, s_key: int) -> np.ndarray:
    ext = mie.ensemble_extinction(WL, d_key / 2.0, s_key / 100.0, n_sizes=7)
    return ext / ext.max()


def unit_spectrum(d_nm: float, sigma_rel: float) -> np.ndarray:
    """Espectro de extinção normalizado (máx = 1), com cache em passos de 0,5 nm e 1 % de dispersão."""
    return _ext(int(round(np.clip(d_nm, 3, 150) * 2)), int(round(np.clip(sigma_rel, 0.02, 0.6) * 100)))


def target_spectrum() -> np.ndarray:
    return 0.8 * unit_spectrum(TARGET_D, TARGET_SIGMA)


def simulate(cond: dict, batch: str, reagent_lot: str = "RED-A", hardware: str = "hot_plate",
             rng: np.random.Generator | None = None, noiseless: bool = False) -> dict:
    """noiseless=True devolve o valor ESPERADO (sem variação síntese a síntese nem ruído de medida): é a "verdade"
    usada para calcular arrependimento nos benchmarks."""
    rng = rng or np.random.default_rng()
    co = BATCHES[batch]["C_O_ratio"]
    iod = REAGENT_LOTS[reagent_lot]["iodide_ppm"]
    T = cond["temperature_C"] + HARDWARE_OFFSET_C[hardware]
    sites = np.tanh(4 * cond["GO_mg_mL"]) * (2.6 - co)
    d = 6 + 45 * np.exp(-0.3 * cond["reductant_to_Au_ratio"]) * (1 + 0.6 * cond["HAuCl4_mM"]) \
        * (1 - 0.35 * sites) * (1 - 0.004 * (T - 20)) * (1 + 0.003 * iod)
    t = float(cond.get("time_min", DEFAULT_TIME_MIN))
    d *= 1 + 0.06 * np.log(max(t, 1.0) / DEFAULT_TIME_MIN)
    d = float(np.clip(d * (1.0 if noiseless else rng.lognormal(0, 0.04)), 3, 150))
    ph_opt = 6.0 + 1.5 * (co - 1.6)
    sigma = 0.07 + 0.05 * abs(cond["pH"] - ph_opt) / 4 + 0.001 * iod + 0.02 * (0.5 if noiseless else rng.random())
    yld = (1 - np.exp(-cond["reductant_to_Au_ratio"] / 2.5)) * np.exp(-((cond["pH"] - ph_opt) / 3.5) ** 2) \
        * (0.85 + 0.15 * sites) * (1 - np.exp(-t / 15.0))
    conc = cond["HAuCl4_mM"] / 0.5
    spec = 0.8 * conc * yld * unit_spectrum(d, sigma) + cond["GO_mg_mL"] * 0.15 * (450 / WL) ** 3
    if not noiseless:
        spec = spec + rng.normal(0, NOISE_SD, WL.size)
    desc = uvvis.lspr(WL, spec)
    J = uvvis.spectral_loss_J(WL, spec, WL, target_spectrum(), s=NOISE_SD * 5, grid=WL)
    return {"spectrum": spec, "size_mean_nm": d, "size_sd_nm": d * sigma, "size_cv": sigma, "LSPR_nm": desc["LSPR_nm"],
            "A_LSPR": desc["A_LSPR"], "spectral_loss_J": J, "yield_pct": 100 * float(np.clip(yld, 0, 1))}


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    base = {"HAuCl4_mM": 0.5, "reductant_to_Au_ratio": 4.0, "GO_mg_mL": 0.2, "pH": 6.5, "temperature_C": 60}
    for b in ("L1", "L3"):
        for lot in REAGENT_LOTS:
            r = simulate(base, b, lot, rng=rng)
            print(b, lot, {k: round(v, 2) for k, v in r.items() if k != "spectrum"})
