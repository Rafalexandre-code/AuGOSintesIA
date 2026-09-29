---
title: Interface Generator (API)
---

# Interface Generator (API)

Generate heterostructure interfaces via the REST API using InterfaceCombi (Zur & McGill ZSL lattice matching). This is the GET endpoint counterpart to the Heterostructure Builder's POST endpoint. Accepts film/substrate as POSCAR strings or JARVIS JIDs with full ZSL parameters. Optionally computes work of adhesion with ALIGNN-FF.

[:material-open-in-new: Open App](https://atomgpt.org/generate_interface){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **InterMat** — `InterfaceCombi` for ZSL lattice matching. **JARVIS dft_3d** for JID lookups.

## Endpoint

### `GET /generate_interface` — Generate heterostructure (API key)

Returns the combined heterostructure POSCAR as plain text.

```bash
curl "https://atomgpt.org/generate_interface?film_ids=JVASP-1002&subs_ids=JVASP-1174&film_indices=0_0_1&subs_indices=0_0_1&max_area=300&APIKEY=sk-XYZ"
```

| Param | Default | Description |
|-------|---------|-------------|
| `poscar_film` | null | Film POSCAR (provide this OR film_ids) |
| `poscar_subs` | null | Substrate POSCAR (provide this OR subs_ids) |
| `film_ids` | null | Comma-separated JARVIS JIDs for film |
| `subs_ids` | null | Comma-separated JARVIS JIDs for substrate |
| `film_indices` | 0_0_1 | Film Miller indices (h_k_l) |
| `subs_indices` | 0_0_1 | Substrate Miller indices |
| `film_thickness` | 16 | Film slab thickness (Å) |
| `subs_thickness` | 16 | Substrate slab thickness (Å) |
| `max_area` | 300 | Max supercell area (Å²) |
| `ltol` | 0.08 | Length tolerance for ZSL |
| `separations` | 2.5 | Comma-separated interface separations (Å) |
| `vacuum_interface` | 2.0 | Vacuum at interface (Å) |
| `conventional` | true | Use conventional cell |
| `calculate_wad` | false | Compute W_ad with ALIGNN-FF |

Returns plain text POSCAR of the heterostructure. With `calculate_wad=true`, returns JSON with `heterostructure_atoms`, `film_atoms`, `substrate_atoms`, `wads`, and `min_wad`.

---

## Python Examples

=== "Generate by JID"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/generate_interface",
        params={
            "film_ids": "JVASP-1002",
            "subs_ids": "JVASP-1174",
            "film_indices": "0_0_1",
            "subs_indices": "0_0_1",
            "max_area": 300,
            "APIKEY": "sk-XYZ",
        },
    )
    with open("POSCAR_interface", "w") as f:
        f.write(response.text)
    print(f"Interface POSCAR: {len(response.text)} chars")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show interface generator (api) for Silicon")
print(response)
```

## References

- K. Choudhary et al., Phys. Rev. Mat. 7, 014009 (2023) [:material-link: DOI](https://doi.org/10.1103/PhysRevMaterials.7.014009)
- K. Choudhary et al., Digital Discovery 3, 1209 (2024) [:material-link: DOI](https://doi.org/10.1039/D4DD00031E)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
