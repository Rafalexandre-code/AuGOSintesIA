---
title: Convex Hull
---

# Convex Hull

Compute convex hull phase diagrams from JARVIS-DFT formation energies. Supports 2-element (binary 2D plot), 3-element (ternary triangle), and 4+-element (3D tetrahedron) systems. Based on `jarvis.analysis.thermodynamics.energetics.PhaseDiagram`. Returns hull vertices, simplices, and per-entry stability classification.

[:material-open-in-new: Open App](https://atomgpt.org/convexhull){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS dft_3d** — formation energies via `PhaseDiagram` from jarvis-tools.

## Endpoints

### `POST /convexhull/compute` — Compute phase diagram

```bash
curl -X POST "https://atomgpt.org/convexhull/compute" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"elements": "Ni-Al", "only_stable": false}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `elements` | string | required | Dash-separated elements (e.g. `Ni-Al`, `Ni-Al-O`) |
| `only_stable` | bool | false | Only plot hull-stable phases |

**Response varies by dimensionality:**

- **Binary (2 elements):** `plot_type: "2d"`, x (composition), e (energy), names, hull (bool array), simplices (line segments)
- **Ternary (3 elements):** `plot_type: "ternary"`, a/b (triangle coords), hull, simplices (triangles)
- **Quaternary+ (4+ elements):** `plot_type: "3d"`, a/b/c (tetrahedron coords), hull, simplices

All include `entries` array with formula, jid, energy, on_hull flag.


---

## Python Examples

=== "Binary hull"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/convexhull/compute",
        headers={"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"},
        json={"elements": "Ni-Al"},
    )
    data = response.json()
    stable = [e for e in data["entries"] if e["on_hull"]]
    print(f"Ni-Al system: {data['n_entries']} entries, {len(stable)} on hull")
    for s in stable:
        print(f"  {s['formula']}: {s['energy']:.3f} eV/atom")
    ```


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show convex hull data")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
