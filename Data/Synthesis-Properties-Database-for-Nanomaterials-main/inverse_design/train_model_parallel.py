#!/usr/bin/env python3
"""
Model parallel training script - Full parameter fine-tuning on dual GPUs using DeepSpeed ZeRO-3
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.environ.get("LLAMAFACTORY_CONFIG", os.path.join(SCRIPT_DIR, "train_config_model_parallel.yaml"))
# Optional conda activation (leave empty if llamafactory-cli is already on PATH)
CONDA_ACTIVATE = os.environ.get("LLAMAFAC_CONDA_ACTIVATE", "")
CONDA_ENV = os.environ.get("LLAMAFAC_CONDA_ENV", "llamafac")

def setup_environment():
    """Set up model parallel training environment variables"""
    # Set GPUs to use
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    
    # NCCL optimization settings
    os.environ["NCCL_DEBUG"] = "INFO"
    os.environ["NCCL_SOCKET_IFNAME"] = "lo"
    os.environ["NCCL_IB_DISABLE"] = "1"
    
    # DeepSpeed and model parallel settings
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    print("Environment variables setup completed:")
    print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES')}")
    print(f"PYTORCH_CUDA_ALLOC_CONF: {os.environ.get('PYTORCH_CUDA_ALLOC_CONF')}")

def run_training():
    """Run model parallel training"""
    config_file = CONFIG_FILE
    
    # Check if config file exists
    if not os.path.exists(config_file):
        print(f"Error: Config file {config_file} does not exist")
        return False
    
    # Build training command
    cmd = [
        "llamafactory-cli",
        "train",
        config_file
    ]
    
    print("Starting model parallel training...")
    print(f"Training command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Execute training command
        result = subprocess.run(cmd, check=True, cwd=SCRIPT_DIR)
        print("Training completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Training failed, exit code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("Training interrupted by user")
        return False
    except Exception as e:
        print(f"Error occurred during training: {e}")
        return False

def main():
    """Main function"""
    print("Qwen3-0.6B Model Parallel Training Script")
    print("Full parameter fine-tuning on dual GPUs using DeepSpeed ZeRO-3")
    print("=" * 60)
    
    # Set environment variables
    env_vars = {
        'CUDA_VISIBLE_DEVICES': '0,1',
        'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True',
        'NCCL_DEBUG': 'INFO',
        'DEEPSPEED_LOG_LEVEL': 'INFO',
        'DISABLE_ARGS_MODIFICATION': '1',  # Disable argument modification
        'TORCH_DISTRIBUTED_DEBUG': 'DETAIL'  # Enable distributed debugging
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("Environment variables setup completed:")
    for key, value in env_vars.items():
        print(f"{key}: {value}")
    
    print("\nStarting model parallel training...")
    
    # Training command - activate conda environment and run
    config_path = CONFIG_FILE
    if CONDA_ACTIVATE:
        train_cmd = f"/bin/bash -c 'source {CONDA_ACTIVATE} {CONDA_ENV} && llamafactory-cli train {config_path}'"
    else:
        train_cmd = f"llamafactory-cli train {config_path}"
    
    print(f"Training command: {train_cmd}")
    print("=" * 60)
    
    try:
        # Execute training
        result = subprocess.run(train_cmd, shell=True, check=True, 
                              capture_output=False, text=True, cwd=SCRIPT_DIR)
        print("Model parallel training completed!")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during training: {e}")
        print("Model parallel training failed!")
        return 1
    except FileNotFoundError as e:
        print(f"Error occurred during training: {e}")
        print("Model parallel training failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
