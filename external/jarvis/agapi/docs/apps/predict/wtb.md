---
title: Wannier TB Bands
---

# Wannier TB Bands

Compute electronic band structures and density of states from Wannier tight-binding Hamiltonians in the JARVIS-WTB database. Select a material by JARVIS ID, provide a VASP-format k-point path, and the app downloads the `wannier90_hr.dat` from figshare, diagonalizes the Hamiltonian along the k-path using `jarvis.io.wannier.outputs.WannierHam`, and returns eigenvalues + DOS.

[:material-open-in-new: Open App](https://atomgpt.org/wtb){ .md-button .md-button--primary }

---

## Overview

The JARVIS-WTB database contains Wannier90 tight-binding Hamiltonians for thousands of materials, enabling rapid band structure calculations without re-running DFT. The app downloads the compressed `wannier90_hr.dat` file, parses it with `WannierHam`, computes eigenvalues along a user-specified k-path, and calculates DOS with Gaussian broadening (σ=0.1, 1000 energy points). Results include Wannier function count, Fermi energy, and DFT-vs-Wannier interpolation errors (`maxdiff_bz`, `maxdiff_mesh`).

!!! info "Data Source"
    **JARVIS-WTB** — `wannier90_hr.dat` files from `jarvis.db.figshare.data('raw_files')['WANN']`.
    Material metadata from `all_wanns.json` (formula, space group, Fermi energy, interpolation errors).

## Endpoints

### `GET /wtb/options` — List available WTB materials

Returns a dropdown list of all materials in the JARVIS-WTB database with JID, formula, and space group.

```bash
curl "https://atomgpt.org/wtb/options" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:** `{"success": true, "options": [{"jid": "JVASP-1002", "formula": "Si", "spg": "Fd-3m"}, ...]}`

---

### `POST /wtb/predict` — Compute bandstructure + DOS

Select a material by JID and provide a VASP line-mode KPOINTS path. Downloads the Wannier Hamiltonian and computes eigenvalues + DOS.

```bash
curl -X POST "https://atomgpt.org/wtb/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-1002",
    "kpoints": "Line mode\n40\nReciprocal\n0.5 0.5 0.5 L\n0.0 0.0 0.0 \\Gamma\n\n0.0 0.0 0.0 \\Gamma\n0.5 0.0 0.5 X\n\n0.5 0.0 0.5 X\n0.5 0.25 0.75 W\n\n0.5 0.25 0.75 W\n0.375 0.375 0.75 K"
  }'
```

BCC k-path example:

```bash
curl -X POST "https://atomgpt.org/wtb/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-816",
    "kpoints": "Line mode\n40\nReciprocal\n0.0 0.0 0.0 \\Gamma\n0.5 -0.5 0.5 H\n\n0.5 -0.5 0.5 H\n0.25 0.25 0.25 P\n\n0.25 0.25 0.25 P\n0.0 0.0 0.0 \\Gamma\n\n0.0 0.0 0.0 \\Gamma\n0.0 0.0 0.5 N"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `jid` | string | JARVIS ID from the WTB database (use `/wtb/options` to list) |
| `kpoints` | string | VASP line-mode KPOINTS format (pairs of k-points with labels) |

**Response:**

| Field | Description |
|-------|-------------|
| `bands` | 2D array (nbands × nkpts) of eigenvalues (eV, relative to E_F) |
| `nkpts` | Number of k-points along the path |
| `kp_labels_points` | k-point indices where labels appear |
| `kp_labels_text` | High-symmetry point labels (Γ, X, W, K, etc.) |
| `en_dos` | DOS energy grid (eV) |
| `dos` | DOS values |
| `formula` | Chemical formula |
| `spg` | Space group |
| `efermi` | Fermi energy (eV) |
| `nwan` | Number of Wannier functions |
| `maxdiff_bz` | Max DFT-vs-Wannier error along BZ path (eV) |
| `maxdiff_mesh` | Max DFT-vs-Wannier error on k-mesh (eV) |
| `total_time` | Computation time (seconds) |
| `download_url` | Direct download URL for the wannier90_hr.dat.zip |

---

## Python Examples

=== "Compute bandstructure"

    ```python
    import requests

    FCC_KPOINTS = """Line mode
    40
    Reciprocal
    0.5 0.5 0.5 L
    0.0 0.0 0.0 \\Gamma

    0.0 0.0 0.0 \\Gamma
    0.5 0.0 0.5 X

    0.5 0.0 0.5 X
    0.5 0.25 0.75 W

    0.5 0.25 0.75 W
    0.375 0.375 0.75 K"""

    response = requests.post(
        "https://atomgpt.org/wtb/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"jid": "JVASP-1002", "kpoints": FCC_KPOINTS},
    )
    data = response.json()
    if data["success"]:
        print(f"{data['formula']} ({data['spg']})")
        print(f"  Wannier functions: {data['nwan']}")
        print(f"  Fermi energy: {data['efermi']:.3f} eV")
        print(f"  Bands: {len(data['bands'])}, K-points: {data['nkpts']}")
        print(f"  Maxdiff BZ: {data['maxdiff_bz']} eV")
        print(f"  Time: {data['total_time']}s")
    ```

=== "Plot bandstructure"

    ```python
    import requests
    import matplotlib.pyplot as plt

    response = requests.post(
        "https://atomgpt.org/wtb/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"jid": "JVASP-1002", "kpoints": open("KPOINTS").read()},
    )
    data = response.json()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 1]})

    # Band structure
    for band in data["bands"]:
        ax1.plot(range(data["nkpts"]), band, "b-", lw=0.8)
    ax1.axhline(0, color="gray", ls="--", lw=0.5)
    ax1.set_xticks(data["kp_labels_points"])
    ax1.set_xticklabels(data["kp_labels_text"])
    ax1.set_ylabel("E - E_F (eV)")
    ax1.set_ylim(-4, 4)
    ax1.set_title(f"{data['formula']} ({data['spg']})")

    # DOS
    ax2.plot(data["dos"], data["en_dos"], "b-", lw=1.5)
    ax2.fill_betweenx(data["en_dos"], 0, data["dos"], alpha=0.15)
    ax2.axhline(0, color="gray", ls="--", lw=0.5)
    ax2.set_xlabel("DOS")
    ax2.set_ylim(-4, 4)
    ax2.set_yticklabels([])

    plt.tight_layout()
    plt.savefig(f"wtb_{data['jid']}.png", dpi=150)
    ```

=== "List available materials"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/wtb/options",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"Total WTB materials: {len(data['options'])}")
    for opt in data["options"][:10]:
        print(f"  {opt['jid']:12s} {opt['formula']:10s} {opt['spg']}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Compute band structure
response = agent.query_sync("Compute Wannier TB bandstructure for Si (JVASP-1002)")
print(response)
```

## References

- K. Choudhary et al., Sci. Data 8, 106 (2021) — JARVIS-WTB [:material-link: DOI](https://doi.org/10.1038/s41597-021-00885-z)
- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
