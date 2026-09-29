---
title: EFG Explorer
---

# EFG Explorer

Visualize and compare electric field gradient (EFG) tensors from JARVIS-DFT for NMR/NQR applications. Per-site 3×3 EFG tensors with element and Wyckoff labels, max EFG (Vzz), and asymmetry parameter η. Data parsed from JARVIS XML `<efg_raw_tensor>` section.

[:material-open-in-new: Open App](https://atomgpt.org/efg){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS-DFT** — EFG tensors parsed from JARVIS XML (`<efg_raw_tensor>` tag).

## Endpoints

### `POST /efg/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/efg/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

Standard search fields: `formula`, `jid`, `elements`, `element_mode` (any/all/exact), `bandgap_min`, `bandgap_max`, `spacegroup`. Max 500 results.

!!! note
    Pre-filtered to materials with `max_efg != 'na'`.

---

### `GET /efg/data/{jid}` — Fetch per-site 3×3 EFG tensors for a single material.

```bash
curl "https://atomgpt.org/efg/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "bandgap": 0.611,
  "max_efg": 0.001,
  "max_efg_eta": null,
  "sites": [
    {
      "element": "Si",
      "wyckoff": "a",
      "tensor": [[0.001, 0.0, 0.0], [0.0, 0.001, 0.0], [0.0, 0.0, -0.002]]
    }
  ]
}
```

EFG tensor format in XML: `Element,Wyckoff,xx,xy,xz,yx,yy,yz,zx,zy,zz;` semicolon-separated sites. Returns per-site 3×3 tensor, element, Wyckoff label, plus scalar `max_efg` and `max_efg_eta`.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/efg/search",
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
        "https://atomgpt.org/efg/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — max EFG: {data['max_efg']}")
    for site in data["sites"]:
        print(f"  {site['element']} ({site['wyckoff']}): Vzz={site['tensor'][2][2]:.4f}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show efg explorer for Silicon")
print(response)
```

## References

- K. Choudhary et al., Nature Sci. Data 7, 362 (2020) [:material-link: DOI](https://doi.org/10.1038/s41597-020-00707-8)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
