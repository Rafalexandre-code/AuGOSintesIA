# Dataset Format

All ALIGNN training entry points read a directory containing **structure files** plus an
index file (`id_prop.csv` for property prediction, `id_prop.json` for force-field
training).

Supported structure formats: **POSCAR**, **CIF**, **XYZ**, **PDB**.

## Directory layout

```
my_dataset/
├── POSCAR-1
├── POSCAR-2
├── ...
└── id_prop.csv
```

## id_prop.csv (property prediction)

Filename and target value(s) per row, no header:

```csv
POSCAR-1,1.234
POSCAR-2,0.567
```

For multi-output regression, append additional columns per target.

## id_prop.json (force-field training)

JSON list of entries containing `jid`, `energy` (per atom), `forces`, and `stress`. See
`alignn/examples/sample_data_ff/id_prop.json` for a concrete example.

A Colab notebook for compiling VASP `vasprun.xml` files into `id_prop.json` is available
[here](https://colab.research.google.com/gist/knc6/5513b21f5fd83a7943509ffdf5c3608b/make_id_prop.ipynb).

## Train/val/test split

By default the dataset is split **80/10/10** (set by `train_ratio`, `val_ratio`,
`test_ratio` in the config).

To control the split manually, set `n_train`, `n_val`, `n_test` and
`keep_data_order: true` in the config — this disables the random shuffle so you can train
on one set and validate/test on another.

## Configuration file

All hyperparameters live in a JSON config. Start from the examples:

- [`config_example.json`](https://github.com/atomgptlab/alignn/blob/main/alignn/examples/sample_data/config_example.json) — property prediction
- [`config_example_atomwise.json`](https://github.com/atomgptlab/alignn/blob/main/alignn/examples/sample_data_ff/config_example_atomwise.json) — force-field

!!! tip
    The example configs ship with `batch_size: 2` so the tests run fast. Bump to **32**
    or **64** for real trainings, otherwise training will be slow and under-performing.
