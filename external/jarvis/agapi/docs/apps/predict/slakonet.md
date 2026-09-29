---
title: SlakoNet Bands
---

# SlakoNet Bands

Deep learning tight-binding electronic structure calculator. Three tabs: (1) Band Structure + DOS — high-symmetry path band diagram with atom-projected DOS, (2) 3D Band Surface — interactive kx-ky energy surface with BZ overlay and Fermi plane, (3) Fermi Surface — 2D contour plots, 3D near-Fermi bands, and true 3D Fermi isosurfaces via marching cubes. All powered by SlakoNet neural network Slater-Koster parameters.

[:material-open-in-new: Open App](https://atomgpt.org/slakonet){ .md-button .md-button--primary }

---

## Overview

SlakoNet predicts Slater-Koster tight-binding parameters using a deep learning model, enabling rapid electronic band structure and density of states calculations without DFT. The model supports elements up to Z=85 and handles multi-element systems. Max 50 atoms for band structure, max 20 atoms for 3D Fermi isosurface (due to N³ k-mesh cost).

!!! info "Data Source"
    **SlakoNet** pretrained model — neural network Slater-Koster parameters from `slakonet.predict_slakonet`.

## Endpoints

### `GET /slakonet/bandstructure` — Band structure image (API key)

Returns a PNG image of the band structure + DOS along the high-symmetry path. Band gap, VBM, and CBM are in response headers.

```bash
curl "https://atomgpt.org/slakonet/bandstructure?jid=JVASP-1002&energy_range_min=-8&energy_range_max=8&APIKEY=sk-XYZ" \
  --output bandstructure_Si.png
```

With POSCAR string:

```bash
curl "https://atomgpt.org/slakonet/bandstructure?poscar=MgB2%0A1.0%0A1.537%20-2.662%200.0%0A1.537%202.662%200.0%0A0.0%200.0%203.515%0AMg%20B%0A1%202%0ACartesian%0A0.0%200.0%200.0%0A1.537%20-0.887%201.757%0A1.537%200.887%201.757&APIKEY=sk-XYZ" \
  --output bandstructure_MgB2.png
```

| Param | Description |
|-------|-------------|
| `jid` | JARVIS ID — provide `jid` OR `poscar` |
| `poscar` | URL-encoded POSCAR string |
| `energy_range_min` | Energy axis min (default -8 eV) |
| `energy_range_max` | Energy axis max (default 8 eV) |
| `APIKEY` | API key |

Returns `image/png` with headers: `X-Band-Gap`, `X-VBM`, `X-CBM`, `X-Formula`.

---

### `POST /slakonet/web_analyze` — Band structure + DOS (JSON)

Returns band gap, VBM, CBM, base64 plot, and full band data (eigenvalues, DOS, atom-projected DOS) as JSON.

```bash
curl -X POST "https://atomgpt.org/slakonet/web_analyze" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "MgB2\n1.0\n1.537 -2.662 0.0\n1.537 2.662 0.0\n0.0 0.0 3.515\nMg B\n1 2\nCartesian\n0.0 0.0 0.0\n1.537 -0.887 1.757\n1.537 0.887 1.757",
    "energy_range_min": -8,
    "energy_range_max": 8
  }'
```

**Response** includes `band_gap`, `vbm`, `cbm`, `plot_base64` (PNG), `formula`, `num_atoms`, and `band_data` (eigenvalues, dos_energies, dos_values, atom_pdos).

---

### `POST /slakonet/bandstructure3d` — 3D band surface (kx-ky plane)

Compute band energies on a 2D Cartesian k-mesh at kz=0 for interactive 3D Plotly surface plots.

```bash
curl -X POST "https://atomgpt.org/slakonet/bandstructure3d" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "MgB2\n1.0\n1.537 -2.662 0.0\n1.537 2.662 0.0\n0.0 0.0 3.515\nMg B\n1 2\nCartesian\n0.0 0.0 0.0\n1.537 -0.887 1.757\n1.537 0.887 1.757",
    "nk_per_dim": 30
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | POSCAR (max 50 atoms) |
| `nk_per_dim` | int | 30 | k-points per axis (10–60) |

**Response** includes `kx_grid`, `ky_grid`, `bands` (one 2D array per band), `bz_x`/`bz_y` (BZ outline), `bandgap`, `nbands`.

---

### `POST /slakonet/fermisurface` — 2D Fermi surface

Compute 2D Fermi contours at kz=0. Returns band energies on k-mesh, Fermi-crossing band indices, BZ outline, and high-symmetry point coordinates (Γ, K, K', M).

```bash
curl -X POST "https://atomgpt.org/slakonet/fermisurface" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "MgB2\n1.0\n1.537 -2.662 0.0\n1.537 2.662 0.0\n0.0 0.0 3.515\nMg B\n1 2\nCartesian\n0.0 0.0 0.0\n1.537 -0.887 1.757\n1.537 0.887 1.757",
    "nk_per_dim": 40,
    "energy_window": 0.5
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | POSCAR (max 50 atoms) |
| `nk_per_dim` | int | 40 | k-points per axis (10–60) |
| `energy_window` | float | 0.5 | Energy window around E_F for identifying Fermi bands (eV) |

**Response** includes `fermi_bands` (indices), `band_info` (per-band min/max/crosses_ef), `kx_1d`/`ky_1d`/`kx_grid`/`ky_grid`, `bands`, `high_sym` (Γ/K/K'/M coordinates).

---

### `POST /slakonet/fermisurface3d` — 3D Fermi isosurface (marching cubes)

Compute a true 3D Fermi isosurface on a full kx-ky-kz mesh using marching cubes (`skimage.measure.marching_cubes`). Returns mesh vertices and faces for Plotly Mesh3d rendering. Computationally heavy — max 20 atoms, max 35³ k-points.

```bash
curl -X POST "https://atomgpt.org/slakonet/fermisurface3d" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "MgB2\n1.0\n1.537 -2.662 0.0\n1.537 2.662 0.0\n0.0 0.0 3.515\nMg B\n1 2\nCartesian\n0.0 0.0 0.0\n1.537 -0.887 1.757\n1.537 0.887 1.757",
    "nk_per_dim": 20,
    "energy_window": 0.5
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | POSCAR (max **20** atoms) |
| `nk_per_dim` | int | 20 | k-points per axis (8–35, i.e. max 35³ = 42,875 k-points) |
| `energy_window` | float | 0.5 | Energy window for Fermi band identification (eV) |

**Response** includes `meshes` (per-band: `vertices_x/y/z`, `faces_i/j/k` for Mesh3d), `fermi_bands`, `band_info`, `bz_x`/`bz_y`.

---

## Python Examples

=== "Band structure by JID"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/slakonet/bandstructure",
        headers={"accept": "image/png"},
        params={
            "jid": "JVASP-1002",
            "energy_range_min": -8,
            "energy_range_max": 8,
            "APIKEY": "sk-XYZ",
        },
    )
    with open("bandstructure_Si.png", "wb") as f:
        f.write(response.content)
    print(f"Band gap: {response.headers.get('X-Band-Gap')} eV")
    ```

=== "Web analyze (JSON)"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/slakonet/web_analyze",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={"poscar": open("POSCAR").read()},
    )
    data = response.json()
    print(f"Band gap: {data['band_gap']:.3f} eV")
    print(f"VBM: {data['vbm']:.3f}, CBM: {data['cbm']:.3f} eV")

    # Save plot
    import base64
    with open("bands.png", "wb") as f:
        f.write(base64.b64decode(data["plot_base64"]))
    ```

=== "3D band surface"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/slakonet/bandstructure3d",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={"poscar": open("POSCAR").read(), "nk_per_dim": 30},
    )
    data = response.json()
    print(f"Bands: {data['nbands']}, Gap: {data['bandgap']:.3f} eV")
    print(f"K-mesh: {data['nk']}×{data['nky']}")
    ```

=== "Fermi surface"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/slakonet/fermisurface",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("MgB2.vasp").read(),
            "nk_per_dim": 40,
            "energy_window": 0.5,
        },
    )
    data = response.json()
    print(f"Fermi bands: {data['fermi_bands']}")
    print(f"Band gap: {data['bandgap']:.3f} eV")
    hs = data["high_sym"]
    print(f"Γ={hs['Gamma']}, K={hs['K']}, M={hs['M']}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Band structure
response = agent.query_sync("Compute the SlakoNet band structure for MgB2")
print(response)

# Fermi surface
response = agent.query_sync("Show the Fermi surface of MgB2 using SlakoNet")
print(response)
```

## References

- K. Choudhary, J. Phys. Chem. Lett. 16, 11109 (2025) — SlakoNet [:material-link: DOI](https://doi.org/10.1021/acs.jpclett.5c02456)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/slakonet](https://github.com/atomgptlab/slakonet)
