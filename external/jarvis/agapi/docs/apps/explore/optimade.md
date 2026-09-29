---
title: OPTIMADE Explorer
---

# OPTIMADE Explorer

Query JARVIS-DFT using OPTIMADE-style filter syntax served from an in-memory engine (no external API calls). Supports: `elements HAS ANY/ALL/ONLY`, `chemical_formula_reduced`, `chemical_formula_anonymous`, `spg_symbol`, `id`, and numeric comparisons (>=, <=, >, <, =, !=) on 11 properties. Paginated results in OPTIMADE v1.1.0 format with lattice vectors and site positions.

[:material-open-in-new: Open App](https://atomgpt.org/optimade_explorer){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** — in-memory OPTIMADE filter engine over 76K+ entries.

## Endpoints

### `POST /optimade_explorer/query` — OPTIMADE filter query

```bash
curl -X POST "https://atomgpt.org/optimade_explorer/query" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"filter_string": "elements HAS ALL \\"Si\\",\\"O\\" AND optb88vdw_bandgap > 2", "page": 1, "page_size": 25}'
```

**Supported filters:** `elements HAS ANY/ALL/ONLY "El"`, `chemical_formula_reduced = "X"`, `chemical_formula_anonymous = "AB2"`, `spg_symbol`, `id`, and numeric `>=/<=/>/</=/!=` on: nelements, nsites, formation_energy_peratom, optb88vdw_bandgap, mbj_bandgap, ehull, bulk_modulus_kv, shear_modulus_gv, spillage, magmom_oszicar, slme, density. Clauses joined with `AND`.

**Response:** OPTIMADE v1.1.0 format with `meta`, `links` (pagination), `data` (id, type, attributes with lattice_vectors, cartesian_site_positions, species_at_sites, and all numeric properties).

---

### `GET /optimade_explorer/entry/{jid}` — Single entry

```bash
curl "https://atomgpt.org/optimade_explorer/entry/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ"
```


---

## Python Examples

=== "OPTIMADE query"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/optimade_explorer/query",
        headers={"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"},
        json={"filter_string": "elements HAS ALL \"Si\",\"O\" AND optb88vdw_bandgap > 3", "page_size": 10},
    )
    data = response.json()
    print(f"Found {data['total']} materials")
    for entry in data["data"]:
        a = entry["attributes"]
        print(f"  {entry['id']}: {a['chemical_formula_reduced']} gap={a['optb88vdw_bandgap']}")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show optimade explorer data")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
