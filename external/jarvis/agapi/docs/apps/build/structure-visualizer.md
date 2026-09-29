---
title: Structure Visualizer
---

# Structure Visualizer

Interactive 3D crystal structure viewer and manipulator. Load structures from POSCAR, CIF, XYZ, or PDB format. Build supercells, create surfaces with vacuum, introduce vacancies and substitutions, convert between primitive and conventional cells, and generate XRD patterns. All transformations return updated POSCAR, XYZ (for 3Dmol rendering), and structural info (formula, space group, volume, density).

[:material-open-in-new: Open App](https://atomgpt.org/structure_visualizer){ .md-button .md-button--primary }

---

## Overview

The Structure Visualizer provides a full suite of crystal structure manipulation tools in the browser with a 3Dmol.js interactive viewer. Each operation takes a POSCAR input, applies the transformation server-side using jarvis-tools, and returns the modified structure with updated metadata. Max 500 atoms per structure. Supported input formats: POSCAR, CIF, XYZ, PDB.

!!! info "Data Source"
    **User input** — paste or upload crystal structures.
    **jarvis-tools** — `jarvis.core.atoms`, `jarvis.analysis.defects.surface`, `jarvis.analysis.diffraction.xrd`.

## Endpoints

### `POST /structure_visualizer/load` — Load and parse structure

Load a structure from POSCAR, CIF, XYZ, or PDB format. Returns POSCAR, XYZ (for 3D viewer), and structural info.

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/load" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "structure": "Al FCC\n1.0\n4.05 0.0 0.0\n0.0 4.05 0.0\n0.0 0.0 4.05\nAl\n4\ndirect\n0.0 0.0 0.0\n0.5 0.5 0.0\n0.5 0.0 0.5\n0.0 0.5 0.5",
    "format": "poscar"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `structure` | string | required | Structure file content |
| `format` | string | `"poscar"` | `"poscar"`, `"cif"`, `"xyz"`, or `"pdb"` |

**Response** (same for all manipulation endpoints): `poscar`, `xyz`, `info` (formula, num_atoms, spacegroup, volume, density, elements, coords).

---

### `POST /structure_visualizer/supercell` — Build supercell

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/supercell" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Al FCC\n1.0\n4.05 0.0 0.0\n0.0 4.05 0.0\n0.0 0.0 4.05\nAl\n4\ndirect\n0.0 0.0 0.0\n0.5 0.5 0.0\n0.5 0.0 0.5\n0.0 0.5 0.5",
    "dimensions": [2, 2, 2]
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `poscar` | string | Input POSCAR |
| `dimensions` | list[int] | Supercell dimensions [nx, ny, nz], each 1–5 |

---

### `POST /structure_visualizer/surface` — Create surface slab

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/surface" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Al FCC\n1.0\n4.05 0.0 0.0\n0.0 4.05 0.0\n0.0 0.0 4.05\nAl\n4\ndirect\n0.0 0.0 0.0\n0.5 0.5 0.0\n0.5 0.0 0.5\n0.0 0.5 0.5",
    "miller_indices": [1, 1, 0],
    "vacuum": 15.0
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | Input POSCAR |
| `miller_indices` | list[int] | required | Miller indices [h, k, l] |
| `vacuum` | float | 15.0 | Vacuum thickness (Å) |

---

### `POST /structure_visualizer/vacancy` — Create vacancy defect

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/vacancy" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Al FCC\n1.0\n4.05 0.0 0.0\n0.0 4.05 0.0\n0.0 0.0 4.05\nAl\n4\ndirect\n0.0 0.0 0.0\n0.5 0.5 0.0\n0.5 0.0 0.5\n0.0 0.5 0.5",
    "atom_index": 0
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `poscar` | string | Input POSCAR |
| `atom_index` | int | 0-indexed atom position to remove |

---

### `POST /structure_visualizer/substitution` — Substitute atom

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/substitution" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Al FCC\n1.0\n4.05 0.0 0.0\n0.0 4.05 0.0\n0.0 0.0 4.05\nAl\n4\ndirect\n0.0 0.0 0.0\n0.5 0.5 0.0\n0.5 0.0 0.5\n0.0 0.5 0.5",
    "atom_index": 0,
    "new_element": "Cu"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `poscar` | string | Input POSCAR |
| `atom_index` | int | 0-indexed atom position to substitute |
| `new_element` | string | New element symbol (e.g. `"Cu"`, `"Fe"`, `"N"`) |

---

### `POST /structure_visualizer/to_primitive` — Convert to primitive cell

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/to_primitive" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si Diamond\n1.0\n5.43 0.0 0.0\n0.0 5.43 0.0\n0.0 0.0 5.43\nSi\n8\ndirect\n0.0 0.0 0.0\n0.25 0.25 0.25\n0.5 0.5 0.0\n0.75 0.75 0.25\n0.5 0.0 0.5\n0.75 0.25 0.75\n0.0 0.5 0.5\n0.25 0.75 0.75"
  }'
```

---

### `POST /structure_visualizer/to_conventional` — Convert to conventional cell

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/to_conventional" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n0 2.734 2.734\n2.734 0 2.734\n2.734 2.734 0\nSi\n2\ndirect\n0 0 0\n0.25 0.25 0.25"
  }'
```

---

### `POST /structure_visualizer/xrd` — Generate XRD pattern

```bash
curl -X POST "https://atomgpt.org/structure_visualizer/xrd" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n0 2.734 2.734\n2.734 0 2.734\n2.734 2.734 0\nSi\n2\ndirect\n0 0 0\n0.25 0.25 0.25"
  }'
```

Returns `num_peaks`, `top_peak` (2θ of strongest peak), `theta` (array), `intensities` (array).

---

## Python Examples

=== "Load and visualize"

    ```python
    import requests

    AL_POSCAR = """Al FCC
    1.0
    4.05 0.0 0.0
    0.0 4.05 0.0
    0.0 0.0 4.05
    Al
    4
    direct
    0.0 0.0 0.0
    0.5 0.5 0.0
    0.5 0.0 0.5
    0.0 0.5 0.5"""

    response = requests.post(
        "https://atomgpt.org/structure_visualizer/load",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"structure": AL_POSCAR, "format": "poscar"},
    )
    data = response.json()
    info = data["info"]
    print(f"{info['formula']} — {info['num_atoms']} atoms")
    print(f"  Spacegroup: {info['spacegroup']}")
    print(f"  Volume: {info['volume']:.2f} ų")
    print(f"  Density: {info['density']:.2f} g/cm³")
    ```

=== "Build supercell"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/structure_visualizer/supercell",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("POSCAR").read(),
            "dimensions": [2, 2, 1],
        },
    )
    data = response.json()
    print(f"Supercell: {data['info']['num_atoms']} atoms")
    with open("POSCAR_supercell", "w") as f:
        f.write(data["poscar"])
    ```

=== "Create surface + vacancy"

    ```python
    import requests

    HEADERS = {
        "Authorization": "Bearer sk-XYZ",
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    poscar = open("POSCAR").read()

    # Create (110) surface
    resp = requests.post(
        "https://atomgpt.org/structure_visualizer/surface",
        headers=HEADERS,
        json={"poscar": poscar, "miller_indices": [1, 1, 0], "vacuum": 15.0},
    )
    surface_poscar = resp.json()["poscar"]
    print(f"Surface: {resp.json()['info']['num_atoms']} atoms")

    # Create vacancy at atom 0
    resp = requests.post(
        "https://atomgpt.org/structure_visualizer/vacancy",
        headers=HEADERS,
        json={"poscar": surface_poscar, "atom_index": 0},
    )
    print(f"With vacancy: {resp.json()['info']['num_atoms']} atoms")
    with open("POSCAR_surface_vacancy", "w") as f:
        f.write(resp.json()["poscar"])
    ```

=== "XRD pattern"

    ```python
    import requests
    import matplotlib.pyplot as plt

    response = requests.post(
        "https://atomgpt.org/structure_visualizer/xrd",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": open("POSCAR").read()},
    )
    data = response.json()
    print(f"Peaks: {data['num_peaks']}, Top at 2θ={data['top_peak']:.2f}°")

    plt.figure(figsize=(8, 4))
    plt.stem(data["theta"], data["intensities"], linefmt="b-", markerfmt="bo", basefmt="k-")
    plt.xlabel("2θ (degrees)")
    plt.ylabel("Intensity")
    plt.title("Powder XRD Pattern")
    plt.tight_layout()
    plt.savefig("xrd_pattern.png")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Load structure
response = agent.query_sync("Visualize the crystal structure of Al FCC")
print(response)

# Build supercell
response = agent.query_sync("Create a 2x2x2 supercell of Si")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
