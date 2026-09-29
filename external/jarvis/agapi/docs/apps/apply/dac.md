---
title: Direct Air Capture
---

# Direct Air Capture

Predict CO₂ adsorption isotherms for metal-organic frameworks (MOFs) using ALIGNN trained on the hypothetical MOF (hMOF) dataset. Outputs CO₂ uptake at 5 pressure points (0.01, 0.05, 0.1, 0.5, 2.5 bar) from a single POSCAR input. The model (`hmof_co2_absp_alignn`) is auto-downloaded from figshare on first use.

[:material-open-in-new: Open App](https://atomgpt.org/dac){ .md-button .md-button--primary }

---

## Overview

The DAC app uses a specialized ALIGNN model with 5 output features, each corresponding to CO₂ adsorption (mol/kg) at a different pressure point. The model was trained on the hMOF dataset of ~130K hypothetical metal-organic frameworks with GCMC-computed CO₂ isotherms. Input any MOF crystal structure as POSCAR and get the predicted isotherm in seconds.

!!! info "Data Source"
    **ALIGNN** model `hmof_co2_absp_alignn` — auto-downloaded from figshare via `alignn.pretrained.get_figshare_model()`.
    Trained on the hMOF dataset (hypothetical MOFs with GCMC CO₂ isotherms).

## Endpoints

### `POST /dac/predict` — Predict CO₂ isotherm from POSCAR

```bash
curl -X POST "https://atomgpt.org/dac/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "ZIF-8\n1.0\n-8.496 8.496 8.496\n8.496 -8.496 8.496\n8.496 8.496 -8.496\nZn N H C\n6 24 96 48\ndirect\n0.75 0.25 0.5\n0.25 0.75 0.5\n0.5 0.75 0.25\n0.5 0.25 0.75\n0.25 0.5 0.75\n0.75 0.5 0.25\n0.651 0.093 0.378\n0.714 0.273 0.622\n0.286 0.907 0.559\n0.349 0.727 0.441\n0.378 0.651 0.093\n0.622 0.714 0.273\n0.559 0.286 0.907\n0.441 0.349 0.727\n0.093 0.378 0.651\n0.273 0.622 0.714\n0.907 0.559 0.286\n0.727 0.441 0.349\n0.093 0.651 0.378\n0.273 0.714 0.622\n0.907 0.286 0.559\n0.727 0.349 0.441\n0.651 0.378 0.093\n0.714 0.622 0.273\n0.286 0.559 0.907\n0.349 0.441 0.727\n0.378 0.093 0.651\n0.622 0.273 0.714\n0.559 0.907 0.286\n0.441 0.727 0.349"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | VASP POSCAR of MOF structure (max 50KB) |

**Response:**

| Field | Description |
|-------|-------------|
| `pressures` | `[0.01, 0.05, 0.1, 0.5, 2.5]` (bar) |
| `adsorption` | Predicted CO₂ uptake at each pressure (mol/kg) |
| `pressure_unit` | `"bar"` |
| `adsorption_unit` | `"mol/kg"` |
| `formula` | Reduced chemical formula |
| `num_atoms` | Number of atoms |
| `spacegroup` | Space group |

---

## Python Examples

=== "Predict isotherm"

    ```python
    import requests

    ZIF8 = open("ZIF-8.vasp").read()

    response = requests.post(
        "https://atomgpt.org/dac/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": ZIF8},
    )
    data = response.json()
    if data["success"]:
        print(f"{data['formula']} ({data['num_atoms']} atoms)")
        for p, a in zip(data["pressures"], data["adsorption"]):
            print(f"  {p:>5.2f} bar → {a:.5f} mol/kg")
    ```

=== "Plot isotherm"

    ```python
    import requests
    import matplotlib.pyplot as plt

    response = requests.post(
        "https://atomgpt.org/dac/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": open("MOF.vasp").read()},
    )
    data = response.json()

    plt.figure(figsize=(7, 5))
    plt.semilogx(data["pressures"], data["adsorption"], "o-", color="#22c55e", lw=2, ms=8)
    plt.xlabel("Pressure (bar)")
    plt.ylabel("CO₂ Adsorption (mol/kg)")
    plt.title(f"{data['formula']} — CO₂ Isotherm (ALIGNN)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("co2_isotherm.png")
    ```

=== "Screen multiple MOFs"

    ```python
    import requests
    import glob

    results = []
    for f in glob.glob("mofs/*.vasp"):
        response = requests.post(
            "https://atomgpt.org/dac/predict",
            headers={
                "Authorization": "Bearer sk-XYZ",
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"poscar": open(f).read()},
        )
        data = response.json()
        if data["success"]:
            # Adsorption at 0.5 bar (index 3)
            results.append((data["formula"], data["adsorption"][3]))

    results.sort(key=lambda x: x[1], reverse=True)
    print("Top MOFs by CO₂ uptake at 0.5 bar:")
    for formula, ads in results[:10]:
        print(f"  {formula}: {ads:.4f} mol/kg")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Predict isotherm
response = agent.query_sync("Predict the CO2 adsorption isotherm for ZIF-8")
print(response)
```

## References

- Kamal Choudhary, Taner Yildirim, Daniel W Siderius, A Gilad Kusne, Austin McDannald, Diana L Ortiz-Montalvo, Comp. Mat. Sci. 210, 111388 (2022) [:material-link: DOI](https://www.sciencedirect.com/science/article/pii/S092702562200163X)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- K. Choudhary, npj Comp. Mat. 7, 185 (2021) — ALIGNN [:material-link: DOI](https://doi.org/10.1038/s41524-021-00650-1)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
