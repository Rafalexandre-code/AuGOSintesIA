---
title: Elastic Tensor
---

# Elastic Tensor

Visualize and compare the 6×6 elastic stiffness tensor Cij for any JARVIS-DFT material. Search by formula, elements, space group, and bulk/shear modulus ranges. The data endpoint returns the full tensor plus Voigt-Reuss-Hill derived mechanical properties (bulk/shear modulus, Young's modulus, Poisson ratio, Pugh ratio).

[:material-open-in-new: Open App](https://atomgpt.org/elastic_tensor){ .md-button .md-button--primary }

---

## Overview

Search materials by formula, JARVIS ID, elements, space group, or property ranges. Click any result to fetch and plot the full spectrum. All search results are capped at 500 entries.

!!! info "Data Source"
    **JARVIS-DFT** — `elastic_tensor` field in `dft_3d` dataset (no XML fetch needed).

## Endpoints

### `POST /elastic_tensor/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/elastic_tensor/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si"
  }'
```

Search with elements:

```bash
curl -X POST "https://atomgpt.org/elastic_tensor/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "elements": ["Ti", "O"],
    "element_mode": "all"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | null | Chemical formula |
| `jid` | string | null | Exact JARVIS ID |
| `elements` | list[string] | null | Element symbols |
| `element_mode` | string | "any" | "any", "all", or "exact" |
| `bulk_modulus_min` | float | null | Min bulk modulus Kv (GPa) |
| `bulk_modulus_max` | float | null | Max bulk modulus Kv (GPa) |
| `shear_modulus_min` | float | null | Min shear modulus Gv (GPa) |
| `shear_modulus_max` | float | null | Max shear modulus Gv (GPa) |
| `spacegroup` | string | null | Space group substring |

**Response fields:** `jid, formula, spacegroup, crys, bulk_modulus_kv, shear_modulus_gv, poisson, density`.

---

### `GET /elastic_tensor/data/{jid}` — Fetch spectrum data

Fetch the full 6×6 elastic tensor and Voigt-Reuss-Hill derived properties for a single material.

```bash
curl "https://atomgpt.org/elastic_tensor/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "spacegroup": "Fd-3m",
  "crys": "cubic",
  "density": 2.329,
  "tensor": [[165.77, 63.93, 63.93, 0, 0, 0], ...],
  "derived": {
    "bulk_modulus_voigt": 97.88,
    "bulk_modulus_reuss": 97.88,
    "bulk_modulus_vrh": 97.88,
    "shear_modulus_voigt": 60.23,
    "shear_modulus_reuss": 49.73,
    "shear_modulus_vrh": 54.98,
    "youngs_modulus": 139.72,
    "poisson_ratio": 0.2703,
    "pugh_ratio": 1.78
  },
  "stored": {
    "bulk_modulus_kv": 97.88,
    "shear_modulus_gv": 60.23,
    "poisson": 0.27
  }
}
```

Tensor is 6×6 Voigt notation (GPa). Derived properties computed via Voigt-Reuss-Hill averaging. `stored` contains the pre-computed values from JARVIS-DFT for cross-reference.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/elastic_tensor/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"formula": "Si"},
    )
    data = response.json()
    print(f"Found {data['total']} materials")
    for m in data["results"][:5]:
        print(f"  {m['jid']}: {m['formula']}")
    ```

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/elastic_tensor/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    d = data["derived"]
    print(f"{data['formula']} ({data['crys']})")
    print(f"  Bulk modulus (VRH): {d['bulk_modulus_vrh']} GPa")
    print(f"  Shear modulus (VRH): {d['shear_modulus_vrh']} GPa")
    print(f"  Young's modulus: {d['youngs_modulus']} GPa")
    print(f"  Poisson ratio: {d['poisson_ratio']}")
    print(f"  Pugh ratio: {d['pugh_ratio']}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show elastic tensor for Silicon")
print(response)
```

## References

- K. Choudhary et al., Phys. Rev. B 98, 014107 (2018) [:material-link: DOI](https://doi.org/10.1103/PhysRevB.98.014107)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
