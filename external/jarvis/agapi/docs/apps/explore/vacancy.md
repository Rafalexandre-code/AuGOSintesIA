---
title: Vacancy Explorer
---

# Vacancy Explorer

Browse, search, and visualize vacancy formation energies from the JARVIS vacancy database (464 entries). Filter by bulk formula, vacancy element, Wyckoff position, material type, and formation energy range. Each entry includes bulk and defective structures, chemical potentials, and energetics.

[:material-open-in-new: Open App](https://atomgpt.org/vacancy){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS vacancydb** — 464 vacancy defect entries from `jarvis.db.figshare.data('vacancydb')`.

## Endpoints

### `POST /vacancy/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/vacancy/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `formula` | string | Bulk formula substring |
| `jid` | string | JARVIS ID substring |
| `symbol` | string | Vacancy element symbol |
| `wycoff` | string | Wyckoff position |
| `material_type` | string | Material type (metal, semiconductor, etc.) |
| `ef_min` | float | Min formation energy (eV) |
| `ef_max` | float | Max formation energy (eV) |

**Response fields:** `id, jid, bulk_formula, symbol, wycoff, ef, material_type, chem_pot, bulk_energy, defective_energy`.

---

### `GET /vacancy/data/{defect_id}` — Fetch full vacancy defect record by defect ID.

```bash
curl "https://atomgpt.org/vacancy/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "id": "JVASP-867_Cu_a",
  "jid": "JVASP-867",
  "bulk_formula": "Cu",
  "symbol": "Cu",
  "wycoff": "a",
  "ef": 1.234,
  "chem_pot": -3.456,
  "bulk_energy": -14.567,
  "defective_energy": -10.234,
  "material_type": "metal",
  "bulk": {"n_atoms": 4, "elements": ["Cu"], "abc": [3.61, 3.61, 3.61], "angles": [90.0, 90.0, 90.0]},
  "defective": {"n_atoms": 3, "elements": ["Cu"], "abc": [3.61, 3.61, 3.61], "angles": [90.0, 90.0, 90.0]}
}
```

Formation energy: E_f = E_defective - E_bulk + μ_element. Defect ID format: `{JID}_{element}_{wyckoff}` (e.g. `JVASP-867_Cu_a`).

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/vacancy/search",
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
        "https://atomgpt.org/vacancy/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['bulk_formula']} vacancy at {data['symbol']} ({data['wycoff']})")
    print(f"  Formation energy: {data['ef']:.3f} eV")
    print(f"  Bulk atoms: {data['bulk']['n_atoms']}, Defective: {data['defective']['n_atoms']}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show vacancy explorer for Silicon")
print(response)
```

## References

- K. Choudhary, AIP Advances 13(9) (2023) [:material-link: DOI](https://doi.org/10.1063/5.0159299)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
