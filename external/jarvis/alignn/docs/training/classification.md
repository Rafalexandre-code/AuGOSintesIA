# Binary Classification

Convert a regression dataset into binary labels and train a classifier — for example,
**metal vs. non-metal** based on a bandgap threshold.

## Command

```bash
train_alignn.py \
  --root_dir "alignn/examples/sample_data" \
  --classification_threshold 0.01 \
  --config "alignn/examples/sample_data/config_example.json" \
  --output_dir=temp
```

Values in `id_prop.csv` are thresholded: `1` if above `--classification_threshold`, `0`
otherwise.

## Supported tasks

!!! note "Binary only"
    The current training script supports **binary classification only**. For multi-class
    problems, open a GitHub issue — it is being considered.

## Typical classification targets (JARVIS-DFT)

| Classifier | Threshold |
|---|---|
| Metal / non-metal (OPT / MBJ bandgap) | 0.01 eV |
| Magnetic / non-magnetic | 0.05 µB |
| Stable / unstable (ehull) | 0.1 eV |
| High / low SLME | 10 % |
| High / low spillage | 0.1 |
| High / low Seebeck | ±100 µV K⁻¹ |
| High / low power factor | 1000 µW (mK²)⁻¹ |

See the [Performance](../performance.md) page for accuracy numbers.

## Metrics

The training loop reports AUC and accuracy on the validation set and writes
`prediction_results_test_set.csv` with per-structure predicted probabilities.

## See also

- [Single-output regression](single-output-regression.md)
- [Colab: miscellaneous tasks (incl. classification)](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/Training_ALIGNN_model_example.ipynb)
