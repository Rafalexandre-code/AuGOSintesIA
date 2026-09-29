---
title: HEA Explorer
---

# HEA Explorer

High-Entropy Alloy design tool. Two endpoints: (1) Compute — calculates thermodynamic parameters (ΔS_mix, atomic size mismatch δ, VEC, Ω parameter, ΔH_mix approximation) from element composition with equiatomic or custom fractions, predicts FCC/BCC phase and solid solution likelihood via Hume-Rothery rules. (2) Screen — searches JARVIS-DFT for multi-element compositions matching the target elements. Built-in database of 47 elements with atomic radii, melting points, VEC, electronegativity, density, and elastic modulus.

[:material-open-in-new: Open App](https://atomgpt.org/hea){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **Built-in element property database** (47 elements) + **JARVIS dft_3d** (for composition screening).

## Endpoints

### `POST /hea/compute` — Compute HEA parameters

```bash
curl -X POST "https://atomgpt.org/hea/compute" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"elements": ["Ti", "V", "Cr", "Mn", "Fe"]}'
```

| Field | Type | Description |
|-------|------|-------------|
| `elements` | list[string] | 2–10 element symbols |
| `fractions` | list[float] | Optional molar fractions (default: equiatomic) |

**Response:** composition string, per-element properties, parameters (ΔS_mix, δ%, VEC, Ω, ΔH_mix, Tm_avg, ρ_avg, E_avg), predictions (FCC/BCC/mixed phase, solid solution likelihood, Hume-Rothery checks).

---

### `POST /hea/screen` — Screen JARVIS-DFT

```bash
curl -X POST "https://atomgpt.org/hea/screen" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"elements": ["Ti", "V", "Cr"], "require_all": true, "max_results": 50}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `elements` | list[string] | required | Target elements |
| `require_all` | bool | true | All elements must be present |
| `min_elements` | int | 2 | Minimum number of elements |
| `max_results` | int | 50 | Max results |


---

## Python Examples

=== "Compute HEA"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/hea/compute",
        headers={"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"},
        json={"elements": ["Ti", "V", "Cr", "Mn", "Fe"]},
    )
    data = response.json()
    p = data["parameters"]
    print(f"{data['composition']}: VEC={p['VEC']}, δ={p['delta_pct']}%, ΔS={p['delta_s_mix_R']}R")
    print(f"Phase: {data['predictions']['phase']}, SS likely: {data['predictions']['solid_solution_likely']}")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show hea explorer data")
print(response)
```

## References

- Y. Zhang et al., Mater. Today 19, 349 (2016) [:material-link: DOI](https://doi.org/10.1016/j.mattod.2015.11.026)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
