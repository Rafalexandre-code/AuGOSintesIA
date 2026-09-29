# Notes & FAQ

A grab-bag of tips collected from user issues and questions.

## GPU / DGL

- Install a DGL build that matches your CUDA runtime, e.g. `pip install dgl-cu111` for
  CUDA 11.1. Mismatched builds are the most common install failure.
- If you see errors involving `libcudart.so` or `libtorch_cuda.so`, reinstall DGL from
  the wheel index that matches your PyTorch CUDA version (see
  [Installation](installation.md)).

## Structure file parsing

- Simple `.cif` and `.pdb` files are handled by `jarvis-tools` directly.
- For more complex CIFs, install `cif2cell==2.0.0a3`.
- For complex PDBs, install `pytraj` via `conda install -c ambermd pytraj`.

## Training hyperparameters

- The example `config_example.json` ships with `batch_size: 2` so the test suite runs
  fast. **Use `batch_size: 32` or `64` for real trainings** — otherwise training will
  be very slow and under-performing.
- `pandas >= 1.2.3` is required.
- Starting March 2024, `pytorch-ignite` is no longer a dependency (removed for
  conda-forge build compatibility).

## CLIs are importable scripts

`train_alignn.py`, `pretrained.py`, and `run_alignn_ff.py` are installed as executables
in your environment's `bin/` directory. You do not need the absolute path — just run
them.

## Known dataset issues

- **QM9** results: see
  [issue #54](https://github.com/atomgptlab/alignn/issues/54) for details on a data-split
  discrepancy that affects reproducibility.

## Getting help

- File a GitHub issue: <https://github.com/atomgptlab/alignn/issues>
- Email: `drkamal@jhu.edu`
