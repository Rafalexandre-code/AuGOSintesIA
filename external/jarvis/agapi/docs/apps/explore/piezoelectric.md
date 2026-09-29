---
title: Piezoelectric Explorer
---

# Piezoelectric Explorer

Visualize and compare DFPT piezoelectric stress tensors eij (3×6 Voigt, C/m²) and IR intensity spectra from JARVIS-DFT. Data parsed from JARVIS XML `<dfpt_piezoelectric_tensor>` and `<ir_intensity>` sections.

[:material-open-in-new: Open App](https://atomgpt.org/piezoelectric){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS-DFT** — DFPT piezoelectric tensor and IR intensity from JARVIS XML.

## Endpoints

### `POST /piezoelectric/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/piezoelectric/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

Standard search fields: `formula`, `jid`, `elements`, `element_mode` (any/all/exact), `bandgap_min`, `bandgap_max`, `spacegroup`. Max 500 results.

!!! note
    Pre-filtered to materials with `dfpt_piezo_max_eij != 'na'`.

---

### `GET /piezoelectric/data/{jid}` — Fetch 3×6 piezoelectric stress tensor and IR intensity spectrum.

```bash
curl "https://atomgpt.org/piezoelectric/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-5741",
  "formula": "AlN",
  "bandgap": 4.04,
  "max_piezo": 1.04,
  "piezo_tensor": [[e11,e12,e13,e14,e15,e16], [e21,...], [e31,...]],
  "ir": {"frequencies": [512.97, 532.99, ...], "intensities": [1.31, 0.85, ...]},
  "max_ir_mode": 532.99,
  "min_ir_mode": 512.97
}
```

Piezo tensor is 3×6 (3 Cartesian directions × 6 Voigt strain components). XML format: 6 columns separated by commas, each column has 3 rows separated by semicolons. IR format: `freq1,freq2,...;intensity1,intensity2,...`. Returns both tensor and IR when available.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/piezoelectric/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"formula": "Si"},
    )
    data = response.json()
    print(f"Found {data['total']} entries")
    for m in data["results"][:5]:
        print(f"  {m['jid']}: {m.get('formula', m.get('bulk_formula', ''))}")
    ```

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/piezoelectric/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — max piezo: {data['max_piezo']} C/m²")
    if data["piezo_tensor"]:
        import numpy as np
        t = np.array(data["piezo_tensor"])
        print(f"  Tensor shape: {t.shape}, max |eij|: {np.abs(t).max():.3f}")
    if data["ir"]:
        print(f"  IR modes: {len(data['ir']['frequencies'])}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show piezoelectric explorer for Silicon")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 1 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-0337-2)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
