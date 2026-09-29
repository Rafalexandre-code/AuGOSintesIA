"""
Wide & Deep Transfer Learning Model for Active Learning.

Supports loading pretrained weights and fine-tuning with frozen non-linear layers.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score


class WideDeepNet(nn.Module):
    """Wide & Deep Neural Network."""

    def __init__(self, input_dim, hidden_dim=384, n_layers=5, dropout=0.05, wide_ratio=4):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.wide_dim = hidden_dim // wide_ratio

        self.wide = nn.Linear(input_dim, self.wide_dim)

        layers = []
        dims = [input_dim] + [hidden_dim] * n_layers
        for i in range(n_layers):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            layers.append(nn.BatchNorm1d(dims[i + 1]))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(dropout))
        self.deep = nn.Sequential(*layers)

        combined_dim = self.wide_dim + hidden_dim
        self.head = nn.Sequential(
            nn.Linear(combined_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3)
        )

    def forward(self, x):
        wide_out = self.wide(x)
        deep_out = self.deep(x)
        combined = torch.cat([wide_out, deep_out], dim=1)
        return self.head(combined)


class WideDeepTransfer:
    """
    Wide & Deep Classifier with Transfer Learning Support.

    Loads pretrained weights and fine-tunes with frozen non-linear layers
    """

    def __init__(self, train, test, pretrained_path: str = None) -> None:
        self.train_data = train
        self.test_data = test
        self.pretrained_path = pretrained_path

        torch.manual_seed(4)
        np.random.seed(4)

        self.hidden_dim = 384
        self.n_layers = 5
        self.dropout = 0.05
        self.batch_size = 32
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        datasize = len([i["coordination"] for i in self.train_data][0])
        self.x_train = np.array([i["coordination"] for i in train]).reshape(-1, datasize)
        self.x_test = np.array([i["coordination"] for i in test]).reshape(-1, datasize)
        self.y_train_raw = np.array([i["label"] for i in train]).reshape(-1)
        self.y_test_raw = np.array([i["label"] for i in test]).reshape(-1)

        self.scaler = StandardScaler()
        self.x_train_scaled = self.scaler.fit_transform(self.x_train)
        self.x_test_scaled = self.scaler.transform(self.x_test)

        self.model = None
        self.input_dim = self.x_train.shape[1]

    def create_model(self) -> None:
        """Create WideDeep model architecture."""
        self.model = WideDeepNet(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            n_layers=self.n_layers,
            dropout=self.dropout
        ).to(self.device)

    def load_pretrained(self, checkpoint_path: str = None) -> None:
        """Load pretrained weights from checkpoint."""
        path = checkpoint_path or self.pretrained_path
        if path is None:
            raise ValueError("No pretrained path provided")

        if self.model is None:
            self.create_model()

        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.scaler.mean_ = checkpoint["scaler_mean"]
        self.scaler.scale_ = checkpoint["scaler_scale"]

    def freeze_non_linear_layers(self) -> list:
        """Freeze non-linear layers, return trainable Linear parameters."""
        linear_params = []
        for module in self.model.modules():
            if isinstance(module, nn.Linear):
                for param in module.parameters():
                    param.requires_grad = True
                    linear_params.append(param)
            elif isinstance(module, (nn.BatchNorm1d, nn.Dropout)):
                for param in module.parameters():
                    param.requires_grad = False
        return linear_params

    def unfreeze_all_layers(self) -> None:
        """Unfreeze all layers for full training."""
        for param in self.model.parameters():
            param.requires_grad = True

    def fit(self, finetune_data: list = None, epochs: int = 50, lr: float = 0.0005) -> None:
        """
        Fine-tune model with frozen non-linear layers.

        Args:
            finetune_data: Data for fine-tuning (if None, uses train_data)
            epochs: Number of fine-tuning epochs
            lr: Learning rate
        """
        if self.model is None:
            self.create_model()

        data = finetune_data if finetune_data else self.train_data
        datasize = len(data[0]["coordination"])
        x_data = np.array([i["coordination"] for i in data]).reshape(-1, datasize)
        y_data = np.array([i["label"] for i in data]).reshape(-1).astype(int)

        x_scaled = self.scaler.transform(x_data)
        X_t = torch.FloatTensor(x_scaled).to(self.device)
        y_t = torch.LongTensor(y_data).to(self.device)

        linear_params = self.freeze_non_linear_layers()
        optimizer = optim.AdamW(linear_params, lr=lr, weight_decay=0.01)
        criterion = nn.CrossEntropyLoss()

        dataset = torch.utils.data.TensorDataset(X_t, y_t)
        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=min(16, len(y_data)),
            shuffle=True,
            drop_last=False
        )

        self.model.train()
        for _ in range(epochs):
            for xb, yb in loader:
                if xb.size(0) <= 1:
                    continue
                optimizer.zero_grad()
                out = self.model(xb)
                loss = criterion(out, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

        self.unfreeze_all_layers()

    def predict(self) -> float:
        """Return accuracy on test set."""
        X_t = torch.FloatTensor(self.x_test_scaled).to(self.device)

        self.model.eval()
        with torch.no_grad():
            pred_classes = self.model(X_t).argmax(1).cpu().numpy()

        return accuracy_score(self.y_test_raw.astype(int), pred_classes)

    def sample_model(self, x_new) -> np.ndarray:
        """Predict class labels for new samples."""
        self.model.eval()
        x_new = np.array(x_new)
        if x_new.ndim == 1:
            x_new = x_new.reshape(1, -1)

        x_scaled = self.scaler.transform(x_new)
        X_t = torch.FloatTensor(x_scaled).to(self.device)

        with torch.no_grad():
            result = self.model(X_t).argmax(1).cpu().numpy()
        return result

    def probability_model(self, x_new) -> np.ndarray:
        """Return class probabilities for new samples."""
        self.model.eval()
        x_new = np.array(x_new)
        if x_new.ndim == 1:
            x_new = x_new.reshape(1, -1)

        x_scaled = self.scaler.transform(x_new)
        X_t = torch.FloatTensor(x_scaled).to(self.device)

        with torch.no_grad():
            probs = torch.softmax(self.model(X_t), dim=1).cpu().numpy()
        return probs

    def variance_model(self, x_new) -> np.ndarray:
        """Return uncertainty estimates using prediction entropy."""
        probs = self.probability_model(x_new)
        entropy = -np.sum(probs * np.log(probs + 1e-10), axis=1)
        return entropy
