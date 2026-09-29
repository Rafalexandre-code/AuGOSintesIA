---
title: Spillage Explorer
---

# Spillage Explorer

Visualize and compare spin-orbit coupling (SOC) spillage data from JARVIS-DFT for identifying topological insulators and semimetals. Returns per-k-point spillage values, k-point coordinates, max spillage, and topological classification (spillage > 0.5 = non-trivial). Data parsed from JARVIS XML.

[:material-open-in-new: Open App](https://atomgpt.org/spillage){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS-DFT** — SOC spillage from JARVIS XML (`<spillage_k>`, `<max_spillage>`, `<spillage_kpoints>` tags).

## Endpoints

### `POST /spillage/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/spillage/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

Standard search fields: `formula`, `jid`, `elements`, `element_mode` (any/all/exact), `bandgap_min`, `bandgap_max`, `spacegroup`. Max 500 results.

!!! note
    Pre-filtered to materials with `spillage != 'na'`.

---

### `GET /spillage/data/{jid}` — Fetch per-k-point spillage values and topological classification.

```bash
curl "https://atomgpt.org/spillage/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "bandgap": 0.611,
  "max_spillage": 0.32,
  "spillage_k": [0.12, 0.15, 0.32, 0.08, ...],
  "kpoints": [[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], ...],
  "k_indices": [0, 1, 2, 3, ...],
  "n_kpoints": 50,
  "n_above_threshold": 0,
  "topological_classification": "Topologically trivial (spillage <= 0.5)"
}
```

Spillage > 0.5 indicates topologically non-trivial band inversion. `n_above_threshold` counts k-points with spillage > 0.5. K-points parsed from semicolon-separated `kx;ky;kz` format.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/spillage/search",
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
        "https://atomgpt.org/spillage/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']}: {data['topological_classification']}")
    print(f"  Max spillage: {data['max_spillage']}")
    print(f"  K-points above 0.5: {data['n_above_threshold']}/{data['n_kpoints']}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show spillage explorer for Silicon")
print(response)
```

## References

- K. Choudhary et al., Sci. Rep. 9, 8534 (2019) [:material-link: DOI](https://doi.org/10.1038/s41598-019-45028-y)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
