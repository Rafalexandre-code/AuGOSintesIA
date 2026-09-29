---
title: Polymer Chain Builder
---

# Polymer Chain Builder

Build statistical polymer chains using 4 models: FJC (Freely Jointed Chain with optional angle constraint), FRC (Freely Rotating Chain), WLC (Worm-Like Chain), and RIS (Rotational Isomeric State). Computes chain statistics (Ree, Rg, C∞, persistence length, overlap concentration), supports monomer XYZ upload for full-atom visualization, batch sampling for distributions, and bulk periodic box generation with LAMMPS topology export. Adapted from polybuildv4.f (K. Choudhary, JHU/NIST).

[:material-open-in-new: Open App](https://atomgpt.org/polymer_builder){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    Client-side 3D visualization + server-side chain generation. No external databases.

## Endpoints

### `POST /polymer_builder/generate` — Generate single chain

```bash
curl -X POST "https://atomgpt.org/polymer_builder/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "model=FJC" -F "N=100" -F "b=1.5" -F "seed=42"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model` | string | FJC | Chain model: FJC, FRC, WLC, RIS |
| `N` | int | 100 | Chain length (monomers) |
| `b` | float | 1.5 | Bond length (Å) |
| `theta` | float | 109.5 | Bond angle (°, FRC/RIS) |
| `Lp` | float | 10.0 | Persistence length (Å, WLC) |
| `T` | float | 300.0 | Temperature (K, RIS) |
| `seed` | int | 42 | Random seed |
| `cos_min` | float | -1.0 | Angle constraint for FJC (-1=off) |
| `mw_monomer` | float | 0 | Monomer molecular weight (g/mol) |
| `xyz_string` | string | null | Monomer XYZ (optional) |

**Response:** `pts` (backbone coordinates), `stats` (Ree, Rg, L, C_inf, Lp_eff, c_star_mg_mL, bulk_density), `mono` info.

---

### `POST /polymer_builder/sample` — Batch sample distributions

Returns Ree/Rg arrays for up to 500 chains.

### `POST /polymer_builder/export` — Export chain (XYZ/PDB/ZIP/LAMMPS)

### `POST /polymer_builder/bulk` — Build periodic bulk box (up to 200 chains, LAMMPS topology)


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show polymer chain builder data")
print(response)
```

## References

- P.J. Flory, Statistical Mechanics of Chain Molecules (1969) [:material-link: DOI](https://doi.org/10.1002/9780470316566)
- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
