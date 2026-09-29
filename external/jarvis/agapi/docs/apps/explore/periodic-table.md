---
title: Periodic Table
---

# Periodic Table

Interactive periodic table with JARVIS property overlays. The backend aggregates per-element statistics from all 76K+ materials in dft_3d, computing count, mean, min, max, and median for 40+ properties including band gaps, formation energy, mechanical moduli, dielectric constants, thermoelectric coefficients, and more.

[:material-open-in-new: Open App](https://atomgpt.org/periodic_table){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** — per-element statistics aggregated from 76K+ materials.

## Endpoints

### `GET /periodic_table/stats` — Per-element aggregated statistics

```bash
curl "https://atomgpt.org/periodic_table/stats" \
  -H "Authorization: Bearer sk-XYZ"
```

**Response:** Per-element dict: `{count, bandgap: {n, mean, min, max, median}, formation_energy: {...}, bulk_modulus: {...}, ...}` for 40+ properties.

40+ properties aggregated: bandgap, mbj_bandgap, hse_gap, spillage, formation_energy, ehull, exfoliation_energy, magmom, bulk_modulus, shear_modulus, poisson, epsx/y/z, mepsx/y/z, piezo_eij/dij, max_ir_mode, n/p-Seebeck, slme, max_efg, avg_elec/hole_mass, Tc_supercon, density, and more.


---

## Python Examples

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/periodic_table/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    si = data.get("Si", {})
    print(f"Si: {si['count']} materials in JARVIS")
    bg = si.get("bandgap")
    if bg:
        print(f"  Band gap: mean={bg['mean']}, range=[{bg['min']}, {bg['max']}] eV")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show periodic table data")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
