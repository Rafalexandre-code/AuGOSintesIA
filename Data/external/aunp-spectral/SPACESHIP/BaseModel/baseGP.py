"""
Gaussian Process Models for Classification and Regression

This module provides GP model implementations using GPyTorch:
- ExactGPModel: Multi-task exact GP for multi-class classification
- GPClassificationModel: Variational GP for binary classification
- WeightedVGP: Weighted variational GP with class balancing support
"""

import gpytorch
from gpytorch.models import AbstractVariationalGP, ApproximateGP
from gpytorch.variational import CholeskyVariationalDistribution, VariationalStrategy


class ExactGPModel(gpytorch.models.ExactGP):
    """Multi-task Exact GP model for multi-class learning."""

    def __init__(self, train_x, train_y, likelihood, num_tasks):
        super().__init__(train_x, train_y, likelihood)
        self.num_tasks = num_tasks

        self.mean_module = gpytorch.means.MultitaskMean(
            gpytorch.means.ConstantMean(), num_tasks=num_tasks
        )

        base_kernel = gpytorch.kernels.RBFKernel()
        base_kernel.lengthscale = 0.08

        self.covar_module = gpytorch.kernels.MultitaskKernel(
            base_kernel, num_tasks=num_tasks, rank=1
        )

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultitaskMultivariateNormal(mean_x, covar_x)


class GPClassificationModel(AbstractVariationalGP):
    """Variational GP model for binary classification."""

    def __init__(self, train_x):
        variational_distribution = CholeskyVariationalDistribution(train_x.size(0))
        variational_strategy = VariationalStrategy(self, train_x, variational_distribution)
        super().__init__(variational_strategy)

        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.RBFKernel())

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)


class WeightedVGP(ApproximateGP):
    """Variational GP with class weighting for imbalanced datasets."""

    def __init__(self, train_x, likelihood, class_weights):
        variational_distribution = CholeskyVariationalDistribution(train_x.size(0))
        variational_strategy = VariationalStrategy(
            self, train_x, variational_distribution, learn_inducing_locations=True
        )
        super().__init__(variational_strategy)

        self.mean_module = gpytorch.means.ZeroMean()
        self.covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.RBFKernel())
        self.class_weights = class_weights

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)
