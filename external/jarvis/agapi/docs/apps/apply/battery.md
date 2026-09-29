---
title: Battery Explorer
---

# Battery Explorer

Predict battery cathode voltage profiles and theoretical capacity using ALIGNN force-field. Sequentially removes intercalating ions from a supercell, computes energy at each step with ALIGNN-FF, and builds the voltage vs. ion-fraction curve. Supports 6 ion types (Li, Na, K, Mg, Ca, Zn) and 2 ALIGNN-FF models (default, wt01).

[:material-open-in-new: Open App](https://atomgpt.org/battery){ .md-button .md-button--primary }

---

## Overview

The Battery Explorer takes a cathode POSCAR structure, creates a supercell (enforced ~8 Å c-axis), identifies all intercalating ion sites, then sequentially removes ions one at a time. At each step, the total energy is computed with ALIGNN-FF (`AlignnAtomwiseCalculator`). The voltage at each step is:

**V = E(n+1) − E(n) + μ_element**

where μ_element is the per-atom energy of the elemental reference (e.g., BCC Li). Theoretical gravimetric (mAh/g) and volumetric (mAh/cm³) capacities are computed from the composition and Faraday's constant.

!!! info "Data Source"
    **ALIGNN-FF** (`default_path` or `wt01_path`) for energy calculations.
    **JARVIS-DFT** elemental reference energies from `jarvis.analysis.thermodynamics.energetics.get_optb88vdw_energy()`.

## Endpoints

### `POST /battery/predict` — Voltage profile + capacity

Predict the full voltage profile and theoretical capacity for a cathode material. Takes a POSCAR structure, intercalating ion, and model selection.

```bash
curl -X POST "https://atomgpt.org/battery/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "LiO2Co\n1.0\n2.719 -0.003 4.091\n1.234 2.423 4.091\n-0.004 -0.003 4.913\nLi Co O\n1 1 2\nCartesian\n1.974 1.209 6.548\n0.0 0.0 0.0\n1.027 0.629 3.405\n2.922 1.789 9.690",
    "element": "Li",
    "model": "default"
  }'
```

Na-ion battery example:

```bash
curl -X POST "https://atomgpt.org/battery/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "NaCoO2\n1.0\n2.89 0.0 0.0\n-1.445 2.502 0.0\n0.0 0.0 10.83\nNa Co O\n1 1 2\nDirect\n0.0 0.0 0.25\n0.0 0.0 0.0\n0.0 0.0 0.117\n0.0 0.0 0.883",
    "element": "Na",
    "model": "default"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | VASP POSCAR of cathode structure (must contain the intercalating ion) |
| `element` | string | `"Li"` | Intercalating ion: `"Li"`, `"Na"`, `"K"`, `"Mg"`, `"Ca"`, or `"Zn"` |
| `model` | string | `"default"` | ALIGNN-FF model: `"default"` or `"wt01"` |

**Response:**

| Field | Description |
|-------|-------------|
| `compositions` | Ion fraction array (normalized 0→1) |
| `voltages` | Cell voltage at each step (eV) |
| `energies` | Total energy at each step (eV) |
| `n_steps` | Number of ion removal steps |
| `gravimetric_capacity` | Theoretical gravimetric capacity (mAh/g) |
| `volumetric_capacity` | Theoretical volumetric capacity (mAh/cm³) |
| `density` | Material density (g/cm³) |
| `molar_mass` | Molar mass (g/mol) |
| `formula` | Reduced chemical formula |
| `spacegroup` | Space group |
| `charge` | Ion oxidation state |
| `result_text` | Human-readable summary with CSV data |

---

## Python Examples

=== "Li-ion cathode"

    ```python
    import requests

    LICOO2 = """LiO2Co
    1.0
    2.719 -0.003 4.091
    1.234 2.423 4.091
    -0.004 -0.003 4.913
    Li Co O
    1 1 2
    Cartesian
    1.974 1.209 6.548
    0.0 0.0 0.0
    1.027 0.629 3.405
    2.922 1.789 9.690"""

    response = requests.post(
        "https://atomgpt.org/battery/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": LICOO2,
            "element": "Li",
            "model": "default",
        },
    )
    data = response.json()
    if data["success"]:
        print(f"{data['formula']} — {data['element']}+ cathode")
        print(f"  Gravimetric: {data['gravimetric_capacity']} mAh/g")
        print(f"  Volumetric:  {data['volumetric_capacity']} mAh/cm³")
        print(f"  Steps: {data['n_steps']}")
        for c, v in zip(data["compositions"], data["voltages"]):
            print(f"  x={c:.3f}  V={v:.3f} eV")
    ```

=== "Plot voltage profile"

    ```python
    import requests
    import matplotlib.pyplot as plt

    response = requests.post(
        "https://atomgpt.org/battery/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("LiCoO2.vasp").read(),
            "element": "Li",
        },
    )
    data = response.json()

    plt.figure(figsize=(8, 5))
    plt.plot(data["compositions"], data["voltages"], "o-", color="#f59e0b", lw=2)
    plt.xlabel("Li fraction")
    plt.ylabel("Voltage (eV)")
    plt.title(f"{data['formula']} — {data['gravimetric_capacity']} mAh/g")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("voltage_profile.png")
    ```

=== "Compare ions"

    ```python
    import requests

    POSCAR = open("cathode.vasp").read()

    for ion in ["Li", "Na", "K"]:
        response = requests.post(
            "https://atomgpt.org/battery/predict",
            headers={
                "Authorization": "Bearer sk-XYZ",
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"poscar": POSCAR, "element": ion},
        )
        data = response.json()
        if data["success"]:
            avg_v = sum(data["voltages"]) / len(data["voltages"])
            print(f"{ion}: {data['gravimetric_capacity']} mAh/g, avg V={avg_v:.2f} eV")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Predict voltage profile
response = agent.query_sync("Predict the Li-ion voltage profile for LiCoO2")
print(response)

# Compare models
response = agent.query_sync("Compare default and wt01 ALIGNN-FF for LiCoO2 battery cathode")
print(response)
```

## References

- K. Choudhary, Digital Discovery 2(2), 346 (2023) — ALIGNN-FF [:material-link: DOI](https://doi.org/10.1039/D2DD00096B)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
