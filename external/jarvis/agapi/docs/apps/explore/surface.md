---
title: Surface Explorer
---

# Surface Explorer

Browse, search, and visualize surface properties from the JARVIS surface database (607 entries). Surface energies, work functions, Fermi levels, VBM/CBM, and electrostatic potential profiles. Filter by formula, JID, Miller indices, and surface energy range.

[:material-open-in-new: Open App](https://atomgpt.org/surface){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS surfacedb** — 607 surface slab entries from `jarvis.db.figshare.data('surfacedb')`.

## Endpoints

### `POST /surface/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/surface/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `formula` | string | Formula substring |
| `jid` | string | JARVIS ID (extracted from surface name) |
| `miller` | string | Miller index string (e.g. '110') |
| `surf_en_min` | float | Min surface energy |
| `surf_en_max` | float | Max surface energy |

**Response fields:** `idx, name, jid, miller, thickness, formula, surf_en, efermi, scf_vbm, scf_cbm, surf_vbm, surf_cbm`.

---

### `GET /surface/data/{idx (integer)}` — Fetch full surface record by index.

```bash
curl "https://atomgpt.org/surface/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "idx": 42,
  "name": "Surface-JVASP-1002_miller_1_1_1_thickness_16_VASP_PBE_noDP",
  "jid": "JVASP-1002",
  "miller": "(1 1 1)",
  "thickness": "16",
  "method": "VASP PBE",
  "formula": "Si",
  "surf_en": 1.36,
  "efermi": 4.52,
  "scf_vbm": -5.73, "scf_cbm": -4.52,
  "surf_vbm": -5.73, "surf_cbm": -4.52,
  "avg_max": 8.2,
  "phi": [0.1, 0.2, ...],
  "slab": {"n_atoms": 32, "elements": ["Si"], "abc": [3.84, 3.84, 40.0], "angles": [90, 90, 90]}
}
```

Surface name parsed for JID, Miller indices, and thickness. `phi` is the electrostatic potential profile (1D array along z-axis). Surface energy in J/m².

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/surface/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"formula": "Si"},
    )
    data = response.json()
    print(f"Found {data['total']} entries")
    for m in data["results"][:5]:
        print(f"  {m['jid']}: {m.get('formula', m.get('bulk_formula', ''))}")
    ```

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/surface/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} {data['miller']} surface")
    print(f"  Surface energy: {data['surf_en']} J/m²")
    print(f"  Work function proxy: {data['avg_max']}")
    print(f"  Slab: {data['slab']['n_atoms']} atoms")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show surface explorer for Silicon")
print(response)
```

## References

- K. Choudhary et al., Digital Discovery (2024) [:material-link: DOI](https://doi.org/10.1039/D4DD00031E)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
