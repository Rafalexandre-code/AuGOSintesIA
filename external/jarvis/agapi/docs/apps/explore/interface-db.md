---
title: Interface Database
---

# Interface Database

Browse and search the JARVIS heterostructure interface database. View pre-computed interface properties including band alignments (Type I/II/III), lattice mismatch, and interface energies.

[:material-open-in-new: Open App](https://atomgpt.org/interface_db){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS interfacedb** — pre-computed heterostructure interface entries.

## Endpoints

### `GET /interface_db` — HTML page

### `POST /interface_db/search` — Search interfaces

```bash
curl -X POST "https://atomgpt.org/interface_db/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"formula": "Si"}'
```

### `GET /interface_db/data/{idx}` — Full interface record


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show interface database data")
print(response)
```

## References

- K. Choudhary et al., Phys. Rev. Mat. 7, 014009 (2023) [:material-link: DOI](https://doi.org/10.1103/PhysRevMaterials.7.014009)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
