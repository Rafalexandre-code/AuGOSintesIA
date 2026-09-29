---
title: 2D Materials Explorer
---

# 2D Materials Explorer

Browse, search, and visualize properties of ~1,100 2D monolayer materials from the JARVIS-DFT 2D dataset. Filter by formula, elements, space group, band gap, exfoliation energy, and magnetic state. Full property card with 30+ fields per material.

[:material-open-in-new: Open App](https://atomgpt.org/twod){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_2d** — ~1,100 2D monolayer entries from `jarvis.db.figshare.data('dft_2d')`.

## Endpoints

### `POST /twod/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/twod/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"formula": "MoS2"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `formula` | string | Chemical formula |
| `jid` | string | JARVIS ID |
| `elements` | list[string] | Element symbols |
| `element_mode` | string | "any" or "all" |
| `spacegroup` | string | Space group symbol or number |
| `bandgap_min/max` | float | OptB88vdW band gap range (eV) |
| `exfol_min/max` | float | Exfoliation energy range (meV/atom) |
| `magnetic` | string | "yes", "no", or null (any) |

**Response:** `jid, formula, spg_symbol, bandgap, mbj_bandgap, exfoliation_energy, magmom, spillage, ehull, formation_energy`.

---

### `GET /twod/data/{jid}` — Full record

```bash
curl "https://atomgpt.org/twod/data/JVASP-664" \
  -H "Authorization: Bearer sk-XYZ"
```

**Response:** 30+ fields: bandgap, mbj_bandgap, hse_gap, formation_energy, exfoliation_energy, magmom, spillage, slme, ehull, Tc_supercon, epsx/y/z, mepsx/y/z, max_efg, dfpt_piezo_max_eij, max_ir_mode, n/p-Seebeck, bulk/shear modulus, poisson, structure info.


---

## Python Examples

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/twod/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} ({data['spg_symbol']})")
    print(f"  Band gap: {data['bandgap']} eV, Exfoliation: {data['exfoliation_energy']} meV/atom")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show 2d materials explorer data")
print(response)
```

## References

- K. Choudhary et al., Sci. Rep. 7, 5179 (2017) [:material-link: DOI](https://doi.org/10.1038/s41598-017-05402-0)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
