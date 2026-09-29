---
title: HardMat
---

# HardMat

Predict Vickers hardness (GPa and HV) from elastic moduli using 9 semi-empirical models (H1a–H5, Tian, Mazhnik-Oganov, Lyakhov-Oganov). Two tabs: (1) JARVIS-DFT lookup — fetches Kv, Gv, bandgap, density, spacegroup from dft_3d, applies CLA1/CLA2 smart model selection (Dovale-Farelo 2022 Tables 5&6). (2) ALIGNN — predicts Kv & Gv from POSCAR, then runs all 9 models. Built-in crystal system classification from space group number, bandgap class (metal/semiconductor/insulator), and density class (low/medium/high).

[:material-open-in-new: Open App](https://atomgpt.org/hardmat){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** (Tab 1) + **ALIGNN** (Tab 2). Smart model selection from Dovale-Farelo et al., Sci. Rep. 12, 22475 (2022).

## Endpoints

### `POST /hardmat/jarvis` — JARVIS-DFT lookup + predict

```bash
curl -X POST "https://atomgpt.org/hardmat/jarvis" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"jid": "JVASP-1002"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `jid` | string | JARVIS ID (exact match) |
| `formula` | string | Chemical formula (hill order; selects lowest-ehull entry with elastic data) |

**Response:** `jid, formula, K_GPa, G_GPa, Y_GPa, poisson, pugh_ratio, density, bandgap, spacegroup, ehull, crystal_system, bandgap_class, density_class, cla1_recommended, cla2_recommended, hardness_GPa` (9 models), `hardness_HV` (converted), `warnings`, `selection_note`.

---

### `POST /hardmat/alignn` — ALIGNN prediction from POSCAR

```bash
curl -X POST "https://atomgpt.org/hardmat/alignn" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"poscar": "System\n1.0\n3.26 0 0\n0 3.26 0\n0 0 3.26\nTi Au\n1 1\ndirect\n0.5 0.5 0.5 Ti\n0 0 0 Au"}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | VASP POSCAR string (max 50 atoms) |

**Response:** Same as JARVIS endpoint plus `alignn_props` (formation_energy, bandgap_mbj, supercon_tc).

**9 hardness models:** H1a (Jiang 2011), H1b (Jiang 2011), H2 (Teter 1998), H3 (Jiang 2010), H4 (Miao 2011), H5/Chen (2011), Tian (2012), Mazhnik-Oganov (2019), Lyakhov-Oganov (2011).


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show hardmat data")
print(response)
```

## References

- V. Dovale-Farelo et al., Sci. Rep. 12, 22475 (2022) [:material-link: DOI](https://doi.org/10.1038/s41598-022-27083-w)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
