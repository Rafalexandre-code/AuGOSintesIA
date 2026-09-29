"""
Gaussian Process Classifier for multi-class classification.

Uses MultitaskGP with one-hot encoded labels and class weighting
for imbalanced datasets.
"""

import os
import sys

import torch
import numpy as np
import gpytorch
from sklearn.metrics import accuracy_score

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from baseGP import ExactGPModel


class GPC:
    """Multi-class Gaussian Process Classifier with standardized interface."""

    def __init__(self, train, test, class_weights=None):
        self.train = train
        self.test = test
        torch.manual_seed(52)

        datasize = len(train[0]["coordination"])
        self.x_train = torch.Tensor(
            np.array([i["coordination"] for i in train]).reshape(-1, datasize)
        )
        self.x_test = torch.Tensor(
            np.array([i["coordination"] for i in test]).reshape(-1, datasize)
        )

        self.y_train_raw = torch.Tensor(
            np.array([i["label"] for i in train]).reshape(-1, 1)
        )
        self.y_test_raw = torch.Tensor(
            np.array([i["label"] for i in test]).reshape(-1, 1)
        )

        self.y_train = (
            torch.nn.functional.one_hot(self.y_train_raw.long(), num_classes=3)
            .float()
            .squeeze(1)
        )
        self.y_test = torch.nn.functional.one_hot(
            self.y_test_raw.long(), num_classes=3
        ).float()

        if class_weights is None:
            unique, counts = np.unique(self.y_train_raw.numpy(), return_counts=True)
            total = len(self.y_train_raw)
            weights = total / (len(unique) * counts)
            self.class_weights = torch.FloatTensor(weights)
        else:
            self.class_weights = torch.FloatTensor(class_weights)

    def create_model(self):
        num_tasks = self.y_train.shape[1]
        self.likelihood = gpytorch.likelihoods.MultitaskGaussianLikelihood(
            num_tasks=num_tasks
        )
        self.likelihood.noise = 0.008
        self.model = ExactGPModel(
            self.x_train, self.y_train, self.likelihood, num_tasks=num_tasks
        )

    def fit(self):
        self.model.train()
        likelihood = self.model.likelihood
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.1)
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, self.model)

        nir_weight = 10.0

        for _ in range(50):
            optimizer.zero_grad()
            output = self.model(self.x_train)

            base_loss = -mll(output, self.y_train)

            nir_mask = (self.y_train_raw.squeeze() == 2).float()
            pred_mean = output.mean
            nir_target = self.y_train[:, 2]
            nir_pred = pred_mean[:, 2]
            nir_loss = ((nir_target - nir_pred) ** 2 * nir_mask).mean() * nir_weight

            loss = base_loss + nir_loss
            loss.backward()
            optimizer.step()

    def predict(self):
        self.model.eval()
        likelihood = self.model.likelihood

        with torch.no_grad():
            output = self.model(self.x_test)
            observed_pred = likelihood(output)

            pred_classes = torch.argmax(observed_pred.mean, dim=-1).numpy()
            true_classes = torch.argmax(self.y_test, dim=-1).numpy()

            result = accuracy_score(true_classes, pred_classes)
        return result

    def sample_model(self, x_new):
        self.model.eval()
        x_new_tensor = torch.Tensor(np.array(x_new))

        with torch.no_grad():
            output = self.model(x_new_tensor)
            observed_pred = self.likelihood(output)

            probs = observed_pred.mean.clone()
            probs[:, 2] = probs[:, 2] + 0.03

            result = torch.argmax(probs, dim=-1).numpy()
        return result

    def probability_model(self, x_new):
        self.model.eval()
        likelihood = self.model.likelihood

        with torch.no_grad():
            test_x = torch.Tensor(x_new)
            output = self.model(test_x)
            observed_pred = likelihood(output)

            probs = observed_pred.mean.clone()
            probs[:, 2] = probs[:, 2] + 0.03

        return probs.numpy()

    def variance_model(self, x_new):
        self.model.eval()
        likelihood = self.model.likelihood

        with torch.no_grad():
            test_x = torch.Tensor(x_new)
            output = self.model(test_x)
            observed_pred = likelihood(output)

        return observed_pred.variance.numpy()

    def fine_tuned(self, new_data, epochs=30, lr=0.01):
        """Fine-tune the model with additional data."""
        datasize = len(new_data[0]["coordination"])
        x_new = torch.Tensor(
            np.array([i["coordination"] for i in new_data]).reshape(-1, datasize)
        )
        y_new_raw = torch.Tensor(
            np.array([i["label"] for i in new_data]).reshape(-1, 1)
        )
        y_new = (
            torch.nn.functional.one_hot(y_new_raw.long(), num_classes=3)
            .float()
            .squeeze(1)
        )

        x_all = torch.cat([self.x_train, x_new], dim=0)
        y_all = torch.cat([self.y_train, y_new], dim=0)

        self.model.set_train_data(x_all, y_all, strict=False)

        self.model.train()
        self.likelihood.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(self.likelihood, self.model)

        for _ in range(epochs):
            optimizer.zero_grad()
            output = self.model(x_all)
            loss = -mll(output, y_all)
            loss.backward()
            optimizer.step()

        self.x_train = x_all
        self.y_train = y_all
