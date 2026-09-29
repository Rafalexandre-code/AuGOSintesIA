---
title: Catalysis
---

# Catalysis

Predict adsorption energy of a molecule on a substrate surface using ALIGNN force-field. Provide the clean substrate POSCAR and the substrate+adsorbate POSCAR, specify which atoms are the adsorbate (1-indexed), and the app computes E_ads = E_cat − E_sub + μ(adsorbate). Chemical potentials are from JARVIS DFT elemental reference energies. Supports default and wt01 ALIGNN-FF models.

[:material-open-in-new: Open App](https://atomgpt.org/catalysis){ .md-button .md-button--primary }

---

## Overview

The Catalysis app computes adsorption energies without running full DFT. It uses ALIGNN-FF (`AlignnAtomwiseCalculator`) to evaluate the total energy of both the clean substrate and the substrate+adsorbate system, then combines them with JARVIS elemental chemical potentials:

**E_ads = E_catalyst − E_substrate + μ(adsorbate atoms)**

where μ is the sum of per-atom elemental reference energies from `jarvis.analysis.thermodynamics.energetics.get_optb88vdw_energy()`. Negative E_ads indicates exothermic (favorable) adsorption.

!!! info "Data Source"
    **ALIGNN-FF** (`default_path` or `wt01_path`) for energy calculations.
    **JARVIS-DFT** elemental reference chemical potentials.

## Endpoints

### `POST /catalysis/predict` — Compute adsorption energy

Takes two POSCAR structures (substrate and catalyst) plus adsorbate atom indices. Computes energies with ALIGNN-FF and returns the adsorption energy breakdown.

```bash
curl -X POST "https://atomgpt.org/catalysis/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "substrate": "Substrate\n1.0\n5.882 0.0 0.0\n2.941 5.094 0.0\n0.0 0.0 22.203\nAg Au\n12 4\ndirect\n0.0 0.0 0.338\n0.5 0.0 0.338\n0.0 0.5 0.338\n0.5 0.5 0.338\n0.167 0.167 0.446\n0.667 0.167 0.446\n0.167 0.667 0.446\n0.667 0.667 0.446\n-0.167 0.333 0.554\n0.333 0.333 0.554\n-0.167 0.833 0.554\n0.333 0.833 0.554\n0.0 0.0 0.662\n0.5 0.0 0.662\n0.0 0.5 0.662\n0.5 0.5 0.662",
    "catalyst": "Catalyst,adsorbate_indices:[17]\n1.0\n5.882 0.0 0.0\n2.941 5.094 0.0\n0.0 0.0 22.203\nAg Au O\n12 4 1\ndirect\n0.0 0.0 0.338\n0.5 0.0 0.338\n0.0 0.5 0.338\n0.5 0.5 0.338\n0.167 0.167 0.446\n0.667 0.167 0.446\n0.167 0.667 0.446\n0.667 0.667 0.446\n-0.167 0.333 0.554\n0.333 0.333 0.554\n-0.167 0.833 0.554\n0.333 0.833 0.554\n0.0 0.0 0.662\n0.5 0.0 0.662\n0.0 0.5 0.662\n0.5 0.5 0.662\n0.0 0.0 0.743",
    "adsorbate_indices": [17],
    "model": "default"
  }'
```

Multi-atom adsorbate (CO on Cu):

```bash
curl -X POST "https://atomgpt.org/catalysis/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "substrate": "Cu\n1.0\n3.615 0.0 0.0\n0.0 3.615 0.0\n0.0 0.0 3.615\nCu\n4\ndirect\n0.0 0.0 0.0\n0.0 0.5 0.5\n0.5 0.0 0.5\n0.5 0.5 0.0",
    "catalyst": "Cu,adsorbate_indices:[5,6]\n1.0\n3.615 0.0 0.0\n0.0 3.615 0.0\n0.0 0.0 3.615\nCu C O\n4 1 1\ndirect\n0.0 0.0 0.0\n0.0 0.5 0.5\n0.5 0.0 0.5\n0.5 0.5 0.0\n0.0 0.0 0.2\n0.0 0.0 0.35",
    "adsorbate_indices": [5, 6],
    "model": "default"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `substrate` | string | required | POSCAR of clean substrate (no adsorbate) |
| `catalyst` | string | required | POSCAR of substrate + adsorbate |
| `adsorbate_indices` | list[int] | required | 1-indexed atom positions of adsorbate in catalyst POSCAR |
| `model` | string | `"default"` | ALIGNN-FF model: `"default"` or `"wt01"` |

!!! tip "Auto-detection"
    The web UI auto-detects adsorbate indices from the POSCAR comment line format `adsorbate_indices:[17]`.

**Response:**

| Field | Description |
|-------|-------------|
| `adsorption_energy` | E_ads (eV) — negative = exothermic |
| `substrate_energy` | E_substrate from ALIGNN-FF (eV) |
| `catalyst_energy` | E_catalyst from ALIGNN-FF (eV) |
| `chemical_potential` | Sum of elemental μ for adsorbate atoms (eV) |
| `chemical_potential_details` | Per-element breakdown |
| `formula_substrate` | Reduced formula of substrate |
| `formula_catalyst` | Reduced formula of catalyst |
| `adsorbate_elements` | List of adsorbate element symbols |
| `result_text` | Human-readable summary |

---

## Python Examples

=== "O on AgAu surface"

    ```python
    import requests

    SUBSTRATE = """Substrate
    1.0
    5.882 0.0 0.0
    2.941 5.094 0.0
    0.0 0.0 22.203
    Ag Au
    12 4
    direct
    0.0 0.0 0.338
    0.5 0.0 0.338
    0.0 0.5 0.338
    0.5 0.5 0.338
    0.167 0.167 0.446
    0.667 0.167 0.446
    0.167 0.667 0.446
    0.667 0.667 0.446
    -0.167 0.333 0.554
    0.333 0.333 0.554
    -0.167 0.833 0.554
    0.333 0.833 0.554
    0.0 0.0 0.662
    0.5 0.0 0.662
    0.0 0.5 0.662
    0.5 0.5 0.662"""

    CATALYST = """Catalyst,adsorbate_indices:[17]
    1.0
    5.882 0.0 0.0
    2.941 5.094 0.0
    0.0 0.0 22.203
    Ag Au O
    12 4 1
    direct
    0.0 0.0 0.338
    0.5 0.0 0.338
    0.0 0.5 0.338
    0.5 0.5 0.338
    0.167 0.167 0.446
    0.667 0.167 0.446
    0.167 0.667 0.446
    0.667 0.667 0.446
    -0.167 0.333 0.554
    0.333 0.333 0.554
    -0.167 0.833 0.554
    0.333 0.833 0.554
    0.0 0.0 0.662
    0.5 0.0 0.662
    0.0 0.5 0.662
    0.5 0.5 0.662
    0.0 0.0 0.743"""

    response = requests.post(
        "https://atomgpt.org/catalysis/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "substrate": SUBSTRATE,
            "catalyst": CATALYST,
            "adsorbate_indices": [17],
            "model": "default",
        },
    )
    data = response.json()
    if data["success"]:
        sign = "exothermic" if data["adsorption_energy"] < 0 else "endothermic"
        print(f"E_ads = {data['adsorption_energy']} eV ({sign})")
        print(f"  E_sub  = {data['substrate_energy']} eV")
        print(f"  E_cat  = {data['catalyst_energy']} eV")
        print(f"  μ(ads) = {data['chemical_potential']} eV")
        print(f"  Adsorbate: {data['adsorbate_elements']}")
    ```

=== "Compare adsorbates"

    ```python
    import requests

    PT_SUB = open("Pt_substrate.vasp").read()

    for ads_file, indices in [("Pt_H.vasp", [5]), ("Pt_O.vasp", [5]), ("Pt_CO.vasp", [5, 6])]:
        cat = open(ads_file).read()
        response = requests.post(
            "https://atomgpt.org/catalysis/predict",
            headers={
                "Authorization": "Bearer sk-XYZ",
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "substrate": PT_SUB,
                "catalyst": cat,
                "adsorbate_indices": indices,
            },
        )
        data = response.json()
        if data["success"]:
            ads = "+".join(data["adsorbate_elements"])
            print(f"Pt + {ads}: E_ads = {data['adsorption_energy']:.3f} eV")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Predict adsorption
response = agent.query_sync("Predict the adsorption energy of O on AgAu surface using ALIGNN-FF")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- J. Catal. 442, 116171 (2025) — CatalysisMat [:material-link: DOI](https://doi.org/10.1016/j.jcat.2025.116171)
- K. Choudhary, Digital Discovery 2(2), 346 (2023) — ALIGNN-FF [:material-link: DOI](https://doi.org/10.1039/D2DD00096B)
- [atomgptlab/catalysismat](https://github.com/atomgptlab/catalysismat)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
