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
# custos e massas ILUSTRATIVOS do laboratório simulado (tabela resources; não são preços reais)
SIM_COSTS = {"HAuCl4_g": 450.0, "citrate_g": 0.5, "GO_g": 80.0, "water_g": 0.01, "kWh": 0.9, "UV-Vis_h": 40.0,
             "TEM_h": 300.0, "TEM_grid": 15.0}
M_HAUCL4_3H2O, M_CITRATE_2H2O = 393.83, 294.10


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
    if "reductant_lot_id" not in syn:
        syn["reductant_lot_id"] = ""
    missing = syn["reductant_lot_id"].astype(str).isin(["", "nan"])   # só preenche o que falta
    syn.loc[missing, "reductant_lot_id"] = [rng.choice(list(sim.REAGENT_LOTS)) for _ in range(int(missing.sum()))]
    n_sp = len(pd.read_csv(os.path.join(lab, "spectra.csv"))) if os.path.exists(os.path.join(lab, "spectra.csv")) else 0
    spectra, char, outc, res, resources = [], [], [], [], []
    for _, s in syn.iterrows():
        cond = {k: float(s[k]) for k in sim.SPACE if k in s and str(s[k]) not in ("", "nan")}
        r = sim.simulate(cond, s["go_batch_id"], s["reductant_lot_id"], s["hardware"], rng)
        n_sp += 1
        sp_id = f"UV-{n_sp:04d}"
        fname = f"raw_data/{sp_id}.csv"
        np.savetxt(os.path.join(lab, fname), np.c_[sim.WL, r["spectrum"]], delimiter=",",
                   header="wavelength_nm,absorbance", comments="")
        spectra.append({"spectrum_id": sp_id, "synthesis_id": s["synthesis_id"], "technique": "UV-Vis", "file": fname,
                        "dilution_factor": 1, "path_length_mm": 10, "time_after_prep_min": 30, "notes": "SIMULADO"})
        # leitura em duplicata da mesma alíquota (SOP-UVVIS-01): só o ruído de medida muda
        n_sp += 1
        dup_id, dup_f = f"UV-{n_sp:04d}", f"raw_data/UV-{n_sp:04d}.csv"
        np.savetxt(os.path.join(lab, dup_f), np.c_[sim.WL, r["spectrum"] + rng.normal(0, sim.NOISE_SD, sim.WL.size)],
                   delimiter=",", header="wavelength_nm,absorbance", comments="")
        spectra.append({"spectrum_id": dup_id, "synthesis_id": s["synthesis_id"], "technique": "UV-Vis", "file": dup_f,
                        "dilution_factor": 1, "path_length_mm": 10, "time_after_prep_min": 32,
                        "notes": "SIMULADO; leitura em duplicata"})
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
                  "direction": "minimize", "target_value": "", "derived_from": f"M-{sid}-spectral_loss_J",
                  "notes": "SIMULADO"},
                 {"synthesis_id": sid, "objective": "size_mean_nm", "value": round(r["size_mean_nm"], 4),
                  "uncertainty": round(r["size_sd_nm"] / 10, 4), "direction": "target", "target_value": TARGET_SIZE_NM,
                  "derived_from": f"M-{sid}-size_mean_nm", "notes": "SIMULADO"},
                 # restrições pré-registradas (config/preregistration.yaml): monodispersidade e produto mensurável
                 {"synthesis_id": sid, "objective": "size_cv", "value": round(r["size_cv"], 5), "direction": "constraint",
                  "target_value": 0.25, "derived_from": f"M-{sid}-size_mean_nm|M-{sid}-size_sd_nm", "notes": "SIMULADO"},
                 {"synthesis_id": sid, "objective": "A_LSPR", "value": round(r["A_LSPR"], 5), "direction": "constraint",
                  "target_value": 0.10, "derived_from": f"M-{sid}-A_LSPR", "notes": "SIMULADO"}]
        resources += sim_resources(sid, cond, s["go_batch_id"])
        res.append({"synthesis_id": sid, "go_batch_id": s["go_batch_id"], **{k: r[k] for k in
                    ("spectral_loss_J", "size_mean_nm", "LSPR_nm", "yield_pct")}})
    _append(lab, "aunp_syntheses", syn.to_dict("records"))
    _append(lab, "spectra", spectra)
    _append(lab, "aunp_characterization", char)
    _append(lab, "outcomes", outc)
    _append(lab, "resources", resources)
    return pd.DataFrame(res)


def sim_resources(sid: str, cond: dict, batch: str, volume_mL: float = 10.0) -> list[dict]:
    """Insumos, energia, tempo de instrumento e resíduo de uma síntese SIMULADA (fronteira: síntese + caracterização)."""
    v_l = volume_mL / 1000.0
    au_g = cond["HAuCl4_mM"] / 1000 * v_l * M_HAUCL4_3H2O
    red_g = cond["reductant_to_Au_ratio"] * cond["HAuCl4_mM"] / 1000 * v_l * M_CITRATE_2H2O
    go_g = cond.get("GO_mg_mL", 0.0) * v_l
    hours = cond.get("time_min", sim.DEFAULT_TIME_MIN) / 60.0
    kwh = 0.4 * hours * (1.0 if cond.get("temperature_C", 25) > 30 else 0.1)
    items = [("synthesis", "", "reagent", "HAuCl4·3H2O", au_g, "g", au_g, au_g * SIM_COSTS["HAuCl4_g"]),
             ("synthesis", "", "reagent", "citrato de sódio", red_g, "g", red_g, red_g * SIM_COSTS["citrate_g"]),
             ("synthesis", "", "reagent", "GO", go_g, "g", go_g, go_g * SIM_COSTS["GO_g"]),
             ("synthesis", "", "solvent", "água ultrapura", volume_mL, "mL", volume_mL, volume_mL * SIM_COSTS["water_g"]),
             ("synthesis", "", "energy", "aquecimento/agitação", kwh, "kWh", None, kwh * SIM_COSTS["kWh"]),
             ("synthesis", "", "waste", "resíduo aquoso com Au", volume_mL, "g", volume_mL, 0.0),
             ("characterization", "UV-Vis", "instrument_time", "espectrofotômetro (2 leituras)", 0.1, "h", None,
              0.1 * SIM_COSTS["UV-Vis_h"]),
             ("characterization", "TEM", "instrument_time", "TEM (10 campos)", 0.5, "h", None, 0.5 * SIM_COSTS["TEM_h"]),
             ("characterization", "TEM", "consumable", "grade de Cu/C", 1, "unidade", 0.05, SIM_COSTS["TEM_grid"])]
    return [{"resource_id": f"RES-{sid}-{k:02d}", "synthesis_id": sid, "go_batch_id": batch, "flow": f, "technique": t,
             "category": c, "item": it, "amount": round(am, 6), "unit": u, "mass_g": "" if m is None else round(m, 6),
             "cost": round(cost, 4), "currency": "BRL", "notes": "SIMULADO"}
            for k, (f, t, c, it, am, u, m, cost) in enumerate(items, 1)]
