"""Variational Gaussian Process Classifier for binary classification."""

import torch
import numpy as np
import gpytorch
from sklearn.metrics import accuracy_score

from baseGP import GPClassificationModel
from gpytorch.mlls.variational_elbo import VariationalELBO


class vGPC:
    """Variational GP Classifier with standardized train/test interface."""

    def __init__(self, train, test):
        self.train = train
        self.test = test
        self.training_metrics = []

        datasize = len(train[0]["coordination"])
        self.x_train = torch.Tensor(
            np.array([i["coordination"] for i in train]).reshape(-1, datasize)
        ).float()
        self.y_train = torch.Tensor(
            np.array([i["label"] for i in train]).flatten()
        ).float()
        self.x_test = torch.Tensor(
            np.array([i["coordination"] for i in test]).reshape(-1, datasize)
        ).float()
        self.y_test = torch.Tensor(
            np.array([i["label"] for i in test]).flatten()
        ).float()

    def create_model(self):
        self.model = GPClassificationModel(self.x_train)
        self.likelihood = gpytorch.likelihoods.BernoulliLikelihood()

    def fit(self):
        self.model.train()
        self.likelihood.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.1)
        mll = VariationalELBO(self.likelihood, self.model, self.y_train.numel())
        num_points = self.y_train.numel()

        for i in range(50):
            optimizer.zero_grad()
            output = self.model(self.x_train)
            loss = -mll(output, self.y_train)

            with torch.no_grad():
                data_term = mll._log_likelihood_term(output, self.y_train).sum().item()
                kl_term = self.model.variational_strategy.kl_divergence().item()
                ell_bar = data_term / num_points
                denom = num_points * abs(ell_bar)
                ratio = kl_term / denom if denom > 0 else float("inf")

            loss.backward()
            optimizer.step()

        return ratio

    def predict(self):
        self.model.eval()
        self.likelihood.eval()
        with torch.no_grad():
            observed_pred = self.likelihood(self.model(self.x_test))
            result = accuracy_score(
                self.y_test, observed_pred.mean.ge(0.5).float()
            )
        return result

    def sample_model(self, x_new):
        self.model.eval()
        with torch.no_grad():
            x_new_tensor = torch.Tensor(np.array(x_new)).float()
            output = self.model(x_new_tensor)
            observed_pred = self.likelihood(output)
            result = observed_pred.mean.ge(0.5).float().numpy()
        return result

    def probability_model(self, x_new, batch_size=100):
        self.model.eval()
        self.likelihood.eval()
        probabilities = []
        with torch.no_grad():
            for i in range(0, len(x_new), batch_size):
                batch_data = torch.Tensor(x_new[i : i + batch_size]).float()
                observed_pred = self.likelihood(self.model(batch_data))
                probabilities.append(observed_pred.mean.numpy())
        return np.concatenate(probabilities)

    def variance_model(self, x_new, batch_size=100):
        self.model.eval()
        self.likelihood.eval()
        variances = []
        with torch.no_grad():
            for i in range(0, len(x_new), batch_size):
                batch_data = torch.Tensor(x_new[i : i + batch_size]).float()
                observed_pred = self.likelihood(self.model(batch_data))
                variances.append(observed_pred.variance.numpy())
        return np.concatenate(variances)
