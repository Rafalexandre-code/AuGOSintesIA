---
title: Force Field DB
---

# Force Field DB

Search the JARVIS Force-Field (JFF) database. Filter by elements, JID, formula, crystal system (space group), or force-field type (EAM, Tersoff, ReaxFF, etc.). Returns mechanical properties (Kv, Gv, Poisson, Young's modulus), surface/vacancy energies, lattice parameters, and phonon availability.

[:material-open-in-new: Open App](https://atomgpt.org/ff){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS-FF (JFF)** — from `jarvis.db.figshare.data('jff')`.

## Endpoints

### `POST /ff/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/ff/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"formula": "MoS2"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `elements` | string | Dash-separated elements (e.g. 'Si-Ge-') |
| `jid` | string | JID substring |
| `formula` | string | Formula substring |
| `crystal_system` | string | Space group substring |
| `forcefield` | string | Force-field type substring (e.g. 'eam', 'tersoff') |

**Response:** `jid, formula, spg, forcefield, kv, gv, poisson, youngs_gpa, surface_energy, vacancy_energy, a/b/c, n_atoms, ref, phonon`.

---


---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/ff/search",
        headers={"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"},
        json={"formula": "Si"},
    )
    data = response.json()
    print(f"Found {data['total']} entries")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show force field db data")
print(response)
```

## References

- K. Choudhary et al., J. Phys.: Condens. Matter 30, 395901 (2018) [:material-link: DOI](https://doi.org/10.1088/1361-648X/aadaff)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
