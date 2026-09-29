---
title: Python Client
---

# Python Client

The `agapi` package provides both direct function calls and a natural language agent interface.

```bash
pip install agapi jarvis-tools scipy httpx
```

## Client Setup

```python
import os
from agapi.agents.client import AGAPIClient

client = AGAPIClient(api_key=os.environ.get("AGAPI_KEY"))
```

## Available Functions

### Database Queries

| Function | Description | Example |
|----------|-------------|---------|
| `query_by_formula(formula, client)` | Search by chemical formula | `query_by_formula("Si", client)` |
| `query_by_jid(jid, client)` | Fetch by JARVIS ID | `query_by_jid("JVASP-1002", client)` |
| `query_by_elements(elements, client)` | Filter by elements | `query_by_elements("Si", client)` |
| `query_by_property(prop, min, max, ...)` | Filter by property range | `query_by_property("bandgap", 0.1, 3.0, elements="Si", api_client=client)` |
| `find_extreme(prop, is_max, ...)` | Find max/min property material | `find_extreme("bulk modulus", True, elements="Si", api_client=client)` |
| `list_jarvis_columns()` | List available properties | `list_jarvis_columns()` |

### AI Predictions

| Function | Description |
|----------|-------------|
| `alignn_predict(jid, api_client)` | GNN property prediction (50+ properties) |
| `alignn_ff_relax(poscar, api_client)` | Structure relaxation with ALIGNN-FF |
| `alignn_ff_single_point(poscar, api_client)` | Single-point energy calculation |
| `alignn_ff_optimize(poscar, api_client)` | Geometry optimization |
| `alignn_ff_md(poscar, api_client)` | Molecular dynamics simulation |
| `slakonet_bandstructure(poscar, api_client)` | Tight-binding band structure |

### Structure Manipulation (Local, No API Key Needed)

| Function | Description |
|----------|-------------|
| `make_supercell(poscar, dims)` | Build supercell |
| `substitute_atom(poscar, old, new, count)` | Atomic substitution |
| `create_vacancy(poscar, element, count)` | Vacancy creation |
| `generate_xrd_pattern(poscar)` | Simulated powder XRD |
| `generate_interface(poscar1, poscar2, api_client)` | Heterostructure interface |

### Characterization

| Function | Description |
|----------|-------------|
| `pxrd_match(formula, xrd_data, api_client)` | Match XRD pattern to structure |
| `xrd_analyze(formula, xrd_data, api_client)` | Analyze XRD data |
| `diffractgpt_predict(formula, peaks, client)` | AI XRD interpretation |
| `microscopygpt_analyze(description, api_client)` | AI STEM/TEM analysis |

### Literature & External

| Function | Description |
|----------|-------------|
| `search_arxiv(query, max_results, api_client)` | Search arXiv papers |
| `search_crossref(query, rows, api_client)` | Search Crossref publications |
| `query_mp(formula)` | Query Materials Project |
| `query_oqmd(formula)` | Query OQMD |
| `protein_fold(sequence, api_client)` | Protein structure prediction |
| `openfold_predict(sequence, api_client)` | OpenFold prediction |

## Common Input Formats

### POSCAR String

```python
SI_PRIM = """Si
1.0
0 2.734 2.734
2.734 0 2.734
2.734 2.734 0
Si
2
direct
0 0 0
0.25 0.25 0.25
"""
```

### XRD Data

```python
SI_XRD = """28.44 1.00
47.30 0.55
56.12 0.30
"""
```

## Usage Examples

### Search → Predict → Relax Pipeline

```python
from agapi.agents.functions import *

# 1. Find material
r = query_by_formula("GaN", client)
jid = r["materials"][0]["jid"]

# 2. Get structure
r = query_by_jid(jid, client)
poscar = r["POSCAR"]

# 3. Predict properties
r = alignn_predict(jid=jid, api_client=client)

# 4. Relax with force field
r = alignn_ff_relax(poscar, api_client=client)

# 5. Generate XRD
r = generate_xrd_pattern(poscar)
```

### Structure Manipulation

```python
# Supercell
r = make_supercell(SI_PRIM, [2, 2, 1])
print(f"Atoms: {r['original_atoms']} → {r['supercell_atoms']}")

# Substitution
r = substitute_atom(GAAS_PRIM, "Ga", "Al", 1)
print(f"New formula: {r['new_formula']}")  # AlAs

# Vacancy
r = create_vacancy(GAAS_PRIM, "Ga", 1)
print(f"Atoms: {r['original_atoms']} → {r['new_atoms']}")
```
