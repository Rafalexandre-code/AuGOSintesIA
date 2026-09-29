"""Logistic Regression classifier wrapper with unified interface."""

import torch
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from util import convert_matrix_to_vector


class Logistic:
    """Logistic Regression classifier with standardized train/test interface."""

    def __init__(self, train, test):
        self.train = train
        self.test = test

        datasize = len(train[0]["coordination"])
        self.x_train = torch.Tensor(
            np.array([i["coordination"] for i in train]).reshape(-1, datasize)
        )
        self.y_train = torch.Tensor(
            np.array([i["label"] for i in train]).flatten()
        )
        self.x_test = torch.Tensor(
            np.array([i["coordination"] for i in test]).reshape(-1, datasize)
        )
        self.y_test = torch.Tensor(
            np.array([i["label"] for i in test]).flatten()
        )

    def create_model(self):
        self.model = LogisticRegression()

    def fit(self):
        if len(self.y_train.shape) > 1:
            self.y_train = convert_matrix_to_vector(self.y_train)
        self.model.fit(self.x_train, self.y_train.numpy())

    def predict(self):
        y_test_pred = self.model.predict(self.x_test)
        return accuracy_score(self.y_test.numpy(), y_test_pred)

    def sample_model(self, unlab):
        unlab_tensor = torch.Tensor(np.array(unlab))
        result = self.model.predict_proba(unlab_tensor)[:, 1]
        return (result > 0.5).astype(int)

    def probability_model(self, unlab):
        unlab_tensor = torch.Tensor(np.array(unlab))
        return self.model.predict_proba(unlab_tensor)[:, 1]
