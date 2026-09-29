# Pre-trained ALIGNN-FF

ALIGNN-FF is a universal graph neural network force-field. Several pretrained versions
are shipped with the package under
[`alignn/ff/`](https://github.com/atomgptlab/alignn/tree/main/alignn/ff) and on
[Figshare](https://figshare.com/projects/ALIGNN_models/126478).

## CLI

```bash
run_alignn_ff.py -h
```

Common tasks:

```bash
# Single-point energy on the unrelaxed structure
run_alignn_ff.py --file_path POSCAR --task="unrelaxed_energy"

# Structure optimization
run_alignn_ff.py --file_path POSCAR --task="optimize"

# Energy vs. volume curve
run_alignn_ff.py --file_path POSCAR --task="ev_curve"
```

Additional tasks supported by the CLI include phonon calculations, interface
gamma-surface scans, and simple MD — run `-h` to see the full set.

## Available checkpoints

Model folders bundled with the package:

- `v10.30.2024_dft_3d_307k` — trained on 307k JARVIS-DFT configurations (Oct 2024)
- `v12.2.2024_dft_3d_307k` — updated December 2024 release
- `v2024.12.12_dft_3d_multi_prop` — multi-property (energy + atomwise targets)
- `alignnff_wt01` — weighted loss variant
- `alex_band_gap`, `jv_mbj_bandgap_alignn` — bandgap-oriented models

Additional models are listed in
[`all_models_alignn_atomwise.json`](https://github.com/atomgptlab/alignn/blob/main/alignn/ff/all_models_alignn_atomwise.json).

## Default path helper

```python
from alignn.ff.ff import default_path
print(default_path())  # directory containing the default checkpoint
```

## Using it programmatically

See the [ASE calculator](../usage/ase-calculator.md) page for a full worked example
covering relaxation and an EV curve.

## See also

- [Train / fine-tune a force-field](../training/force-field.md)
- [Property predictors](property-predictor.md)
- [Colab: ALIGNN-FF relaxation, EV curve, phonons, interfaces](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/ALIGNN_Structure_Relaxation_Phonons_Interface.ipynb)
- [Colab: Melt-quench MD](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/Fast_Melt_Quench.ipynb)
