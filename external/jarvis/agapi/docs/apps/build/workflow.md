---
title: Workflow Builder
---

# Workflow Builder

Visual pipeline builder for the JARVIS computational materials science ecosystem. Drag-and-drop 32 blocks across 9 categories (input, transform, DFT, force field/MLFF, GNN/ML, tight binding, quantum, analysis, output) to build computational pipelines. Choose from 8 pre-built templates or create custom workflows. Auto-generates ready-to-run Python scripts using jarvis-tools, ALIGNN, AtomGPT, SlakoNet, and Qiskit.

[:material-open-in-new: Open App](https://atomgpt.org/workflow){ .md-button .md-button--primary }

---

## Overview

The Workflow Builder is a code generator, not a compute engine — it produces Python scripts that you run locally or on a cluster. The three-panel UI has a block palette (left), pipeline canvas (center), and live script preview (right). Each block maps to a Python code template that is composed into a complete script with proper variable wiring between blocks.

!!! info "How It Works"
    **No computation happens server-side.** The app generates Python scripts from your pipeline definition. You run the generated `.py` file in your own environment with the required packages installed.

## Block Categories

| Category | Blocks | Description |
|----------|--------|-------------|
| **Input** | `jarvis_id`, `poscar_input`, `formula_input` | Load structures from JARVIS, POSCAR text, or formula |
| **Transform** | `supercell`, `vacancy`, `surface`, `heterostructure` | Structure manipulation |
| **DFT** | `vasp_relax`, `vasp_bands`, `vasp_optics`, `vasp_elastic`, `vasp_phonon`, `vasp_factory`, `qe_relax` | VASP and QE job generation |
| **Force Field** | `alignn_ff_opt`, `alignn_ff_md`, `alignn_ff_phonon`, `lammps_ff`, `chipsff_bench` | ML and classical force fields |
| **GNN / ML** | `alignn_predict`, `atomgpt_predict`, `atomgpt_generate`, `cfid_descriptors` | Property prediction and inverse design |
| **Tight Binding** | `slakonet_bands`, `wannier_tb`, `chipstb_bench` | TB band structure methods |
| **Quantum** | `vqe_electron` | VQE electronic structure via Qiskit |
| **Analysis** | `xrd_analysis`, `rdf_analysis`, `spacegroup_analysis` | Structural characterization |
| **Output** | `save_poscar`, `leaderboard_submit` | Export and benchmarking |

## Pre-built Templates

| Template | Pipeline |
|----------|----------|
| DFT Full | JARVIS ID → VASP JobFactory (relax + bands + optics + elastic) |
| MLFF | JARVIS ID → ALIGNN-FF optimize → MD → phonons |
| GNN Screen | JARVIS ID → ALIGNN predict (formation energy, band gap, bulk modulus) |
| Surface Study | JARVIS ID → surface slab → spacegroup analysis → XRD |
| Defect Study | JARVIS ID → vacancies → ALIGNN-FF optimize |
| TB Bands | JARVIS ID → SlakoNet bands → Wannier TB bands |
| Quantum VQE | VQE electronic at X-point for Al |
| Inverse Design | AtomGPT generate → ALIGNN validate → save POSCAR |

## Endpoints

### `GET /workflow/blocks` — List all available blocks

Returns the full block definition catalog with parameters, categories, and I/O types.

```bash
curl "https://atomgpt.org/workflow/blocks" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

---

### `GET /workflow/templates` — List pre-built templates

Returns 8 template definitions with block sequences and default parameters.

```bash
curl "https://atomgpt.org/workflow/templates" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

---

### `POST /workflow/generate` — Generate Python script

Submit a pipeline definition (list of blocks with parameters) and receive a ready-to-run Python script.

```bash
curl -X POST "https://atomgpt.org/workflow/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "name": "si_screening",
    "blocks": [
      {
        "type": "jarvis_id",
        "params": {"jid": "JVASP-1002", "dataset": "dft_3d"}
      },
      {
        "type": "alignn_predict",
        "params": {"model_name": "formation_energy_peratom"}
      },
      {
        "type": "alignn_predict",
        "params": {"model_name": "optb88vdw_bandgap"}
      },
      {
        "type": "alignn_ff_opt",
        "params": {"model": "alignnff_wt10", "fmax": "0.05", "steps": "200"}
      }
    ]
  }'
```

MLFF workflow example:

```bash
curl -X POST "https://atomgpt.org/workflow/generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "name": "mlff_workflow",
    "blocks": [
      {"type": "jarvis_id", "params": {"jid": "JVASP-1002", "dataset": "dft_3d"}},
      {"type": "alignn_ff_opt", "params": {"model": "alignnff_wt10", "fmax": "0.05", "steps": "200"}},
      {"type": "alignn_ff_md", "params": {"model": "alignnff_wt10", "temp": "300", "timestep": "1", "nsteps": "1000"}},
      {"type": "alignn_ff_phonon", "params": {"model": "alignnff_wt10", "dim": "2,2,2"}}
    ]
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Workflow name (used as script filename) |
| `blocks` | list | Ordered list of pipeline blocks |
| `blocks[].type` | string | Block type key (e.g. `"jarvis_id"`, `"alignn_predict"`) |
| `blocks[].params` | dict | Block-specific parameters (see block definitions) |
| `blocks[].id` | string | Optional custom block ID |

**Response:**

| Field | Description |
|-------|-------------|
| `script` | Generated Python script as string |
| `name` | Workflow name |
| `n_blocks` | Number of blocks in pipeline |
| `block_types` | Ordered list of block type names |

---

## Python Examples

=== "Generate GNN screening script"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/workflow/generate",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "name": "gnn_screen_si",
            "blocks": [
                {"type": "jarvis_id", "params": {"jid": "JVASP-1002", "dataset": "dft_3d"}},
                {"type": "alignn_predict", "params": {"model_name": "formation_energy_peratom"}},
                {"type": "alignn_predict", "params": {"model_name": "optb88vdw_bandgap"}},
                {"type": "alignn_predict", "params": {"model_name": "bulk_modulus_kv"}},
            ],
        },
    )
    data = response.json()
    print(f"Generated {data['n_blocks']}-block script")
    print(f"Pipeline: {' → '.join(data['block_types'])}")

    with open(f"{data['name']}.py", "w") as f:
        f.write(data["script"])
    print(f"Saved: {data['name']}.py")
    ```

=== "DFT full pipeline script"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/workflow/generate",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "name": "dft_full_pipeline",
            "blocks": [
                {"type": "jarvis_id", "params": {"jid": "JVASP-1002"}},
                {"type": "vasp_factory", "params": {
                    "steps": "ENCUT,KPLEN,RELAX,BANDSTRUCT,OPTICS,ELASTIC",
                    "functional": "optb88vdw",
                }},
            ],
        },
    )
    data = response.json()
    with open("dft_full_pipeline.py", "w") as f:
        f.write(data["script"])
    ```

=== "List all blocks"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/workflow/blocks",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    blocks = response.json()["blocks"]
    for cat in ["input", "transform", "dft", "ff", "ml", "tb", "quantum", "analysis", "output"]:
        items = [k for k, v in blocks.items() if v["category"] == cat]
        if items:
            print(f"\n{cat.upper()}: {len(items)} blocks")
            for k in items:
                print(f"  {k:25s} {blocks[k]['label']}")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Generate MLFF workflow
response = agent.query_sync("Generate an MLFF workflow script for Si using ALIGNN-FF")
print(response)
```

## References

- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) — JARVIS [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn) | [atomgptlab/atomgpt](https://github.com/atomgptlab/atomgpt) | [atomgptlab/slakonet](https://github.com/atomgptlab/slakonet)
