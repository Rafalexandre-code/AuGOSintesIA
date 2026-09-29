# Installation

ALIGNN supports Linux, macOS, and Windows with Python 3.10.

## Prerequisites

Install Miniconda from <https://conda.io/miniconda.html>. Pick the installer matching
your OS:

```bash
bash Miniconda3-latest-Linux-x86_64.sh      # Linux
bash Miniconda3-latest-MacOSX-x86_64.sh     # macOS
```

On Windows, use the 64-bit Python 3.10 Miniconda installer.

## Method 1 — conda (recommended)

```bash
conda create --name my_alignn python=3.12 -y
conda activate my_alignn
conda install -c dglteam/label/th24_cu124 dgl
conda install alignn -y
```

## Method 2 — from GitHub (development install)

```bash
conda create --name my_alignn python=3.12 -y
conda activate my_alignn
conda install -c dglteam/label/th24_cu124 dgl
git clone https://github.com/atomgptlab/alignn
cd alignn
python -m pip install -e .
```

## Method 3 — pip

If you prefer pip, install DGL first from the wheel index that matches your CUDA/PyTorch
version (see <https://www.dgl.ai/pages/start.html>).

PyTorch 2.1 + CUDA 12.1 (Windows/Linux):

```bash
conda install -c dglteam/label/th24_cu124 dgl
pip install alignn
```

CPU only:

```bash
conda install -c dglteam/label/th24_cu124 dgl
pip install alignn
```

## Verifying your install

```bash
train_alignn.py -h
pretrained.py -h
run_alignn_ff.py -h
```

All three are Python executable scripts installed to your environment's `bin/` directory
— you do not need to provide an absolute path.

## Common issues

!!! warning "DGL + CUDA mismatches"
    The most common install problem is a DGL build that does not match your CUDA version.
    If you see import errors about `libtorch_cuda.so` or similar, reinstall DGL from the
    wheel index matching your CUDA driver.

- Use `batch_size` of 32 or 64 for real trainings (the examples ship with `batch_size: 2`).
- Complex `.cif` and `.pdb` files may require `cif2cell==2.0.0a3` and `pytraj`
  respectively.
- `pandas >= 1.2.3` is required.
- From March 2024, `pytorch-ignite` is no longer required (removed for conda-forge
  compatibility).

See the [Notes & FAQ](notes.md) for more tips.
