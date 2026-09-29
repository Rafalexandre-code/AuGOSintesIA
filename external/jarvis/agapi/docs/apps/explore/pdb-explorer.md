---
title: PDB Explorer
---

# PDB Explorer

Search 200K+ protein structures from the RCSB Protein Data Bank. Full-text search via RCSB Search API v2, with detailed entry metadata (resolution, R-factor, authors, unit cell, polymer entities with sequences). No API key needed — the app proxies RCSB REST API calls.

[:material-open-in-new: Open App](https://atomgpt.org/pdb_explorer){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **RCSB PDB REST API** — `search.rcsb.org` (search) + `data.rcsb.org` (entry metadata + polymer entities).

## Endpoints

### `POST /pdb_explorer/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/pdb_explorer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"formula": "MoS2"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Full-text search query (e.g. 'insulin', 'kinase') |
| `max_results` | int | Max results (default 20, max 50) |

**Response:** `pdb_id, score, title, method, resolution, deposition_date, organism, authors, spacegroup`.

---

### `GET /pdb_explorer/data/{jid}` — Full record

```bash
curl "https://atomgpt.org/pdb_explorer/data/JVASP-664" \
  -H "Authorization: Bearer sk-XYZ"
```

**Response:** pdb_id, title, method, resolution, r_factor, r_free, deposition/release dates, authors, journal, doi, pub_year, cell (a/b/c/α/β/γ), spacegroup, z_value, polymer/nonpolymer/assembly counts, molecular_weight, polymers (entity_id, name, type, sequence, length, organism, weight).


---

## Python Examples

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/pdb_explorer/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['pdb_id']}: {data['title']}")
    print(f"  Method: {data['method']}, Resolution: {data['resolution']} Å")
    for p in data["polymers"]:
        print(f"  Chain {p['entity_id']}: {p['name']} ({p['length']} residues)")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show pdb explorer data")
print(response)
```

## References

- H.M. Berman et al., Nucleic Acids Res. 28, 235 (2000) [:material-link: DOI](https://doi.org/10.1093/nar/28.1.235)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
