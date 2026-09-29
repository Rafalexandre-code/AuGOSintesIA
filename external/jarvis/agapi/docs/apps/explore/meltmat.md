---
title: MeltMat
---

# MeltMat

Predict melting temperature (K) from elastic moduli using 5 models: Varshni/Gilvarry shear scaling, Vočadlo–Alfè empirical fit, Linear K (Stassis), Linear G power law, and Pugh-ratio-corrected Varshni. Also computes Debye temperature from sound velocities. Two tabs: JARVIS-DFT lookup and ALIGNN prediction from POSCAR.

[:material-open-in-new: Open App](https://atomgpt.org/meltmat){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** (Tab 1) + **ALIGNN** (Tab 2). Debye temperature from Voigt-averaged moduli.

## Endpoints

### `POST /meltmat/jarvis` — JARVIS-DFT lookup + predict Tm

```bash
curl -X POST "https://atomgpt.org/meltmat/jarvis" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"jid": "JVASP-1002"}'
```

| Field | Type | Description |
|-------|------|-------------|
| `jid` | string | JARVIS ID |
| `formula` | string | Chemical formula (selects lowest-ehull entry with elastic data) |
| `density_override` | float | Optional density override (g/cm³) |
| `mass_override` | float | Optional average atomic mass override (amu) |

**Response:** `jid, formula, K_GPa, G_GPa, density, avg_mass, vol_per_atom, theta_D` (Debye temp), `models` (5 Tm predictions in K), `spacegroup, ehull, bandgap`.

---

### `POST /meltmat/alignn` — ALIGNN prediction from POSCAR

```bash
curl -X POST "https://atomgpt.org/meltmat/alignn" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"poscar": "...", "density_override": null}'
```

**5 melting temperature models:** Varshni (Tm ∝ G·V^(1/3)), Vočadlo–Alfè (Tm ≈ 80·G^0.56), Linear K (354 + 4.5·K), Linear G (6.3·G^0.6), Pugh-corrected Varshni.


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show meltmat data")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
