---
title: Getting Started with JARVIS
---

# Getting Started with JARVIS

Learn to load materials data, manipulate crystal structures, and query the JARVIS-DFT database.

## Install

```bash
pip install jarvis-tools agapi
```

## Load a Material by JARVIS ID

```python
from jarvis.db.figshare import get_jid_data
from jarvis.core.atoms import Atoms

data = get_jid_data(jid="JVASP-1002", dataset="dft_3d")
atoms = Atoms.from_dict(data["atoms"])

print(f"Formula: {data['formula']}")
print(f"Space group: {data['spg_symbol']}")
print(f"Band gap: {data['optb88vdw_bandgap']} eV")
print(f"Atoms: {atoms.num_atoms}")
print(f"Lattice:\n{atoms.lattice_mat}")
```

## Query the Full Database

```python
from jarvis.db.figshare import data

dft = data("dft_3d")
print(f"{len(dft)} materials loaded")

# Filter: binary oxides with band gap > 2 eV
oxides = [
    e for e in dft
    if e.get("optb88vdw_bandgap") not in (None, "na")
    and float(e["optb88vdw_bandgap"]) > 2.0
    and len(set(e["atoms"]["elements"])) == 2
    and "O" in e["atoms"]["elements"]
]
print(f"Found {len(oxides)} binary oxides with gap > 2 eV")
```

## Using the AGAPI Client

```python
import os
from agapi.agents.client import AGAPIClient
from agapi.agents.functions import query_by_formula, query_by_jid

client = AGAPIClient(api_key=os.environ.get("AGAPI_KEY"))

# Search by formula
r = query_by_formula("SrTiO3", client)
print(f"Found {len(r['materials'])} SrTiO3 entries")

# Get POSCAR for a specific material
r = query_by_jid("JVASP-1002", client)
print(r["POSCAR"][:200])
```

## Structure Manipulation

```python
from jarvis.core.atoms import Atoms

# Make supercell
supercell = atoms.make_supercell([2, 2, 2])
print(f"Supercell: {supercell.num_atoms} atoms")

# Write files
atoms.write_poscar("Si.vasp")
atoms.write_cif("Si.cif")
```

## Next Steps

- [ML Property Prediction](ml-prediction.md) — predict properties with ALIGNN
- [API Reference](../api/python-client.md) — all available functions
