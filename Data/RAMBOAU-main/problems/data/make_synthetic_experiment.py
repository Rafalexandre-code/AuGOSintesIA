"""Generate a SYNTHETIC stand-in for the (unpublished) ZnO campaign data read by problems/exp.py.

The real spreadsheets (problems/data/MT-KBH-004/XRD+synthsis_data_b<N>.xlsx) are not public. This script
writes files with the same schema so that `main_exp.py` / `Experiment4D` can be exercised end to end, and so
the format can be copied for your own campaign (e.g. GO-AuNP: replace the columns by your recipe variables
and measured objectives).

THE NUMBERS ARE FAKE: smooth made-up response surfaces + heteroscedastic replicate noise.

Usage (from the RAMBOAU root):
    python problems/data/make_synthetic_experiment.py            # 34 conditions x 3 replicates
    RAMBOAU_EXP_DATA=problems/data/SYNTHETIC-EXAMPLE python main_exp.py
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

# bounds used by Experiment4D:  C_NaOH/C_ZnCl, C_ZnCl, Q_AC, Q_Air
LOWER = np.array([0.5, 0.1, 4.0, 1.0])
UPPER = np.array([3.5, 1.0, 10.0, 2.5])


def responses(x, rng):
    """Fake (peak ratio, aspect ratio) with replicate noise that grows with the flow rates."""
    u = (x - LOWER) / (UPPER - LOWER)
    peak = 1.5 + np.sin(3 * u[0]) * np.cos(2 * u[1]) + 0.5 * u[2]
    aspect = 2.0 + 3.0 * np.exp(-8 * (u[0] - 0.6) ** 2) * (0.5 + u[3])
    noise_sd = 0.05 + 0.25 * u[2] * u[3]          # heteroscedastic: risky region at high Q_AC & Q_Air
    return peak + noise_sd * rng.normal(), aspect + 2 * noise_sd * rng.normal()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-conditions", type=int, default=34,
                    help="unique recipes (main_exp.py defaults need 34: n_iter*batch + n_init = len + batch)")
    ap.add_argument("--replicates", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent / "SYNTHETIC-EXAMPLE"))
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    rows = []
    X = LOWER + rng.random((args.n_conditions, 4)) * (UPPER - LOWER)
    for i, x in enumerate(X, start=1):
        for _ in range(args.replicates):
            peak, aspect = responses(x, rng)
            c_zn = x[1]
            c_naoh = x[0] * c_zn
            rows.append({
                "id": i, "C_ZnCl": c_zn, "C_NaOH/C_ZnCl": x[0], "C_NaOH": c_naoh,
                "Aspect Ratio": aspect, "Peak Ratio": peak, "Q_AC": x[2], "Q_AIR": x[3],
                "N_ZnO": min(c_zn, 0.5 * c_naoh) * x[2],   # recomputed by Experiment4D anyway
                "note": "SYNTHETIC - not measured data",
            })

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "XRD+synthsis_data_b1.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    print(f"wrote {path} ({args.n_conditions} conditions x {args.replicates} replicates, SYNTHETIC)")


if __name__ == "__main__":
    main()
