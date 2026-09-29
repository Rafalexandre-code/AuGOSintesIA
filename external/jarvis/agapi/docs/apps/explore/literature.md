---
title: Literature Explorer
---

# Literature Explorer

Search for research papers and matching JARVIS materials simultaneously. Queries arXiv (full-text search) and Crossref (DOI-indexed publications) for papers, then cross-references the query formula against JARVIS-DFT for matching crystal structures. Also provides standalone GET endpoints for arXiv and Crossref API access.

[:material-open-in-new: Open App](https://atomgpt.org/literature_materials){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **arXiv API** (Atom XML) + **Crossref API** (JSON) + **JARVIS dft_3d** (formula matching).

## Endpoints

### `POST /literature_materials/search` — Combined literature + materials search

```bash
curl -X POST "https://atomgpt.org/literature_materials/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"query": "MoS2", "max_papers": 10}'
```

**Response:** `papers.arxiv[]` (title, id, summary, published, authors), `papers.crossref[]` (title, doi, publisher, date), `materials[]` (jid, formula, spacegroup, band_gap, formation_energy).

---

### `GET /arxiv` — arXiv search (API key auth)

```bash
curl "https://atomgpt.org/arxiv?query=MgB2&max_results=10&APIKEY=sk-XYZ"
```

### `GET /crossref` — Crossref search (API key auth)

```bash
curl "https://atomgpt.org/crossref?query=Al2O3&rows=20&APIKEY=sk-XYZ"
```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show literature explorer data")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
