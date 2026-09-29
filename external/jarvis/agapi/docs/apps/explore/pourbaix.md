---
title: PourbaixMat
---

# PourbaixMat

Compute Pourbaix (electrochemical aqueous stability) diagrams from JARVIS-DFT formation energies + ASE Pourbaix thermodynamic engine. Supports configurable pH/potential ranges, ionic concentration, temperature, and manual energy overrides. Returns heatmap, stability region, and phase map data for the target material.

[:material-open-in-new: Open App](https://atomgpt.org/pourbaix){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** (formation energies, auto-fetched) + **ASE** (solvated ion refs from Johnson 1992 / Pourbaix atlas).

## Endpoints

### `POST /pourbaix/predict` — Compute Pourbaix diagram

```bash
curl -X POST "https://atomgpt.org/pourbaix/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"element": "Zn", "target": "ZnO", "solids": ["Zn", "ZnO"]}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `element` | string | required | Metal element symbol |
| `target` | string | required | Target formula |
| `solids` | list[string] | [] | Competing solid phases |
| `manual_energies` | dict | {} | Override formation energies (eV/f.u.) |
| `U_min/U_max` | float | -2/2 | Potential range (V vs SHE) |
| `pH_min/pH_max` | float | 0/14 | pH range |
| `resolution` | int | 60 | Grid resolution (20–120) |
| `conc` | float | 1e-6 | Ionic concentration (mol/L) |
| `temperature` | float | 298.15 | Temperature (K) |
| `use_jarvis` | bool | true | Auto-fetch from JARVIS-DFT |

**Response:** `pH` array, `U` array, `energies[pH][U]` (ΔG in eV), `phases[pH][U]` (competing phase names), `refs_used`, `stable_frac`.

---

### `GET /pourbaix/jarvis_search` — Search JARVIS cache

```bash
curl "https://atomgpt.org/pourbaix/jarvis_search?q=ZnO" -H "Authorization: Bearer sk-XYZ"
```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show pourbaixmat data")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
