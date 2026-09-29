"""
File Manager for JSON and Model Persistence.

Provides utilities for saving/loading JSON data and pickle models.
"""

import json
import pickle
from pathlib import Path


class FileManager:
    """Manages JSON file I/O operations."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_data(self, data: list | dict) -> None:
        """Save data to JSON file."""
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)

    def load_data(self) -> list | dict:
        """Load data from JSON file. Creates empty file if not exists."""
        if not self.path.is_file():
            data = []
            self.save_data(data)

        with open(self.path) as f:
            data = json.load(f)

        return data


class ModelManager:
    """Manages model persistence with pickle."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_model(self, model: object, cycle: int) -> None:
        """Save model to pickle file."""
        with open(self.path / str(cycle), "wb") as fw:
            pickle.dump(model, fw)

    def load_model(self, cycle: int) -> object:
        """Load model from pickle file."""
        with open(self.path / str(cycle), "rb") as f:
            model = pickle.load(f)
        return model
