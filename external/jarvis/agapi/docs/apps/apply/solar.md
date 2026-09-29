---
title: Solar Cell Screening
---

# Solar Cell Screening

Predict theoretical solar cell performance using SLME (spectroscopic limited maximum efficiency) and Shockley-Queisser (SQ) limit. Two modes: (1) input a JARVIS ID to download TBmBJ vasprun.xml and compute SLME + SQ + J-V curves automatically, (2) input custom band gaps and absorption coefficient data for SLME calculation.

[:material-open-in-new: Open App](https://atomgpt.org/solar){ .md-button .md-button--primary }

---

## Overview

The Solar Cell Screening app uses `jarvis.analysis.solarefficiency.solar.SolarEfficiency` to compute theoretical photovoltaic performance. For JARVIS materials, it downloads the TBmBJ vasprun.xml from figshare, extracts direct/indirect band gaps and the average absorption coefficient, then sweeps film thickness (1nm–5μm) to find the optimal SLME. It also computes the SQ efficiency limit and full J-V / P-V curves at the optimal thickness.

!!! info "Data Source"
    **JARVIS TBmBJ** — vasprun.xml files from `jarvis.db.figshare.data('raw_files')['TBMBJ']`.
    **AM1.5G** solar spectrum from JARVIS package.

## Endpoints

### `POST /solar/predict-jid` — SLME + SQ from JARVIS ID

Downloads the TBmBJ vasprun.xml for the given JARVIS ID, extracts band gaps and absorption coefficient, computes SLME efficiency vs thickness, finds the optimal thickness, and returns SQ efficiency + J-V curves.

```bash
curl -X POST "https://atomgpt.org/solar/predict-jid" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-1002"
  }'
```

```bash
curl -X POST "https://atomgpt.org/solar/predict-jid" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-1067"
  }'
```

**Response** includes:

| Field | Description |
|-------|-------------|
| `dirgap` | Direct band gap (eV) |
| `indirgap` | Indirect band gap (eV) |
| `optimal_thickness` | Optimal film thickness (m) |
| `optimal_efficiency` | SLME at optimal thickness (%) |
| `sq_efficiency` | Shockley-Queisser limit (%) |
| `thickness` | Array of thickness values (m) |
| `efficiencies` | SLME at each thickness (%) |
| `V` | Voltage array for J-V curve |
| `JV` | Current density array (A/m²) |
| `PV` | Power density array (W/m²) |
| `optimal_voltage` | Voltage at max power (V) |
| `J_sc` | Short-circuit current density (A/m²) |

---

### `POST /solar/predict-data` — SLME from custom absorption data

Compute SLME from user-provided band gaps and absorption coefficient data. Requires at least 5 data points.

```bash
curl -X POST "https://atomgpt.org/solar/predict-data" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "indirect_gap": 1.1,
    "direct_gap": 3.4,
    "temperature": 293.15,
    "energies": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    "absorptions": [0, 0, 100, 5000, 20000, 50000, 80000, 100000, 120000, 150000]
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `indirect_gap` | float | required | Indirect band gap (eV) |
| `direct_gap` | float | required | Direct band gap (eV) |
| `temperature` | float | 293.15 | Temperature (K) |
| `energies` | list[float] | required | Photon energy array (eV) |
| `absorptions` | list[float] | required | Absorption coefficient array (cm⁻¹) |

**Response** same as `/predict-jid` — thickness sweep, optimal SLME, SQ limit, J-V curves.

---

## Python Examples

=== "Predict by JID"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/solar/predict-jid",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"jid": "JVASP-1002"},
    )
    data = response.json()
    if data["success"]:
        print(f"Direct gap: {data['dirgap']:.3f} eV")
        print(f"Indirect gap: {data['indirgap']:.3f} eV")
        print(f"SLME: {data['optimal_efficiency']:.2f}%")
        print(f"SQ limit: {data['sq_efficiency']:.2f}%")
        print(f"Optimal thickness: {data['optimal_thickness']*1e6:.2f} μm")
        print(f"J_sc: {data['J_sc']:.2f} A/m²")
    ```

=== "Custom absorption data"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/solar/predict-data",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "indirect_gap": 1.1,
            "direct_gap": 3.4,
            "temperature": 300.0,
            "energies": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            "absorptions": [0, 0, 100, 5000, 20000, 50000, 80000, 100000],
        },
    )
    data = response.json()
    if data["success"]:
        print(f"SLME: {data['optimal_efficiency']:.2f}%")
        print(f"SQ limit: {data['sq_efficiency']:.2f}%")
    ```

=== "Plot J-V curve"

    ```python
    import requests
    import matplotlib.pyplot as plt

    response = requests.post(
        "https://atomgpt.org/solar/predict-jid",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"jid": "JVASP-1002"},
    )
    data = response.json()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(data["V"], data["JV"])
    ax1.set_xlabel("Voltage (V)")
    ax1.set_ylabel("Current density (A/m²)")
    ax1.set_title("J-V curve")

    ax2.plot([t * 1e6 for t in data["thickness"]], data["efficiencies"])
    ax2.set_xlabel("Thickness (μm)")
    ax2.set_ylabel("SLME (%)")
    ax2.set_title(f"SLME vs thickness (opt: {data['optimal_efficiency']:.1f}%)")
    plt.tight_layout()
    plt.savefig("solar_jvasp1002.png")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Predict by JID
response = agent.query_sync("Compute the solar cell efficiency for JVASP-1002")
print(response)

# Compare materials
response = agent.query_sync("Compare the SLME of JVASP-1002 and JVASP-1067")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- K. Choudhary, F. Tavazza, Chem. Mater. 31, 5900 (2019) — Accelerated Discovery of Efficient Solar Cell Materials [:material-link: DOI](https://doi.org/10.1021/acs.chemmater.9b02166)
- K. Choudhary et al., Nature Sci. Data 5, 180082 (2018) — JARVIS-DFT [:material-link: DOI](https://doi.org/10.1038/sdata.2018.82)
- C. Ginter, K. Choudhary, S. Mandal, arXiv:2510.08738 (2025) [:material-link: arXiv](https://arxiv.org/abs/2510.08738)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
