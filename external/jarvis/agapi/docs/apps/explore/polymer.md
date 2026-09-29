---
title: Polymer Explorer
---

# Polymer Explorer

Browse and search crystalline polymer properties by cross-referencing the Polymer Genome database (1,073 entries) with JARVIS-DFT 3D via the `reference` field. Merges DFT-computed properties (band gaps, mechanical, magnetic) with polymer-specific data (HSE/GGA gaps, dielectric constants from Polymer Genome).

[:material-open-in-new: Open App](https://atomgpt.org/polymer){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **Polymer Genome** (1,073 entries) cross-referenced with **JARVIS dft_3d** (76K entries) via `reference` field.

## Endpoints

### `POST /polymer/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/polymer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"formula": "MoS2"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `formula` | string | Chemical formula |
| `jid` | string | JARVIS ID |
| `label` | string | Polymer label substring |
| `elements` | string | Comma-separated elements (all required) |
| `bandgap_min/max` | float | OptB88vdW band gap range (eV) |
| `diel_min/max` | float | Total dielectric constant range |

**Response:** `jid, poly_id, formula, label, spg_symbol, bandgap, hse_gap_pg, gga_gap_pg, diel_tot, diel_elec, formation_energy, magmom`.

---

### `GET /polymer/data/{jid}` — Full record

```bash
curl "https://atomgpt.org/polymer/data/JVASP-664" \
  -H "Authorization: Bearer sk-XYZ"
```

**Response:** Merged fields: JARVIS (bandgap, mbj_bandgap, formation_energy, bulk/shear modulus, epsx/y/z, etc.) + Polymer Genome (poly_id, label, method, src, vol, atom_en, hse_gap, gga_gap, diel_tot, diel_ion, diel_elec) + structure info.


---

## Python Examples

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/polymer/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — {data['label']}")
    print(f"  JARVIS gap: {data['bandgap']} eV, PG HSE gap: {data['hse_gap_pg']} eV")
    print(f"  Dielectric: total={data['diel_tot']}, elec={data['diel_elec']}")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show polymer explorer data")
print(response)
```

## References

- K. Choudhary et al., Sci. Data 3, 160012 (2016) [:material-link: DOI](https://doi.org/10.1038/sdata.2016.12)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
