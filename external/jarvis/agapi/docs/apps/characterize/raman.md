---
title: Raman Suite
---

# Raman Suite

Three-tab Raman analysis platform: (1) spectrum matching against JARVIS ramandb (~5K materials), (2) RamanGPT AI-powered structure prediction from Raman peaks, and (3) ALIGNN-based Raman spectrum prediction from crystal structures.

[:material-open-in-new: Open App](https://atomgpt.org/raman){ .md-button .md-button--primary }

---

## Overview

The Raman Suite provides a complete workflow for Raman spectroscopy in materials science. Match experimental spectra to known materials via cosine similarity, predict crystal structures from Raman peaks using RamanGPT, or predict Raman spectra from POSCAR structures using ALIGNN (`jv_raman_alignn`). The ramandb contains ~5K materials with DFT-computed Raman tensors, cross-referenced with JARVIS-DFT JVASP IDs.

!!! info "Data Source"
    **ramandb** (~5K entries with DFT Raman tensors).
    **RamanGPT** model (`knc6/ramangpt_dft_model`) for AI structure prediction.
    **ALIGNN** (`jv_raman_alignn`) for ML Raman spectrum prediction.

## Endpoints

### `POST /raman/match` — Match spectrum against ramandb

Gaussian-broadens user spectrum and computes cosine similarity against all entries in ramandb. Optional formula filter narrows candidates.

```bash
curl -X POST "https://atomgpt.org/raman/match" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "frequencies": [135.2, 196.7, 221.3, 257.0, 418.3, 594.7, 650.1, 701.6, 705.6],
    "activities": [0.024, 0.006, 0.013, 0.091, 0.083, 0.340, 0.001, 1.000, 0.137],
    "formula": "SrTeO3",
    "sigma": 8.0,
    "top_n": 10,
    "freq_min": 0,
    "freq_max": 1200
  }'
```

Match without formula filter (search entire database):

```bash
curl -X POST "https://atomgpt.org/raman/match" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "frequencies": [520, 302, 960],
    "activities": [1.0, 0.02, 0.06],
    "formula": "",
    "sigma": 8.0,
    "top_n": 5
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `frequencies` | list[float] | required | Raman shift values (cm⁻¹) |
| `activities` | list[float] | required | Raman activity/intensity values |
| `formula` | string | `""` | Optional formula or element filter (e.g. `"Si"`, `"SrTeO3"`, `"Te,O"`) |
| `sigma` | float | 8.0 | Gaussian broadening width (cm⁻¹) |
| `top_n` | int | 10 | Number of top matches to return |
| `freq_min` | float | 0 | Minimum frequency for matching grid |
| `freq_max` | float | 1200 | Maximum frequency for matching grid |

**Response** includes `grid` (500-point x-axis), `user_spectrum` (broadened), and `matches` array with `id`, `formula`, `elements`, `similarity`, `n_active_modes`, `active_freqs`, `active_activities`, and `spectrum` (broadened reference).

---

### `POST /raman/lookup` — Look up a material's Raman spectrum by ID

```bash
curl -X POST "https://atomgpt.org/raman/lookup" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "material_id": "JVASP-1002"
  }'
```

Returns `freq_cm`, `raman_activity`, `formula`, and `elements` for the given material.

---

### `POST /raman/ramangpt` — AI structure prediction from Raman peaks

Given a chemical formula and Raman peak data, RamanGPT generates a crystal structure (POSCAR) that would produce the observed spectrum.

```bash
curl -X POST "https://atomgpt.org/raman/ramangpt" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "SrTeO3",
    "raman_data": "135.2  0.024\n196.7  0.006\n221.3  0.013\n257.0  0.091\n418.3  0.083\n594.7  0.340\n701.6  1.000",
    "max_new_tokens": 512
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | required | Chemical formula |
| `raman_data` | string | required | Frequency/intensity pairs, newline-separated |
| `max_new_tokens` | int | 512 | Max generation tokens |

**Response** includes `poscar`, `structure` (formula, spacegroup, num_atoms), `raw_output`, `prompt`, `peak_text`, `inference_time`.

---

### `GET /ramangpt/query` — Direct RamanGPT prediction (GET)

```bash
curl "https://atomgpt.org/ramangpt/query?formula=SrTeO3&peaks=135.2cm-1(0.024),257.0cm-1(0.091),701.6cm-1(1.000)&max_new_tokens=512" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

| Param | Description |
|-------|-------------|
| `formula` | Chemical formula |
| `peaks` | Peaks as `freq_cm-1(intensity)` comma-separated |
| `max_new_tokens` | Max generation tokens (default 512) |

Returns plain-text POSCAR of the predicted structure.

---

### `POST /raman/alignn` — Predict Raman spectrum from POSCAR

Uses the ALIGNN `jv_raman_alignn` model to predict a 200-point Raman spectrum (50–1000 cm⁻¹) from a crystal structure.

```bash
curl -X POST "https://atomgpt.org/raman/alignn" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si2\n1.0\n3.364 0.0 1.942\n1.121 3.172 1.942\n0.0 0.0 3.885\nSi\n2\nCartesian\n3.925 2.775 6.798\n0.561 0.396 0.971"
  }'
```

**Response** includes `x_axis` (200 points, 50–1000 cm⁻¹), `y_axis`, `y_normalized`, `peaks` (top 20 with freq/intensity/normalized), `formula`, `spacegroup`, `lattice`, `inference_time`.

---

## Python Examples

=== "Match spectrum"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/raman/match",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "frequencies": [135.2, 257.0, 418.3, 594.7, 701.6],
            "activities": [0.024, 0.091, 0.083, 0.340, 1.000],
            "formula": "SrTeO3",
            "sigma": 8.0,
            "top_n": 5,
        },
    )
    data = response.json()
    for m in data["matches"]:
        print(f"{m['id']:12s} {m['formula']:10s} sim={m['similarity']:.3f}")
    ```

=== "RamanGPT"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/raman/ramangpt",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "formula": "SrTeO3",
            "raman_data": "135.2  0.024\n257.0  0.091\n701.6  1.000",
            "max_new_tokens": 512,
        },
    )
    data = response.json()
    if data["success"]:
        print(f"Formula: {data['structure']['formula']}")
        print(f"Spacegroup: {data['structure']['spacegroup']}")
        print(f"POSCAR:\n{data['poscar'][:300]}")
    ```

=== "ALIGNN Raman"

    ```python
    import requests

    SI_POSCAR = """Si2
    1.0
    3.364 0.0 1.942
    1.121 3.172 1.942
    0.0 0.0 3.885
    Si
    2
    Cartesian
    3.925 2.775 6.798
    0.561 0.396 0.971"""

    response = requests.post(
        "https://atomgpt.org/raman/alignn",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": SI_POSCAR},
    )
    data = response.json()
    if data["success"]:
        print(f"Formula: {data['formula']}, Peaks: {data['n_peaks']}")
        for p in data["peaks"][:5]:
            print(f"  {p['freq']} cm-1  intensity={p['intensity']:.4e}")
    ```

=== "Lookup by ID"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/raman/lookup",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"material_id": "JVASP-1002"},
    )
    data = response.json()
    if data["success"]:
        print(f"Formula: {data['formula']}")
        for f, a in zip(data["freq_cm"], data["raman_activity"]):
            print(f"  {f:.1f} cm-1  activity={a:.4f}")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Match a spectrum
response = agent.query_sync("Match Raman spectrum for SrTeO3: 135 0.02, 257 0.09, 702 1.0")
print(response)

# Predict structure from Raman
response = agent.query_sync("Use RamanGPT to predict the structure of TiO2 from Raman peaks at 144, 399, 639 cm-1")
print(response)

# Predict Raman from structure
response = agent.query_sync("Predict the Raman spectrum of JVASP-1002 using ALIGNN")
print(response)
```

## References

- Computational Raman Database [:material-link: DOI](https://ramandb.oulu.fi/)
- npj Comp. Mat. 7, 185 (2021) — ALIGNN [:material-link: DOI](https://doi.org/10.1038/s41524-021-00650-1)
- [atomgptlab/atomgpt](https://github.com/atomgptlab/atomgpt)
