---
title: Electronic DOS
---

# Electronic DOS

Visualize and compare the electronic density of states from JARVIS-DFT. Spin-resolved up/down channels with total DOS. Search materials by formula, elements, space group, or band gap range, then fetch DOS spectra from JARVIS XML pages via `Webpage.get_dft_electron_dos()`.

[:material-open-in-new: Open App](https://atomgpt.org/electronic_dos){ .md-button .md-button--primary }

---

## Overview

Search materials by formula, JARVIS ID, elements, space group, or property ranges. Click any result to fetch and plot the full spectrum. All search results are capped at 500 entries.

!!! info "Data Source"
    **JARVIS-DFT** — electronic DOS fetched via `jarvis.db.webpages.Webpage.get_dft_electron_dos()`.

## Endpoints

### `POST /electronic_dos/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/electronic_dos/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si"
  }'
```

Search with elements:

```bash
curl -X POST "https://atomgpt.org/electronic_dos/search" \
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
| `formula` | string | null | Chemical formula (auto-reduced) |
| `jid` | string | null | Exact JARVIS ID |
| `elements` | list[string] | null | Element symbols |
| `element_mode` | string | "any" | "any", "all", or "exact" |
| `bandgap_min` | float | null | Min OptB88vdW band gap (eV) |
| `bandgap_max` | float | null | Max OptB88vdW band gap (eV) |
| `spacegroup` | string | null | Space group substring |

**Response fields:** `jid, formula, spacegroup, optb88vdw_bandgap, mbj_bandgap, magmom`.

---

### `GET /electronic_dos/data/{jid}` — Fetch spectrum data

Fetch electronic DOS spectrum for a single material. Returns energy axis and spin-resolved DOS channels.

```bash
curl "https://atomgpt.org/electronic_dos/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "bandgap": 0.611,
  "energies": [-10.0, -9.99, ...],
  "components": {
    "Spin Up": [0.0, 0.01, ...],
    "Spin Down": [0.0, 0.01, ...],
    "Total": [0.0, 0.02, ...]
  }
}
```

DOS channels auto-detected from keys like `total_edos_up`/`total_edos_down`. Total computed from spin components if not present. Energy axis searched across keys: `energies`, `energy`, `edos_energies`.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/electronic_dos/search",
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
        "https://atomgpt.org/electronic_dos/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — {len(data['energies'])} energy points")
    print(f"Channels: {list(data['components'].keys())}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show electronic dos for Silicon")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- K. Choudhary, JOM 74, 1395 (2022) [:material-link: DOI](https://doi.org/10.1007/s11837-022-05209-3)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
