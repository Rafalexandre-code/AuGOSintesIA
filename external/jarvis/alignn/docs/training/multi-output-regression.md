# Multi-Output Regression

Train a single model that jointly predicts multiple scalar or vector targets — e.g.
formation energy + bandgap + total energy, or full electron / phonon DOS.

## Command

```bash
train_alignn.py \
  --root_dir "alignn/examples/sample_data_multi_prop" \
  --config "alignn/examples/sample_data/config_example.json" \
  --output_dir=temp
```

## Dataset

Extra target columns are appended to each `id_prop.csv` row (order must match the config).
A generator script lives at
[`alignn/examples/sample_data_multi_prop/scripts/`](https://github.com/atomgptlab/alignn/tree/main/alignn/examples/sample_data_multi_prop).

For vector targets like DOS, each target value is a list of floats; see the DOS example
folder under `alignn/examples/`.

## Why multi-output?

- Shared representations often improve individual target accuracy.
- One forward pass predicts all targets, which is useful for screening workflows.
- Correlated targets (e.g. energy and its components) benefit from joint loss signals.

## Global atomwise + graph-wise training (v2024.10.30+)

Starting with **v2024.10.30**, multi-output training can mix output *kinds* in one model:

- **Graph-wise** scalar/vector outputs (e.g. energy, bandgap)
- **Atomwise gradient** outputs (forces — derivatives of energy w.r.t. positions)
- **Atomwise non-gradient** outputs (charges, magnetic moments)

Optional per-atom or per-graph fingerprint features can be concatenated into the input
graph. See end-to-end configs in
[`alignn/examples/`](https://github.com/atomgptlab/alignn/tree/main/alignn/examples).

## See also

- [Force-field training](force-field.md) — atomwise forces & stress
- [Single-output regression](single-output-regression.md)
