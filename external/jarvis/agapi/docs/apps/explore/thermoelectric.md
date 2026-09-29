---
title: Thermoelectric
---

# Thermoelectric

Visualize and compare thermoelectric (BoltzTrap) data from JARVIS-DFT. The data is fetched by parsing JARVIS XML pages for the `<main_boltz><boltztrap_info>` section. Returns Seebeck coefficient, electrical conductivity, power factor, and electronic thermal conductivity for both n-type and p-type carriers (xx, yy, zz components).

[:material-open-in-new: Open App](https://atomgpt.org/thermoelectric){ .md-button .md-button--primary }

---

## Overview

Search materials by formula, JARVIS ID, elements, space group, or property ranges. Click any result to fetch and plot the full spectrum. All search results are capped at 500 entries.

!!! info "Data Source"
    **JARVIS-DFT** — BoltzTrap data parsed from JARVIS XML pages (`<main_boltz><boltztrap_info>` section).

## Endpoints

### `POST /thermoelectric/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/thermoelectric/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si"
  }'
```

Search with elements:

```bash
curl -X POST "https://atomgpt.org/thermoelectric/search" \
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
| `bandgap_min` | float | null | Min OptB88vdW band gap (eV) |
| `bandgap_max` | float | null | Max OptB88vdW band gap (eV) |
| `spacegroup` | string | null | Space group substring |

**Response fields:** `jid, formula, spacegroup, optb88vdw_bandgap, mbj_bandgap, magmom`.

!!! note
    Pre-filtered to materials with `n-Seebeck != 'na'` (materials that have BoltzTrap data).

---

### `GET /thermoelectric/data/{jid}` — Fetch spectrum data

Fetch BoltzTrap thermoelectric properties by parsing the JARVIS XML page for the material.

```bash
curl "https://atomgpt.org/thermoelectric/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "bandgap": 0.611,
  "properties": {
    "pseeb": [230.23, 230.23, 230.23],
    "pcond": [1.2e14, 1.2e14, 1.2e14],
    "ppf": [6.35, 6.35, 6.35],
    "pkappa": [0.89, 0.89, 0.89],
    "nseeb": [-195.5, -195.5, -195.5],
    "ncond": [2.1e14, 2.1e14, 2.1e14],
    "npf": [8.02, 8.02, 8.02],
    "nkappa": [1.12, 1.12, 1.12]
  }
}
```

8 properties, each a 3-component vector [xx, yy, zz]: `pseeb` (p-Seebeck, μV/K), `pcond` (p-conductivity, 1/(Ω·m)), `ppf` (p-power factor, μW/(mK²)), `pkappa` (p-κ_e, W/(mK)), and the n-type equivalents. XML fetched from `https://www.ctcms.nist.gov/~knc6/static/JARVIS-DFT/{JID}.xml`.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/thermoelectric/search",
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
        "https://atomgpt.org/thermoelectric/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    props = data["properties"]
    print(f"{data['formula']}")
    if "pseeb" in props:
        print(f"  p-Seebeck: {props['pseeb']} μV/K")
    if "nseeb" in props:
        print(f"  n-Seebeck: {props['nseeb']} μV/K")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show thermoelectric for Silicon")
print(response)
```

## References

- K. Choudhary et al., J. Phys.: Condens. Matter 32, 475501 (2020) [:material-link: DOI](https://doi.org/10.1088/1361-648X/aba06b)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
