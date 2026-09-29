---
title: ALIGNN-FF Dynamics
---

# ALIGNN-FF Dynamics

Universal ML force field for atomistic simulations. Three tabs: (1) Geometry Optimization — relax structures with FIRE/BFGS/LBFGS, (2) Molecular Dynamics — NVE simulations with Maxwell-Boltzmann initialization, (3) Phonon Bandstructure — finite-displacement phonon calculations via phonopy. All powered by ALIGNN-FF (`AlignnAtomwiseCalculator`).

[:material-open-in-new: Open App](https://atomgpt.org/alignn_ff_dynamics){ .md-button .md-button--primary }

---

## Overview

The ALIGNN-FF app provides a complete atomistic simulation toolkit in the browser. The force field is a pretrained ALIGNN model that predicts energy, forces, and stress for any crystal structure. The app supports geometry optimization with trajectory playback, molecular dynamics with energy/temperature monitoring, and phonon bandstructure calculation via phonopy with interactive Plotly plots.

!!! info "Data Source"
    **ALIGNN-FF** — `AlignnAtomwiseCalculator` from `alignn.ff.ff` (default or wt01 model).
    **phonopy** — for phonon dispersion via finite displacement method.

## Endpoints

### `GET /alignn_ff/query` — Single-point energy (API key)

Compute energy, forces, and stress for a structure without relaxation.

```bash
curl "https://atomgpt.org/alignn_ff/query?poscar=Si%0A1.0%0A0%202.734%202.734%0A2.734%200%202.734%0A2.734%202.734%200%0ASi%0A2%0Adirect%0A0%200%200%0A0.25%200.25%200.25&APIKEY=sk-XYZ" \
  -H "accept: application/json"
```

Returns `energy_eV`, `forces_eV_per_A` (Nx3 array), `stress` (6-component Voigt), `natoms`.

---

### `GET /alignn_ff/relax` — Quick relaxation (plain text POSCAR)

Relax a structure and return the optimized POSCAR as plain text.

```bash
curl "https://atomgpt.org/alignn_ff/relax?poscar=Si%0A1.0%0A5.0%200%200%0A0%205.0%200%0A0%200%205.0%0ASi%0A8%0Adirect%0A0.25%200.75%200.25%0A0%200%200.5%0A0.25%200.25%200.75%0A0%200.5%200%0A0.75%200.75%200.75%0A0.5%200%200%0A0.75%200.25%200.25%0A0.5%200.5%200.5&fmax=0.05&steps=50&APIKEY=sk-XYZ"
```

| Param | Default | Description |
|-------|---------|-------------|
| `poscar` | required | URL-encoded POSCAR |
| `fmax` | 0.05 | Force convergence tolerance (eV/Å) |
| `steps` | 50 | Max relaxation steps |

Returns plain text relaxed POSCAR.

---

### `POST /alignn_ff/optimize` — Full optimization with trajectory

Geometry optimization with full trajectory data for visualization and playback.

```bash
curl -X POST "https://atomgpt.org/alignn_ff/optimize" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n5.0 0 0\n0 5.0 0\n0 0 5.0\nSi\n8\ndirect\n0.25 0.75 0.25\n0 0 0.5\n0.25 0.25 0.75\n0 0.5 0\n0.75 0.75 0.75\n0.5 0 0\n0.75 0.25 0.25\n0.5 0.5 0.5",
    "fmax": 0.05,
    "steps": 100,
    "optimizer": "FIRE",
    "relax_cell": true
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | VASP POSCAR structure (max 100 atoms) |
| `fmax` | float | 0.05 | Force convergence (eV/Å) |
| `steps` | int | 200 | Max optimization steps |
| `optimizer` | string | `"FIRE"` | `"FIRE"`, `"BFGS"`, or `"LBFGS"` |
| `relax_cell` | bool | true | Also optimize cell parameters (via ExpCellFilter) |

**Response** includes `converged`, `final_poscar`, `initial_energy`, `final_energy`, `energy_change`, `steps_taken`, `energies` (per-step), `forces_max` (per-step), `trajectory` (positions/cell every 5 steps for playback), `computation_time`.

---

### `POST /alignn_ff/md` — Molecular dynamics

NVE molecular dynamics with Maxwell-Boltzmann velocity initialization and VelocityVerlet integrator.

```bash
curl -X POST "https://atomgpt.org/alignn_ff/md" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n5.494 0 0\n0 5.494 0\n0 0 5.494\nSi\n8\ndirect\n0.25 0.75 0.25\n0 0 0.5\n0.25 0.25 0.75\n0 0.5 0\n0.75 0.75 0.75\n0.5 0 0\n0.75 0.25 0.25\n0.5 0.5 0.5",
    "temperature": 300.0,
    "timestep": 0.5,
    "steps": 50,
    "interval": 5
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | POSCAR structure (max 50 atoms) |
| `temperature` | float | 300.0 | Initial temperature (K) |
| `timestep` | float | 0.5 | Integration timestep (fs) |
| `steps` | int | 50 | Number of MD steps |
| `interval` | int | 5 | Save trajectory every N steps |

**Response** includes `trajectory` (positions, velocities, T, KE, PE per saved frame), `energies` (total/kinetic/potential arrays), `temperatures`, `average_temperature`, `final_temperature`, `computation_time`.

---

### `POST /alignn_ff/phonons` — Phonon bandstructure

Relax the structure, then compute phonon dispersion via phonopy finite displacements.

```bash
curl -X POST "https://atomgpt.org/alignn_ff/phonons" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n5.494 0 0\n0 5.494 0\n0 0 5.494\nSi\n8\ndirect\n0.25 0.75 0.25\n0 0 0.5\n0.25 0.25 0.75\n0 0.5 0\n0.75 0.75 0.75\n0.5 0 0\n0.75 0.25 0.25\n0.5 0.5 0.5",
    "fmax": 0.05,
    "relax_steps": 50,
    "force_multiplier": 1.9,
    "dim": [2, 2, 2],
    "relax_cell": true
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar` | string | required | POSCAR structure (max 50 atoms) |
| `fmax` | float | 0.05 | Force convergence for pre-relaxation (eV/Å) |
| `relax_steps` | int | 50 | Max relaxation steps |
| `force_multiplier` | float | 1.9 | Force scaling for phonopy |
| `dim` | list[int] | `[2,2,2]` | Supercell dimensions for phonon calculation |
| `relax_cell` | bool | true | Relax cell before phonon calc |

**Response** includes `relaxed_poscar`, `primitive_poscar`, `band_data` (distances + frequencies for interactive Plotly), `plot_base64` (PNG fallback), `supercell_dim`, `computation_time`.

---

## Python Examples

=== "Optimize structure"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/alignn_ff/optimize",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("POSCAR").read(),
            "fmax": 0.05,
            "steps": 100,
            "optimizer": "FIRE",
            "relax_cell": True,
        },
    )
    data = response.json()
    print(f"Converged: {data['converged']}")
    print(f"E: {data['initial_energy']:.4f} → {data['final_energy']:.4f} eV")
    print(f"Steps: {data['steps_taken']}, Time: {data['computation_time']}s")
    with open("CONTCAR", "w") as f:
        f.write(data["final_poscar"])
    ```

=== "Molecular dynamics"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/alignn_ff/md",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("POSCAR").read(),
            "temperature": 300.0,
            "timestep": 0.5,
            "steps": 100,
            "interval": 10,
        },
    )
    data = response.json()
    print(f"Avg T: {data['average_temperature']:.1f} K")
    print(f"Frames: {len(data['trajectory'])}")
    ```

=== "Phonon bandstructure"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/alignn_ff/phonons",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "poscar": open("POSCAR").read(),
            "dim": [2, 2, 2],
            "force_multiplier": 1.9,
        },
    )
    data = response.json()
    print(f"Primitive atoms: {data['num_atoms_prim']}")
    print(f"Supercell: {data['supercell_dim']}")
    print(f"Time: {data['computation_time']}s")

    # Save phonon plot
    if data.get("plot_base64"):
        import base64
        with open("phonon_bands.png", "wb") as f:
            f.write(base64.b64decode(data["plot_base64"]))
    ```

=== "Single-point energy"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/alignn_ff/query",
        headers={"accept": "application/json"},
        params={
            "poscar": open("POSCAR").read(),
            "APIKEY": "sk-XYZ",
        },
    )
    data = response.json()
    print(f"Energy: {data['energy_eV']:.4f} eV")
    print(f"Max force: {max(max(abs(f) for f in row) for row in data['forces_eV_per_A']):.4f} eV/Å")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Relax structure
response = agent.query_sync("Relax the structure of JVASP-1002 using ALIGNN-FF")
print(response)

# Run MD
response = agent.query_sync("Run molecular dynamics on Si at 500K for 100 steps")
print(response)

# Phonons
response = agent.query_sync("Compute the phonon bandstructure of Si using ALIGNN-FF")
print(response)
```

## References

- K. Choudhary, Digital Discovery 2(2), 346 (2023) — ALIGNN-FF [:material-link: DOI](https://doi.org/10.1039/D2DD00096B)
- K. Choudhary, B. DeCost, npj Comp. Mat. 7, 185 (2021) — ALIGNN [:material-link: DOI](https://doi.org/10.1038/s41524-021-00650-1)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
