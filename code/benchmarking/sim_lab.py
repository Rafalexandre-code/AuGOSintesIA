#!/usr/bin/env python3
"""Laboratório SIMULADO no formato do modelo de dados (datasets/data-model/): cria as tabelas de lotes, impurezas
e caracterização do GO, e "executa" sínteses com code/benchmarking/simulator.py gravando o espectro bruto,
a linha em `spectra`, as medidas (UV-Vis via code/spectral/uvvis.py, TEM) e os desfechos. Tudo marcado SIMULADO.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simulator as sim  # noqa: E402

TARGET_SIZE_NM = 20.0


def _append(lab: str, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    path = os.path.join(lab, f"{table}.csv")
    new = pd.DataFrame(rows)
    if os.path.exists(path):
        new = pd.concat([pd.read_csv(path), new], ignore_index=True)
    new.to_csv(path, index=False)


def init_lab(lab: str, batches=("L1", "L2", "L3"), seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(lab, "raw_data"), exist_ok=True)
    for f in os.listdir(lab):
        if f.endswith(".csv"):
            os.remove(os.path.join(lab, f))
    lots = [{"lot_id": "LOT-HAuCl4-SIM", "entity_id": "HAuCl4", "chemical_name": "Gold(III) chloride trihydrate",
             "canonical_name": "hydrogen tetrachloroaurate(III)", "pubchem_cid": 28133, "supplier": "SIM",
             "lot_number": "SIM-AU", "purity": 99.9, "hydrate_form": "trihydrate", "notes": "SIMULADO"}]
    analyses = []
    for lot, imp in sim.REAGENT_LOTS.items():
        lots.append({"lot_id": lot, "entity_id": "trisodium_citrate", "chemical_name": "Sodium citrate dihydrate",
                     "canonical_name": "trisodium citrate", "pubchem_cid": 6224, "supplier": "SIM", "lot_number": lot,
                     "purity": 99.0, "hydrate_form": "dihydrate", "notes": "SIMULADO"})
        analyses.append({"analysis_id": f"RA-{lot}", "lot_id": lot, "analyte": "iodide", "method": "IC",
                         "value": round(imp["iodide_ppm"] * rng.lognormal(0, 0.05), 3), "uncertainty": 1.0,
                         "uncertainty_type": "sd", "n_replicates": 3, "unit": "ppm", "notes": "SIMULADO"})
    pd.DataFrame(lots).to_csv(os.path.join(lab, "reagent_lots.csv"), index=False)
    pd.DataFrame(analyses).to_csv(os.path.join(lab, "reagent_analyses.csv"), index=False)
    pd.DataFrame([{"go_batch_id": b, "source_type": "lab_synthesized", "synthesis_method": "modified_Hummers",
                   "notes": "SIMULADO"} for b in batches]).to_csv(os.path.join(lab, "go_batches.csv"), index=False)
    samples, meas = [], []
    for b in batches:
        sid = f"{b}-S01"
        samples.append({"go_sample_id": sid, "go_batch_id": b, "prep_type": "film_dropcast"})
        for qty, tech, sd in (("C_O_ratio", "XPS", 0.06), ("ID_IG", "Raman", 0.02)):
            for _ in range(3):
                meas.append({"measurement_id": f"M-GO-{len(meas) + 1:04d}", "go_sample_id": sid, "technique": tech,
                             "quantity": qty, "value": round(sim.BATCHES[b][qty] + rng.normal(0, sd), 4),
                             "uncertainty": sd, "uncertainty_type": "instrument", "n_replicates": 1, "unit": "a.u.",
                             "notes": "SIMULADO"})
    pd.DataFrame(samples).to_csv(os.path.join(lab, "go_samples.csv"), index=False)
    pd.DataFrame(meas).to_csv(os.path.join(lab, "go_characterization.csv"), index=False)
    sys.path.insert(0, os.path.join(HERE, "..", "go_navigator"))
    from batch_descriptors import aggregate_from_measurements
    aggregate_from_measurements(lab).to_csv(os.path.join(lab, "go_descriptors.csv"), index=False)
    np.savetxt(os.path.join(lab, "raw_data", "target_spectrum.csv"), np.c_[sim.WL, sim.target_spectrum()],
               delimiter=",", header="wavelength_nm,absorbance", comments="")


def run_syntheses(lab: str, syn: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Executa (simula) as sínteses de `syn` (formato aunp_syntheses) e grava todas as tabelas; devolve os desfechos."""
    syn = syn.copy()
    for c, v in (("gold_precursor_lot_id", "LOT-HAuCl4-SIM"), ("hardware", "hot_plate"), ("status", "done")):
        if c not in syn or syn[c].isna().all() or (syn[c].astype(str) == "").all():
            syn[c] = v
    if "reductant_lot_id" not in syn or (syn["reductant_lot_id"].astype(str).isin(["", "nan"])).any():
        syn["reductant_lot_id"] = [rng.choice(list(sim.REAGENT_LOTS)) for _ in range(len(syn))]
    n_sp = len(pd.read_csv(os.path.join(lab, "spectra.csv"))) if os.path.exists(os.path.join(lab, "spectra.csv")) else 0
    spectra, char, outc, res = [], [], [], []
    for _, s in syn.iterrows():
        cond = {k: float(s[k]) for k in sim.SPACE}
        r = sim.simulate(cond, s["go_batch_id"], s["reductant_lot_id"], s["hardware"], rng)
        n_sp += 1
        sp_id = f"UV-{n_sp:04d}"
        fname = f"raw_data/{sp_id}.csv"
        np.savetxt(os.path.join(lab, fname), np.c_[sim.WL, r["spectrum"]], delimiter=",",
                   header="wavelength_nm,absorbance", comments="")
        spectra.append({"spectrum_id": sp_id, "synthesis_id": s["synthesis_id"], "technique": "UV-Vis", "file": fname,
                        "dilution_factor": 1, "path_length_mm": 10, "time_after_prep_min": 30, "notes": "SIMULADO"})
        sid = s["synthesis_id"]
        for qty, unit, unc, tech in (("LSPR_nm", "nm", 0.5, "UV-Vis"), ("A_LSPR", "a.u.", sim.NOISE_SD, "UV-Vis"),
                                     ("spectral_loss_J", "a.u.", None, "UV-Vis"),
                                     ("size_mean_nm", "nm", r["size_sd_nm"] / np.sqrt(100), "TEM"),
                                     ("size_sd_nm", "nm", None, "TEM")):
            char.append({"measurement_id": f"M-{sid}-{qty}", "synthesis_id": sid, "technique": tech, "quantity": qty,
                         "spectrum_id": sp_id if tech == "UV-Vis" else "", "value": round(r[qty], 5),
                         "uncertainty": round(unc, 5) if unc is not None else "",
                         "uncertainty_type": "sem" if tech == "TEM" and unc else ("instrument" if unc else ""),
                         "n_replicates": 100 if tech == "TEM" else 1, "unit": unit, "notes": "SIMULADO"})
        outc += [{"synthesis_id": sid, "objective": "spectral_loss_J", "value": round(r["spectral_loss_J"], 5),
                  "direction": "minimize", "target_value": "", "notes": "SIMULADO"},
                 {"synthesis_id": sid, "objective": "size_mean_nm", "value": round(r["size_mean_nm"], 4),
                  "uncertainty": round(r["size_sd_nm"] / 10, 4), "direction": "target", "target_value": TARGET_SIZE_NM,
                  "notes": "SIMULADO"}]
        res.append({"synthesis_id": sid, "go_batch_id": s["go_batch_id"], **{k: r[k] for k in
                    ("spectral_loss_J", "size_mean_nm", "LSPR_nm", "yield_pct")}})
    _append(lab, "aunp_syntheses", syn.to_dict("records"))
    _append(lab, "spectra", spectra)
    _append(lab, "aunp_characterization", char)
    _append(lab, "outcomes", outc)
    return pd.DataFrame(res)
