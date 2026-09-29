---
title: SuperconGPT
---

# SuperconGPT

Three-tab superconductor discovery platform: (1) Inverse design — generate crystal structures for a target Tc using AtomGPT, optionally relax with ALIGNN-FF and predict properties, (2) Database search — query SuperconDB (1058 3D + 161 2D materials + hydrides) by elements with α²F(ω) Eliashberg function plots, (3) Tc predictor — predict superconducting Tc and 7 other properties from any POSCAR using ALIGNN.

[:material-open-in-new: Open App](https://atomgpt.org/supercon){ .md-button .md-button--primary }

---

## Overview

SuperconGPT combines generative AI (AtomGPT) for inverse design of superconductors with a curated DFT-based BCS superconductor database and ALIGNN property prediction. The database includes Tc, electron-phonon coupling constant λ, logarithmic phonon frequency ω_log, α²F(ω) Eliashberg functions, and stability information for ambient-pressure 3D and 2D superconductors.

!!! info "Data Source"
    **SuperconDB 3D** (1058 entries) + **SuperconDB 2D** (161 entries) + hydrides from [`jarvis.db.figshare`](https://atomgptlab.github.io/jarvis/databases/).
    **AtomGPT** (SuperconGPT LoRA adapter) for inverse crystal generation.
    **ALIGNN** (`jv_supercon_tc_alignn`) for Tc prediction.

## Endpoints

### `POST /supercon/generate` — Inverse design: generate structure for target Tc

Generate a crystal structure for a given chemical formula and target superconducting Tc using AtomGPT. Optionally relax with ALIGNN-FF and run ALIGNN property predictions.

```bash
curl -X POST "https://atomgpt.org/supercon/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "MgB2",
    "tc": 39.0,
    "max_new_tokens": 512,
    "temperature": 0.0,
    "top_k": 50,
    "top_p": 1.0,
    "do_sample": false,
    "relax": false,
    "run_alignn": true
  }'
```


| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | required | Chemical formula (e.g. `"MgB2"`, `"LaH10"`, `"H3S"`) |
| `tc` | float | required | Target superconducting Tc in Kelvin |
| `max_new_tokens` | int | 512 | Max generation tokens (64–2048) |
| `temperature` | float | 0.0 | Sampling temperature (0 = deterministic) |
| `top_k` | int | 50 | Top-K sampling (1–500) |
| `top_p` | float | 1.0 | Nucleus sampling threshold |
| `do_sample` | bool | false | Enable stochastic sampling |
| `relax` | bool | false | Relax generated structure with ALIGNN-FF |
| `run_alignn` | bool | false | Run ALIGNN property predictions on result |

**Response** includes `poscar`, `formula_generated`, `spacegroup`, `num_atoms`, `density`, `lattice`, `generation_time_s`, `xyz` (for 3D viewer), and optionally `alignn_predictions` (formation_energy, bandgap, bulk_modulus, shear_modulus, supercon_tc_predicted).

---

### `GET /supercon/generate` — Lightweight inverse design (GET)

Same as POST but via query parameters:

```bash
curl "https://atomgpt.org/supercon/generate?formula=MgB2&tc=39&relax=false&max_new_tokens=512" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

---

### `GET /supercon/search` — Search SuperconDB by elements

Search the DFT-based BCS superconductor database by element combination. Returns entries containing ALL specified elements, sorted by Tc descending.

```bash
curl "https://atomgpt.org/supercon/search?elements=Mg,B" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

```bash
curl "https://atomgpt.org/supercon/search?elements=Nb" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

```bash
curl "https://atomgpt.org/supercon/search?elements=La,H" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

| Param | Description |
|-------|-------------|
| `elements` | Comma-separated elements (e.g. `"Mg,B"`, `"Nb"`, `"La,H"`) |

**Response** includes `count`, `elements`, and `entries` array with: `jid`, `formula`, `tc` (K), `lambda` (electron-phonon coupling), `wlog` (K), `pressure`, `stability`, `a2F_x`, `a2F_y` (Eliashberg function data for plotting).

---

### `POST /supercon/predict_tc` — Predict Tc from POSCAR

Predict superconducting Tc and 7 other properties from any crystal structure using ALIGNN pre-trained models. Max 50 atoms.

```bash
curl -X POST "https://atomgpt.org/supercon/predict_tc" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "MgB2\n1.0\n1.537 -2.662 0.0\n1.537 2.662 0.0\n0.0 0.0 3.515\nMg B\n1 2\nCartesian\n0.0 0.0 0.0\n1.537 -0.887 1.757\n1.537 0.887 1.757"
  }'
```

**Response** includes `formula`, `num_atoms`, `spacegroup`, and `properties`:

| Property | Unit | Description |
|----------|------|-------------|
| `supercon_tc` | K | Predicted superconducting Tc |
| `formation_energy` | eV/atom | Formation energy |
| `total_energy` | eV/atom | Total energy |
| `bandgap_optb88` | eV | Band gap (OptB88vdW) |
| `bandgap_mbj` | eV | Band gap (mBJ) |
| `bulk_modulus` | GPa | Bulk modulus (Voigt) |
| `shear_modulus` | GPa | Shear modulus (Voigt) |
| `piezoelectric` | — | Max piezoelectric constant |

---

## Python Examples

=== "Inverse design"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/supercon/generate",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "formula": "MgB2",
            "tc": 39.0,
            "relax": True,
            "run_alignn": True,
        },
    )
    data = response.json()
    if data["success"]:
        print(f"Generated: {data['formula_generated']} ({data['spacegroup']})")
        print(f"Atoms: {data['num_atoms']}, Time: {data['generation_time_s']}s")
        if "alignn_predictions" in data:
            ap = data["alignn_predictions"]
            print(f"Predicted Tc: {ap.get('supercon_tc_predicted', '?')} K")
        print(f"POSCAR:\n{data['poscar'][:300]}")
    ```

=== "Database search"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/supercon/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
        },
        params={"elements": "Nb"},
    )
    data = response.json()
    print(f"Found {data['count']} Nb superconductors")
    for e in data["entries"][:10]:
        print(f"  {e['jid']:12s} {e['formula']:10s} Tc={e['tc']} K  λ={e['lambda']}")
    ```

=== "Predict Tc"

    ```python
    import requests

    MGB2_POSCAR = """MgB2
    1.0
    1.537 -2.662 0.0
    1.537 2.662 0.0
    0.0 0.0 3.515
    Mg B
    1 2
    Cartesian
    0.0 0.0 0.0
    1.537 -0.887 1.757
    1.537 0.887 1.757"""

    response = requests.post(
        "https://atomgpt.org/supercon/predict_tc",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": MGB2_POSCAR},
    )
    data = response.json()
    if data["success"]:
        p = data["properties"]
        print(f"{data['formula']} ({data['spacegroup']})")
        print(f"  Predicted Tc: {p['supercon_tc']:.2f} K")
        print(f"  Formation energy: {p['formation_energy']:.3f} eV/atom")
        print(f"  Band gap: {p['bandgap_optb88']:.3f} eV")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Inverse design
response = agent.query_sync("Generate a crystal structure for MgB2 with Tc=39K using SuperconGPT")
print(response)

# Database search
response = agent.query_sync("Search for Nb-based superconductors in SuperconDB")
print(response)

# Predict Tc
response = agent.query_sync("Predict the superconducting Tc for JVASP-1002")
print(response)
```

## References

- K. Choudhary, K. Garrity, npj Comp. Mat. 8, 244 (2022) — Designing High-Tc Superconductors with BCS-Inspired Screening [:material-link: DOI](https://doi.org/10.1038/s41524-022-00933-1)
- K. Choudhary, J. Phys. Chem. Lett. 15, 6909 (2024) — AtomGPT [:material-link: DOI](https://doi.org/10.1021/acs.jpclett.4c01126)
- D. Wines, T. Xie, K. Choudhary, J. Phys. Chem. Lett. 14, 6630 (2023) — Inverse Design of Superconductors [:material-link: DOI](https://doi.org/10.1021/acs.jpclett.3c01260)
- D. Wines, K. Choudhary et al., Nano Lett. 23, 969 (2023) — 2D Superconductors [:material-link: DOI](https://doi.org/10.1021/acs.nanolett.2c04420)
- D. Wines, K. Choudhary, Materials Futures 3, 025602 (2024) — High-Pressure Hydride Superconductors [:material-link: DOI](https://doi.org/10.1088/2752-5724/ad4a94)
- Charles Rhys Campbell, Aldo H. Romero, and Kamal Choudhary, AtomBench: A Benchmarking Framework for Generative Crystal Reconstruction Models in Conventional Superconductors [:material-link: DOI](https://arxiv.org/pdf/2510.16165)
- [atomgptlab/atomgpt](https://github.com/atomgptlab/atomgpt)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
- [atomgptlab/atombench_inverse](https://github.com/atomgptlab/atombench_inverse)
