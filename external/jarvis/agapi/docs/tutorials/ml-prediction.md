---
title: ML Property Prediction
---

# ML Property Prediction with ALIGNN

Predict 50+ materials properties in seconds using ALIGNN graph neural networks.

## Install

```bash
pip install alignn jarvis-tools agapi
```

## Predict a Single Property

```python
from alignn.pretrained import get_prediction
from jarvis.core.atoms import Atoms
from jarvis.db.figshare import get_jid_data

atoms = Atoms.from_dict(get_jid_data("JVASP-1002", "dft_3d")["atoms"])

# Band gap
gap = get_prediction(atoms=atoms, model_name="jv_optb88vdw_bandgap")
print(f"Predicted band gap: {gap} eV")

# Formation energy
ef = get_prediction(atoms=atoms, model_name="jv_formation_energy_peratom")
print(f"Predicted formation energy: {ef} eV/atom")

# Bulk modulus
kv = get_prediction(atoms=atoms, model_name="jv_bulk_modulus_kv")
print(f"Predicted bulk modulus: {kv} GPa")
```

## Via AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Predict properties of JVASP-1002 with ALIGNN")
print(response)
```

## Batch Screening

```python
from jarvis.db.figshare import data
from alignn.pretrained import get_prediction
from jarvis.core.atoms import Atoms

dft = data("dft_3d")
for entry in dft[:20]:
    atoms = Atoms.from_dict(entry["atoms"])
    pred = get_prediction(atoms=atoms, model_name="jv_formation_energy_peratom")
    dft_val = entry.get("formation_energy_peratom", "na")
    print(f"{entry['jid']}: {entry['formula']:8s} ALIGNN={pred:.3f} DFT={dft_val}")
```

## Via AGAPI REST API

```python
from agapi.agents.functions import alignn_predict

r = alignn_predict(jid="JVASP-1002", api_client=client)
print(r)
```

## Available Models

Key pre-trained models (50+ total):

| Model | Property | Units |
|-------|----------|-------|
| `jv_formation_energy_peratom` | Formation energy | eV/atom |
| `jv_optb88vdw_bandgap` | Band gap (OptB88vdW) | eV |
| `jv_mbj_bandgap` | Band gap (mBJ) | eV |
| `jv_bulk_modulus_kv` | Bulk modulus (Voigt) | GPa |
| `jv_shear_modulus_gv` | Shear modulus (Voigt) | GPa |
| `jv_ehull` | Energy above hull | eV/atom |
| `jv_magmom_oszicar` | Magnetic moment | μB |
| `jv_spillage` | Topological spillage | — |
| `jv_slme` | SLME efficiency | % |
| `jv_n_Seebeck` | n-type Seebeck | μV/K |

## Reference

K. Choudhary et al., npj Comp. Mat. 7, 1 (2021) — [DOI](https://doi.org/10.1038/s41524-021-00650-1)
