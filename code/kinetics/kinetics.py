#!/usr/bin/env python3
"""Modelagem cinética reduzida com verificação de identificabilidade (§4.10, Objetivo 7) — módulo CONDICIONAL.

Modelo de Finke–Watzky (nucleação lenta + crescimento autocatalítico), o mínimo para formação de AuNP:
    A → B (k1, nucleação)        A + B → 2B (k2, crescimento)        A = Au(III), B = Au(0) em partículas
    solução fechada:  [A](t) = (k1/k2 + A0) / (1 + (k1/(k2·A0)) · exp((k1 + k2·A0)·t))
Observável: sinal ∝ B(t) (ex.: A400 ou A_LSPR resolvidos no tempo) ou A(t) (banda do Au(III)); com escala e offset.

Antes de qualquer interpretação mecanística, a proposta exige (e `check` executa):
  1. conservação (A + B = A0) e positividade da solução;
  2. recuperação de parâmetros em dados SINTÉTICOS gerados com os parâmetros ajustados e o ruído observado;
  3. resíduos sem estrutura (teste de sequências de Wald–Wolfowitz e autocorrelação de lag 1);
  4. identificabilidade por PERFIL DE VEROSSIMILHANÇA (Raue et al. 2009): para cada parâmetro, o perfil precisa
     cruzar o limiar χ²(1; 0,95)/2 dos dois lados — perfil plano de um lado = não identificável;
  5. regra de parada: se 2, 3 ou 4 falha, `interpretable = False` e o relatório diz por quê.

Uso:
    python code/kinetics/kinetics.py curva.csv [--observable product --time-unit s] [--out kin.json]
Entrada: duas colunas (tempo, sinal).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spectral"))
CHI2_95_1DF = 3.841


def fw_A(t: np.ndarray, k1: float, k2: float, A0: float = 1.0) -> np.ndarray:
    t = np.asarray(t, float)
    r = k1 / (k2 * A0)
    e = np.exp(np.clip((k1 + k2 * A0) * t, -700, 700))
    return (k1 / k2 + A0) / (1 + r * e)


def model(t, theta, observable: str = "product", A0: float = 1.0):
    """theta = (log10 k1, log10 k2, escala, offset)."""
    k1, k2, sc, off = 10 ** theta[0], 10 ** theta[1], theta[2], theta[3]
    A = fw_A(t, k1, k2, A0)
    return off + sc * ((A0 - A) if observable == "product" else A)


def _nll(theta, t, y, observable):
    r = y - model(t, theta, observable)
    s2 = max(np.mean(r ** 2), 1e-300)
    return 0.5 * len(y) * np.log(s2)            # sigma perfilado analiticamente


def fit(t, y, observable: str = "product", n_starts: int = 20, seed: int = 0) -> dict:
    from scipy.optimize import least_squares
    t, y = np.asarray(t, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    span = float(np.ptp(y)) or 1.0
    best = None
    T = float(t.max() - t.min()) or 1.0
    for _ in range(n_starts):
        p0 = [np.log10(1 / T) + rng.uniform(-3, 0), np.log10(10 / T) + rng.uniform(-1, 2),
              span * rng.uniform(0.8, 1.2), float(y.min() if observable == "product" else y.max() - span)]
        try:
            r = least_squares(lambda p: model(t, p, observable) - y, p0,
                              bounds=([-12, -12, 0, -np.inf], [6, 6, np.inf, np.inf]))
        except ValueError:
            continue
        if best is None or r.cost < best.cost:
            best = r
    theta = best.x
    return {"theta": theta, "k1": 10 ** theta[0], "k2": 10 ** theta[1], "scale": theta[2], "offset": theta[3],
            "nll": _nll(theta, t, y, observable), "rmse": float(np.sqrt(np.mean(best.fun ** 2)))}


def profile(t, y, f: dict, observable: str = "product", which: int = 0, span_dec: float = 3.0, n: int = 25) -> dict:
    """Perfil de verossimilhança de log10 k1 (which=0) ou log10 k2 (which=1): reotimiza os demais em cada ponto."""
    from scipy.optimize import least_squares
    grid = f["theta"][which] + np.linspace(-span_dec, span_dec, n)
    prof = []
    for g in grid:
        free = [i for i in range(4) if i != which]

        def res(p):
            th = np.array(f["theta"], float)
            th[free] = p
            th[which] = g
            return model(t, th, observable) - y
        r = least_squares(res, np.array(f["theta"])[free],
                          bounds=([-12, 0, -np.inf] if which == 1 else [-12, 0, -np.inf],
                                  [6, np.inf, np.inf] if which == 1 else [6, np.inf, np.inf]))
        th = np.array(f["theta"], float)
        th[free], th[which] = r.x, g
        prof.append(_nll(th, t, y, observable) - f["nll"])
    prof = np.array(prof)
    thr = CHI2_95_1DF / 2
    left, right = prof[: n // 2], prof[n // 2 + 1:]
    ok_l, ok_r = bool(np.any(left > thr)), bool(np.any(right > thr))
    inside = grid[prof <= thr]
    return {"grid_log10": grid.tolist(), "delta_nll": prof.tolist(), "identifiable": ok_l and ok_r,
            "ci95_log10": [float(inside.min()), float(inside.max())] if len(inside) else [float("nan")] * 2,
            "bounded_below": ok_l, "bounded_above": ok_r}


def residual_checks(r: np.ndarray) -> dict:
    from scipy.stats import norm
    s = np.sign(r - np.median(r))
    s = s[s != 0]
    n1, n2 = np.sum(s > 0), np.sum(s < 0)
    runs = 1 + int(np.sum(s[1:] != s[:-1]))
    mu = 2 * n1 * n2 / (n1 + n2) + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
    p_runs = float(2 * norm.sf(abs(runs - mu) / np.sqrt(var))) if var > 0 else 1.0
    ac1 = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if len(r) > 3 else 0.0
    return {"runs_p": p_runs, "lag1_autocorr": ac1, "structured": bool(p_runs < 0.05 or abs(ac1) > 0.5)}


def check(t, y, observable: str = "product", n_recovery: int = 20, seed: int = 0) -> dict:
    t, y = np.asarray(t, float), np.asarray(y, float)
    f = fit(t, y, observable, seed=seed)
    from scipy.integrate import solve_ivp
    k1, k2 = f["k1"], f["k2"]
    sol = solve_ivp(lambda _, u: [-k1 * u[0] - k2 * u[0] * u[1], k1 * u[0] + k2 * u[0] * u[1]],
                    (0.0, float(t.max())), [1.0, 0.0], t_eval=np.unique(np.clip(t, 0, None)), method="LSODA",
                    rtol=1e-8, atol=1e-10)
    A_ode, B_ode = sol.y
    conservation = float(np.max(np.abs(A_ode + B_ode - 1.0)))      # A + B = A0 na integração numérica
    closed_vs_ode = float(np.max(np.abs(A_ode - fw_A(sol.t, k1, k2))))
    positivity = bool(np.all(A_ode >= -1e-9) and np.all(B_ode >= -1e-9))
    rng = np.random.default_rng(seed)
    sig = f["rmse"]
    rec = []
    for _ in range(n_recovery):
        ys = model(t, f["theta"], observable) + rng.normal(0, sig, len(t))
        g = fit(t, ys, observable, n_starts=8, seed=int(rng.integers(1e9)))
        rec.append(g["theta"][:2])
    rec = np.array(rec)
    bias = np.median(rec, axis=0) - f["theta"][:2]
    spread = np.percentile(rec, 90, axis=0) - np.percentile(rec, 10, axis=0)
    recovery_ok = bool(np.all(np.abs(bias) < 0.3) and np.all(spread < 1.0))       # em décadas (log10)
    prof = {name: profile(t, y, f, observable, i) for i, name in enumerate(("k1", "k2"))}
    resid = y - model(t, f["theta"], observable)
    rc = residual_checks(resid)
    reasons = []
    if not recovery_ok:
        reasons.append("parâmetros não se recuperam em dados sintéticos (viés ou espalhamento > limiar)")
    for k, v in prof.items():
        if not v["identifiable"]:
            reasons.append(f"{k} não identificável (perfil de verossimilhança plano)")
    if rc["structured"]:
        reasons.append("resíduos estruturados (o modelo reduzido não descreve a curva)")
    return {"fit": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in f.items()},
            "conservation_max_error": conservation, "closed_form_vs_ode": closed_vs_ode, "positivity": positivity,
            "recovery": {"bias_log10": bias.tolist(), "p10_p90_width_log10": spread.tolist(), "ok": recovery_ok},
            "profiles": prof, "residuals": rc, "interpretable": not reasons and positivity,
            "stop_reasons": reasons}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--observable", choices=["product", "reactant"], default="product")
    ap.add_argument("--time-unit", choices=["s", "min"], default="s")
    ap.add_argument("--out")
    a = ap.parse_args()
    from uvvis import read_spectrum
    t, y = read_spectrum(a.file)
    r = check(t * (60 if a.time_unit == "min" else 1), y, a.observable)
    f = r["fit"]
    print(f"k1 = {f['k1']:.3g} s⁻¹, k2 = {f['k2']:.3g} (A0=1)⁻¹ s⁻¹, RMSE {f['rmse']:.3g}")
    for k, v in r["profiles"].items():
        print(f"  {k}: identificável = {v['identifiable']}, IC95 log10 = {v['ci95_log10']}")
    print("interpretável:", r["interpretable"], "|", "; ".join(r["stop_reasons"]) or "todas as verificações passaram")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1, ensure_ascii=False, default=float)


if __name__ == "__main__":
    main()
