#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths can be overridden with environment variables
CONFIG_FILE = os.environ.get("LLAMAFACTORY_CONFIG", os.path.join(SCRIPT_DIR, "train_config.yaml"))

# Conda activation is optional: leave LLAMAFAC_CONDA_ACTIVATE empty if llamafactory-cli is already on PATH
CONDA_ACTIVATE = os.environ.get("LLAMAFAC_CONDA_ACTIVATE", "")  # e.g. ~/miniconda3/bin/activate
CONDA_ENV = os.environ.get("LLAMAFAC_CONDA_ENV", "llamafac")


def main() -> int:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Configuration file does not exist: {CONFIG_FILE}")
        return 1

    if CONDA_ACTIVATE:
        train_cmd = (
            f"/bin/bash -c 'source {CONDA_ACTIVATE} {CONDA_ENV} && "
            f"llamafactory-cli train {CONFIG_FILE}'"
        )
    else:
        train_cmd = f"llamafactory-cli train {CONFIG_FILE}"

    print("Begin single-card training...")

    try:
        subprocess.run(train_cmd, shell=True, check=True, capture_output=False, text=True, cwd=SCRIPT_DIR)
        print("Training complete!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Training failed, exit code: {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("Training was interrupted by the user.")
        return 1
    except Exception as e:
        print(f"An error occurred during training: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())