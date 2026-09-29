---
title: Heterostructure Builder
---

# Heterostructure Builder

Three-tab interface design platform: (1) Interface Generator — build heterostructure interfaces using the Zur & McGill ZSL lattice-matching algorithm via InterMat (`InterfaceCombi`), with optional ALIGNN-FF work of adhesion calculation, (2) 2D Materials — select two monolayers from JARVIS for band alignment classification (Type I/II/III) and van der Waals heterostructure generation, (3) Interface Database — search the JARVIS interface database by elements via OPTIMADE.

[:material-open-in-new: Open App](https://atomgpt.org/heterostructure){ .md-button .md-button--primary }

---

## Overview

The Heterostructure Builder combines three complementary tools for interface science. The Interface Generator accepts film/substrate structures as POSCAR or JARVIS JIDs, applies ZSL lattice matching with configurable Miller indices, slab thicknesses, tolerances, and separation, and returns the combined interface POSCAR with mismatch metrics. The 2D tab predicts heterojunction type (I, II, or III) from VBM/CBM band offsets. The database tab searches the JARVIS interface database (607 entries) via the OPTIMADE REST API.

!!! info "Data Source"
    **InterMat** — `InterfaceCombi` for ZSL lattice matching.
    **JARVIS dft_2d** — monolayer data with work functions (φ) for band alignment.
    **JARVIS interfacedb** — 607 pre-computed interface entries via OPTIMADE.
    **ALIGNN-FF** — optional work of adhesion (W_ad) calculation.

## Endpoints

### `POST /heterostructure/generate` — Generate interface (ZSL)

Build a heterostructure interface from film and substrate structures using InterfaceCombi. Input as POSCAR text or JARVIS JIDs.

```bash
curl -X POST "https://atomgpt.org/heterostructure/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar_film": "Si\n1.0\n5.468 0 0\n0 5.468 0\n0 0 5.468\nSi\n8\nDirect\n0 0 0\n0.5 0.5 0\n0.5 0 0.5\n0 0.5 0.5\n0.25 0.25 0.25\n0.75 0.75 0.25\n0.75 0.25 0.75\n0.25 0.75 0.75",
    "poscar_subs": "Ge\n1.0\n5.658 0 0\n0 5.658 0\n0 0 5.658\nGe\n8\nDirect\n0 0 0\n0.5 0.5 0\n0.5 0 0.5\n0 0.5 0.5\n0.25 0.25 0.25\n0.75 0.75 0.25\n0.75 0.25 0.75\n0.25 0.75 0.75",
    "film_indices": "0_0_1",
    "subs_indices": "0_0_1",
    "film_thickness": 16.0,
    "subs_thickness": 16.0,
    "max_area": 400.0,
    "ltol": 0.08,
    "separation": 2.5,
    "vacuum_interface": 2.0,
    "from_conventional": true,
    "calculate_wad": false
  }'
```

Using JARVIS JIDs instead of POSCARs:

```bash
curl -X POST "https://atomgpt.org/heterostructure/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "film_ids": "JVASP-1002",
    "subs_ids": "JVASP-1174",
    "film_indices": "0_0_1",
    "subs_indices": "0_0_1",
    "max_area": 400,
    "calculate_wad": true
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar_film` | string | — | Film POSCAR (provide this OR `film_ids`) |
| `poscar_subs` | string | — | Substrate POSCAR (provide this OR `subs_ids`) |
| `film_ids` | string | — | Comma-separated JARVIS JIDs for film |
| `subs_ids` | string | — | Comma-separated JARVIS JIDs for substrate |
| `film_indices` | string | `"0_0_1"` | Film Miller indices (h_k_l) |
| `subs_indices` | string | `"0_0_1"` | Substrate Miller indices |
| `film_thickness` | float | 16.0 | Film slab thickness (Å) |
| `subs_thickness` | float | 16.0 | Substrate slab thickness (Å) |
| `max_area` | float | 400.0 | Max supercell area (Å²) |
| `ltol` | float | 0.08 | Length tolerance for ZSL matching |
| `separation` | float | 2.5 | Interface separation (Å) |
| `vacuum_interface` | float | 2.0 | Vacuum at interface (Å) |
| `disp_intvl` | float | 0.0 | Displacement interval |
| `max_area_ratio_tol` | float | 1.0 | Max area ratio tolerance |
| `max_length_tol` | float | 0.03 | Max length tolerance |
| `max_angle_tol` | float | 0.01 | Max angle tolerance |
| `from_conventional` | bool | true | Use conventional cell for slab construction |
| `id_tag` | string | `"jid"` | ID tag type for JID lookups |
| `calculate_wad` | bool | false | Compute work of adhesion with ALIGNN-FF |

**Response** includes `combined_poscar`, `film_poscar`, `subs_poscar`, `combined_xyz`, formulas, atom counts, `mismatch_u`, `mismatch_v`, `mismatch_angle`, and optionally `min_wad` (J/m²).

---

### `GET /heterostructure/monolayer-options` — List 2D monolayers

```bash
curl "https://atomgpt.org/heterostructure/monolayer-options" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

Returns `{"success": true, "options": [{"jid": "JVASP-664", "formula": "MoS2", "spg": "P-6m2"}, ...]}`.

---

### `POST /heterostructure/twod` — 2D heterostructure + band alignment

Select two 2D monolayers by JID. Predicts heterojunction type (I, II, or III), band offsets (VBM/CBM), stacking type, and generates the combined interface.

```bash
curl -X POST "https://atomgpt.org/heterostructure/twod" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid1": "JVASP-664",
    "jid2": "JVASP-680"
  }'
```

**Response** includes `int_type` (I, II, or III), `stack`, `vbm_a`/`vbm_b`/`cbm_a`/`cbm_b` (eV relative to vacuum), `combined_poscar`, `combined_xyz`, `mismatch_u`/`mismatch_v`.

---

### `POST /heterostructure/search-db` — Search JARVIS interface database

Search 607 pre-computed interface entries by elements via the JARVIS OPTIMADE REST API.

```bash
curl -X POST "https://atomgpt.org/heterostructure/search-db" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "elements": "Si-Ge"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `elements` | string | Dash-separated element list (e.g. `"Si-Ge"`, `"Ga-N-Al"`) |

**Response** includes `count`, `rows` array with: `jid`, `formula`, `energy`, `bandgap`, `cbm`, `vbm`, `offset`.

---

## Python Examples

=== "Generate Si/Ge interface"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/heterostructure/generate",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar_film": open("Si.vasp").read(),
            "poscar_subs": open("Ge.vasp").read(),
            "film_indices": "0_0_1",
            "subs_indices": "0_0_1",
            "max_area": 400,
            "separation": 2.5,
            "calculate_wad": True,
        },
    )
    data = response.json()
    if data["success"]:
        print(f"Interface: {data['combined_formula']} ({data['n_atoms_combined']} atoms)")
        print(f"  Mismatch: u={data['mismatch_u']*100:.2f}%, v={data['mismatch_v']*100:.2f}%")
        if "min_wad" in data:
            print(f"  W_ad: {data['min_wad']:.3f} J/m²")
        with open("POSCAR_interface", "w") as f:
            f.write(data["combined_poscar"])
    ```

=== "2D band alignment"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/heterostructure/twod",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"jid1": "JVASP-664", "jid2": "JVASP-680"},
    )
    data = response.json()
    if data["success"]:
        print(f"Type {data['int_type']} ({data['stack']} stacking)")
        print(f"  {data['labels'][0]}: VBM={data['vbms'][0]}, CBM={data['cbms'][0]} eV")
        print(f"  {data['labels'][1]}: VBM={data['vbms'][1]}, CBM={data['cbms'][1]} eV")
        print(f"  Mismatch: {data['mismatch_u']*100:.2f}%")
    ```

=== "Search interface DB"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/heterostructure/search-db",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"elements": "Si-Ge"},
    )
    data = response.json()
    print(f"Found {data['count']} interfaces")
    for row in data["rows"][:5]:
        print(f"  {row['jid']:12s} {row['formula']:10s} gap={row['bandgap']} eV")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Generate interface
response = agent.query_sync("Generate a Si/Ge heterostructure interface along (001)")
print(response)

# 2D band alignment
response = agent.query_sync("Predict the band alignment type for MoS2/WS2 heterostructure")
print(response)
```

## References

- K. Choudhary et al., Phys. Rev. Mat. 7, 014009 (2023) [:material-link: DOI](https://doi.org/10.1103/PhysRevMaterials.7.014009)
- K. Choudhary et al., Digital Discovery 3, 1209 (2024) — InterMat [:material-link: DOI](https://doi.org/10.1039/D4DD00031E)
- K. Choudhary, arXiv:2004.03025 (2020) — 2D Heterostructures [:material-link: arXiv](https://arxiv.org/abs/2004.03025)
- [atomgptlab/intermat](https://github.com/atomgptlab/intermat)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
