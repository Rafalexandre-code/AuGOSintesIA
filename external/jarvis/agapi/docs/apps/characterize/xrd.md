---
title: XRD / DiffractGPT
---

# XRD / DiffractGPT

XRD analysis suite: simulate powder XRD patterns from crystal structures, match experimental data to JARVIS-DFT and COD, Rietveld-style refinement, AI-powered structure prediction via DiffractGPT, and optional ALIGNN/SlakoNet property predictions on structures.

[:material-open-in-new: Open App](https://atomgpt.org/xrd){ .md-button .md-button--primary }

---

## Overview

The XRD app provides a full pipeline from experimental diffraction data to crystal structure identification and property prediction. Three analysis methods are available: cosine-similarity pattern matching against JARVIS-DFT + COD databases, AI-powered structure generation via DiffractGPT, and Rietveld refinement via DARA. Results include best-match POSCAR, similarity scores, overlay plots, and optional ALIGNN/SlakoNet predictions.

!!! info "Data Source"
    **dft_3d** (76K materials) + **COD** (Crystallography Open Database) for pattern matching.
    **DiffractGPT** model for AI structure prediction from peaks.

## Endpoints

### `POST /xrd/analyze` — Match XRD pattern to structures

```bash
curl -X POST "https://atomgpt.org/xrd/analyze" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si",
    "xrd_data": "28.44 1.00\n47.30 0.55\n56.12 0.30\n69.13 0.06\n76.38 0.11",
    "wavelength": 1.54184,
    "method": "pattern_matching",
    "interval": 0.1,
    "x_range_min": 0.0,
    "x_range_max": 90.0
  }'
```

**Options for `method`:** `"pattern_matching"` (default), `"diffractgpt"`, or `"both"`.

Use DiffractGPT:

```bash
curl -X POST "https://atomgpt.org/xrd/analyze" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "LaB6",
    "xrd_data": "21.36 1.00\n30.39 0.64\n37.44 0.31\n43.51 0.20",
    "method": "diffractgpt"
  }'
```

Run both methods:

```bash
curl -X POST "https://atomgpt.org/xrd/analyze" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "SrTiO3",
    "xrd_data": "22.75 0.30\n32.40 1.00\n39.95 0.45\n46.47 0.60\n57.79 0.25",
    "method": "both"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | required | Chemical formula (e.g. `"Si"`, `"LaB6"`, `"SrTiO3"`) |
| `xrd_data` | string | required | `2theta intensity` pairs, newline-separated |
| `wavelength` | float | 1.54184 | X-ray wavelength in Å (Cu Kα) |
| `method` | string | `"pattern_matching"` | `"pattern_matching"`, `"diffractgpt"`, or `"both"` |
| `interval` | float | 0.1 | 2θ interpolation step (degrees) |
| `x_range_min` | float | 0.0 | Minimum 2θ range |
| `x_range_max` | float | 90.0 | Maximum 2θ range |

---

### `POST /xrd/analyze_with_refinement` — Full pipeline with Rietveld + ALIGNN

```bash
curl -X POST "https://atomgpt.org/xrd/analyze_with_refinement" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si",
    "xrd_data": "28.44 1.00\n47.30 0.55\n56.12 0.30",
    "wavelength": 1.54184,
    "method": "both",
    "run_refinement": true,
    "run_alignn": true,
    "run_slakonet": false
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | required | Chemical formula |
| `xrd_data` | string | required | 2θ/intensity data |
| `wavelength` | float | 1.54184 | X-ray wavelength (Å) |
| `method` | string | `"pattern_matching"` | `"pattern_matching"`, `"diffractgpt"`, or `"both"` |
| `run_refinement` | bool | `true` | Run Rietveld refinement on best match |
| `run_alignn` | bool | `false` | Predict properties with ALIGNN on matched structure |
| `run_slakonet` | bool | `false` | Compute band structure with SlakoNet |
| `best_match_poscar` | string | `""` | Override starting structure for refinement |

Pipeline steps: (1) Pattern matching → (2) DiffractGPT → (3) Rietveld refinement → (4) ALIGNN/SlakoNet predictions.

---

### `POST /xrd/generate` — Generate XRD from POSCAR

```bash
curl -X POST "https://atomgpt.org/xrd/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n0 2.734 2.734\n2.734 0 2.734\n2.734 2.734 0\nSi\n2\ndirect\n0 0 0\n0.25 0.25 0.25",
    "wavelength": 1.54184
  }'
```

Returns `two_thetas`, `d_hkls`, `intensities` (normalized to 100), formula, spacegroup, lattice parameters.

---

### `GET /diffractgpt/query` — Direct DiffractGPT prediction

```bash
curl "https://atomgpt.org/diffractgpt/query?formula=Si&peaks=28.4(1.0),47.3(0.55),56.1(0.30)&max_new_tokens=456" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

| Param | Description |
|-------|-------------|
| `formula` | Chemical formula |
| `peaks` | Peaks as `2theta(intensity)` comma-separated |
| `max_new_tokens` | Max generation tokens (default 456) |

Returns plain-text POSCAR of the predicted structure.

---

### `GET /pxrd/query` — Legacy PXRD pattern matching

```bash
curl "https://atomgpt.org/pxrd/query?pattern=Si%0A28.44%201.00%0A47.30%200.55%0A56.12%200.30&intvl=0.1&x_min=0&x_max=90" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

Pattern format: first line = formula, subsequent lines = `2theta intensity`. URL-encode newlines as `%0A`.

---

### `POST /xrd/poscar_to_xyz` — Convert POSCAR to XYZ

```bash
curl -X POST "https://atomgpt.org/xrd/poscar_to_xyz" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{"poscar": "Si\n1.0\n0 2.734 2.734\n2.734 0 2.734\n2.734 2.734 0\nSi\n2\ndirect\n0 0 0\n0.25 0.25 0.25"}'
```

---

## Python Example

```python
import requests

response = requests.post(
    "https://atomgpt.org/xrd/analyze",
    headers={
        "Authorization": "Bearer sk-XYZ",
        "accept": "application/json",
        "Content-Type": "application/json",
    },
    json={
        "formula": "Si",
        "xrd_data": "28.44 1.00\n47.30 0.55\n56.12 0.30",
        "method": "both",
    },
)
data = response.json()

# Pattern matching result
pm = data.get("pattern_matching", {})
if pm.get("success"):
    best = pm["best_match"]
    print(f"Best match: {best['jid']} ({best['formula']})")
    print(f"Similarity: {best['similarity']*100:.1f}%")
    print(f"POSCAR:\n{best['poscar'][:200]}")

# DiffractGPT result
dg = data.get("diffractgpt", {})
if dg.get("success"):
    s = dg["structure"]
    print(f"DiffractGPT: {s['formula']} ({s['spacegroup']})")
    print(f"Similarity: {s['similarity']*100:.1f}%")
```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Match this XRD pattern for Silicon: 28.44 1.00, 47.30 0.55, 56.12 0.30")
print(response)
```

## Reference

- J. Phys. Chem. Lett. 16, 2110 (2025) — DiffractGPT [:material-link: DOI](https://pubs.acs.org/doi/10.1021/acs.jpclett.4c03137)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis/blob/master/jarvis/analysis/diffraction/xrd.py)
- [atomgptlab/agapi](https://github.com/atomgptlab/agapi)
