---
title: ALIGNN-FF Molecular Dynamics
---

# ALIGNN-FF Molecular Dynamics

Run molecular dynamics with near-DFT accuracy using the ALIGNN-FF universal force field.

## Install

```bash
pip install alignn jarvis-tools ase
```

## Single-Point Energy

```python
from alignn.ff.ff import AlignnAtomwiseCalculator, default_path
from jarvis.core.atoms import Atoms
from jarvis.db.figshare import get_jid_data
import numpy as np

calc = AlignnAtomwiseCalculator(path=default_path())

atoms = Atoms.from_dict(get_jid_data("JVASP-1002", "dft_3d")["atoms"])
ase_atoms = atoms.ase_converter()
ase_atoms.calc = calc

energy = ase_atoms.get_potential_energy()
forces = ase_atoms.get_forces()
print(f"Energy: {energy:.4f} eV")
print(f"Max force: {np.max(np.abs(forces)):.4f} eV/Ang")
```

## Structure Relaxation

```python
from ase.optimize import BFGS

opt = BFGS(ase_atoms)
opt.run(fmax=0.01)
print(f"Relaxed energy: {ase_atoms.get_potential_energy():.4f} eV")
```

## Molecular Dynamics (NVT)

```python
from ase.md.langevin import Langevin
from ase import units

dyn = Langevin(ase_atoms, 1.0 * units.fs, temperature_K=300, friction=0.02)

def print_status():
    T = ase_atoms.get_temperature()
    E = ase_atoms.get_potential_energy()
    print(f"Step: T={T:.1f}K E={E:.4f}eV")

dyn.attach(print_status, interval=10)
dyn.run(200)
```

## Via AGAPI

```python
from agapi.agents.functions import alignn_ff_relax, alignn_ff_single_point
import os
from agapi.agents.client import AGAPIClient

client = AGAPIClient(api_key=os.environ.get("AGAPI_KEY"))

SI_PRIM = """Si
1.0
0 2.734 2.734
2.734 0 2.734
2.734 2.734 0
Si
2
direct
0 0 0
0.25 0.25 0.25
"""

r = alignn_ff_relax(SI_PRIM, api_client=client)
print(r)
```

## Reference

K. Choudhary, Digital Discovery 2(2), 346 (2023) — [DOI](https://doi.org/10.1039/D2DD00096B)
