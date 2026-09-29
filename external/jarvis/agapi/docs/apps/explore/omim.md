---
title: OMIM Gene Explorer
---

# OMIM Gene Explorer

Browse the Online Mendelian Inheritance in Man (OMIM) database — 15,000+ genes and 8,000+ phenotypes. Three search modes: Gene Search (by symbol/keyword), Chromosome Browser (by chromosome position), and Clinical Synopsis Search (by phenotype features). Full entry detail with clinical synopsis, allelic variants, and text sections. Uses OMIM REST API.

[:material-open-in-new: Open App](https://atomgpt.org/omim){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **OMIM REST API** (api.omim.org) — requires API key (configured server-side).

## Endpoints

### `POST /omim/gene_search` — Search genes/entries

```bash
curl -X POST "https://atomgpt.org/omim/gene_search" \
  -H "Content-Type: application/json" \
  -d '{"search": "BRCA1", "handler": "entry", "limit": 20}'
```

Also supports `preset` field: `brca_cancer, hemoglobin, collagen, ion_channel, metal_metabolism, kinase, crystallin, mitochondrial`.

### `GET /omim/gene_search` — API key auth

```bash
curl "https://atomgpt.org/omim/gene_search?search=hemoglobin&APIKEY=sk-XYZ"
```

---

### `POST /omim/entry` — Full entry by MIM number

```bash
curl -X POST "https://atomgpt.org/omim/entry" \
  -H "Content-Type: application/json" \
  -d '{"mimNumber": 113705}'
```

### `POST /omim/genemap` — Browse by chromosome

### `POST /omim/clinical_search` — Clinical synopsis search


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show omim gene explorer data")
print(response)
```

## References

- OMIM — Online Mendelian Inheritance in Man [:material-link: DOI](https://omim.org)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
