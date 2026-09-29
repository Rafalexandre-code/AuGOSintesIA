---
title: Reaction Network
---

# Reaction Network

Three-endpoint chemistry toolkit: (1) Balance — balances chemical equations using SVD null-space method. (2) Thermodynamics — computes reaction enthalpy ΔH from JARVIS-DFT formation energies with per-species energy breakdown. (3) Network — builds bipartite reaction network graphs (species ↔ reaction nodes) from a list of equations.

[:material-open-in-new: Open App](https://atomgpt.org/reaction_network){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** — formation energies (OptB88vdW) mapped by formula, with diatomic aliases (O₂→O, N₂→N, etc.).

## Endpoints

### `POST /reaction_network/balance` — Balance equation

```bash
curl -X POST "https://atomgpt.org/reaction_network/balance" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"reactants": "Fe2O3 + C", "products": "Fe + CO2"}'
```

Returns `react_coeffs`, `prod_coeffs`, `balanced` (bool), element counts for verification.

---

### `POST /reaction_network/thermodynamics` — Reaction ΔH

```bash
curl -X POST "https://atomgpt.org/reaction_network/thermodynamics" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"reactants": ["SrO", "TiO2"], "products": ["SrTiO3"], "react_coeffs": [1, 1], "prod_coeffs": [1]}'
```

Returns per-species formation energy (from JARVIS-DFT), total energies, `delta_h`, `feasible` (exothermic if ΔH < 0). Includes diatomic aliases (O₂→O, N₂→N).

---

### `POST /reaction_network/network` — Build reaction graph

```bash
curl -X POST "https://atomgpt.org/reaction_network/network" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"reactions": ["H2 + O2 -> H2O", "CH4 + 2O2 -> CO2 + 2H2O"]}'
```

Returns `nodes` (species + reaction), `edges` (with coefficients), for d3.js bipartite graph rendering.


---

## Python Examples

=== "Balance + ΔH"

    ```python
    import requests
    H = {"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"}

    # Balance
    r = requests.post("https://atomgpt.org/reaction_network/balance", headers=H,
        json={"reactants": "Fe2O3 + C", "products": "Fe + CO2"})
    b = r.json()
    print(f"Balanced: {b['react_coeffs']} -> {b['prod_coeffs']}")

    # Thermodynamics
    r = requests.post("https://atomgpt.org/reaction_network/thermodynamics", headers=H,
        json={"reactants": ["SrO", "TiO2"], "products": ["SrTiO3"]})
    t = r.json()
    print(f"ΔH = {t['delta_h']} eV, Feasible: {t['feasible']}")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show reaction network data")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
