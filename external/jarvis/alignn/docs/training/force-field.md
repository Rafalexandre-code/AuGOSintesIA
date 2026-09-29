# Force-Field / MLIP Training

ALIGNN-FF is trained with the same `train_alignn.py` script but using the
`atomwise_alignn` model. Instead of `id_prop.csv`, the script reads `id_prop.json` with
entries for `jid`, `energy`, `forces`, and `stress`.

!!! warning "Energy is per atom"
    Energy values in `id_prop.json` must be stored **per atom**, not per structure.

## Train from scratch

```bash
train_alignn.py \
  --root_dir "alignn/examples/sample_data_ff" \
  --config "alignn/examples/sample_data_ff/config_example_atomwise.json" \
  --output_dir="temp"
```

## Fine-tune a pretrained ALIGNN-FF

Pass `--restart_model_path` with a checkpoint that uses the same model configuration:

```bash
train_alignn.py \
  --root_dir "alignn/examples/sample_data_ff" \
  --restart_model_path "temp/best_model.pt" \
  --config "alignn/examples/sample_data_ff/config_example_atomwise.json" \
  --output_dir="temp1"
```

## Building an id_prop.json from VASP runs

A reference notebook compiles a directory of `vasprun.xml` files into an
`id_prop.json`:

→ [Colab: `make_id_prop`](https://colab.research.google.com/gist/knc6/5513b21f5fd83a7943509ffdf5c3608b/make_id_prop.ipynb)

## Joint training with extra targets (v2024.10.30+)

From **v2024.10.30**, you can jointly train energy + forces + stress along with
atomwise non-gradient properties (charges, magnetic moments) and optional fingerprint
features. See [Multi-output regression](multi-output-regression.md) and the end-to-end configs under
[`alignn/examples/`](https://github.com/atomgptlab/alignn/tree/main/alignn/examples).

## Recommended Colab walkthrough

The Silicon example is the best starting point before training a new force-field on
your own data:

→ [Colab: Train ALIGNN-FF on Mlearn (Silicon)](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/Train_ALIGNNFF_Mlearn.ipynb)

## See also

- [Using a pretrained ALIGNN-FF](../pretrained/alignn-ff.md)
- [ASE calculator](../usage/ase-calculator.md)
- [Multi-GPU training](multi-gpu.md)
