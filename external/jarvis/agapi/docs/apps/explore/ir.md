---
title: IR Spectra Explorer
---

# IR Spectra Explorer

Visualize and compare infrared (IR) intensity spectra from JARVIS-DFT DFPT calculations. Returns raw peaks (frequency, intensity pairs) plus Gaussian-broadened spectra (σ=10 cm⁻¹, 500-point grid). Data parsed from JARVIS XML `<ir_intensity>` section.

[:material-open-in-new: Open App](https://atomgpt.org/ir){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **JARVIS-DFT** — IR intensity from DFPT, parsed from JARVIS XML (`<ir_intensity>` tag).

## Endpoints

### `POST /ir/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/ir/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"formula": "Si"}'
```

Standard search fields: `formula`, `jid`, `elements`, `element_mode` (any/all/exact), `bandgap_min`, `bandgap_max`, `spacegroup`. Max 500 results.

!!! note
    Pre-filtered to materials with `max_ir_mode != 'na'`.

---

### `GET /ir/data/{jid}` — Fetch IR peaks and Gaussian-broadened spectrum.

```bash
curl "https://atomgpt.org/ir/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-5741",
  "formula": "AlN",
  "bandgap": 4.04,
  "peaks": [{"frequency": 512.97, "intensity": 1.31}, {"frequency": 532.99, "intensity": 0.85}],
  "gaussian_x": [480.0, 480.2, ...],
  "gaussian_y": [0.0, 0.001, ...],
  "max_ir_mode": 532.99,
  "min_ir_mode": 512.97
}
```

Raw peaks from XML `freq1,freq2,...;intensity1,intensity2,...` format. Gaussian broadening applied with σ=10 cm⁻¹ on a 500-point grid spanning ±5σ around the frequency range. Active modes are those with |intensity| > 1e-20.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/ir/search",
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
        "https://atomgpt.org/ir/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    active = [p for p in data["peaks"] if abs(p["intensity"]) > 1e-10]
    print(f"{data['formula']} — {len(active)} active IR modes")
    for p in active[:5]:
        print(f"  {p['frequency']:.1f} cm⁻¹: intensity={p['intensity']:.4f}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show ir spectra explorer for Silicon")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 1 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-0337-2)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
