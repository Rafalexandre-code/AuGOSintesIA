---
title: Dielectric Function
---

# Dielectric Function

Look up and interactively plot the MBJ dielectric function ε(ω) for any JARVIS-DFT material. Returns real and imaginary parts of the dielectric tensor (xx, yy, zz components) plus computed averages. Data fetched via `Webpage.get_dft_mbj_dielectric_function()`.

[:material-open-in-new: Open App](https://atomgpt.org/dielectric_function){ .md-button .md-button--primary }

---

## Overview

Search materials by formula, JARVIS ID, elements, space group, or property ranges. Click any result to fetch and plot the full spectrum. All search results are capped at 500 entries.

!!! info "Data Source"
    **JARVIS-DFT** — MBJ dielectric function via `jarvis.db.webpages.Webpage.get_dft_mbj_dielectric_function()`.

## Endpoints

### `POST /dielectric_function/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/dielectric_function/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si"
  }'
```

Search with elements:

```bash
curl -X POST "https://atomgpt.org/dielectric_function/search" \
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
| `bandgap_min` | float | null | Min MBJ band gap (eV) |
| `bandgap_max` | float | null | Max MBJ band gap (eV) |

**Response fields:** `jid, formula, spacegroup, mbj_bandgap, optb88vdw_bandgap`.

---

### `GET /dielectric_function/data/{jid}` — Fetch spectrum data

Fetch MBJ dielectric function ε(ω) for a single material. Returns energy axis, real/imaginary xx/yy/zz components, and computed averages.

```bash
curl "https://atomgpt.org/dielectric_function/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "energies": [0.0, 0.1, 0.2, ...],
  "components": {
    "imag_xx": [...], "imag_yy": [...], "imag_zz": [...],
    "real_xx": [...], "real_yy": [...], "real_zz": [...],
    "imag_avg": [...], "real_avg": [...]
  }
}
```

8 components: `imag_xx/yy/zz`, `real_xx/yy/zz`, plus computed `imag_avg` and `real_avg` (arithmetic mean of xx/yy/zz).

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/dielectric_function/search",
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
        "https://atomgpt.org/dielectric_function/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — {len(data['energies'])} energy points")
    print(f"Components: {list(data['components'].keys())}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show dielectric function for Silicon")
print(response)
```

## References

- K. Choudhary et al., Nature Sci. Data 5, 180082 (2018) [:material-link: DOI](https://doi.org/10.1038/sdata.2018.82)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
