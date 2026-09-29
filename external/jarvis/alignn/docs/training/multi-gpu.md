# Multi-GPU & High-Throughput Training

## Multi-GPU (`torchrun`)

ALIGNN supports PyTorch `DistributedDataParallel` launched via `torchrun`:

```bash
torchrun --nproc_per_node=4 train_alignn.py \
  --root_dir DataDir \
  --config config.json \
  --output_dir temp
```

!!! note "Experimental"
    Multi-GPU training is not yet thoroughly tested. Please report issues on GitHub.

### SLURM example

```
#SBATCH -n 4
#SBATCH -N 1
#SBATCH --gres=gpu:4

torchrun --nproc_per_node=4 train_alignn.py \
  --root_dir DataDir --config config.json --output_dir temp
```

Make sure `--nproc_per_node` matches the GPUs requested from the scheduler.

## High-throughput training

For running the same training pipeline across many public datasets, see
[`alignn/scripts/train_*.py`](https://github.com/atomgptlab/alignn/tree/main/alignn/scripts).
These scripts:

- Download datasets via
  [jarvis-tools databases](https://jarvis-tools.readthedocs.io/en/master/databases.html)
  (JARVIS-DFT, Materials Project, QM9_JCTC, …)
- Generate the `id_prop.csv` and per-target configs automatically
- Submit one training job per target property

Adapt the scheduler-specific lines (`sbatch`, `qsub`, …) at the top of each script for
your cluster.

## When to use which

| Situation | Use |
|---|---|
| Single dataset, single target, one node | plain `train_alignn.py` |
| Single dataset, multiple GPUs on one node | `torchrun --nproc_per_node=N` |
| Many datasets / targets, cluster queue | `alignn/scripts/train_*.py` |
