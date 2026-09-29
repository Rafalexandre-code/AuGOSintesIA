"""XGBoost Classifier wrapper with unified interface."""

import torch
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score

from util import convert_matrix_to_vector


class Xgboost:
    """XGBoost classifier with standardized train/test interface."""

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
        self.model = xgb.XGBClassifier()

    def fit(self):
        if len(self.y_train.shape) > 1:
            self.y_train = convert_matrix_to_vector(self.y_train)
        self.model.fit(self.x_train.numpy(), self.y_train.numpy())

    def predict(self):
        y_test_pred = self.model.predict(self.x_test.numpy())
        return accuracy_score(self.y_test.numpy(), y_test_pred)

    def sample_model(self, x_new):
        x_new_tensor = torch.Tensor(x_new)
        return self.model.predict(x_new_tensor.numpy())

    def probability_model(self, x_new):
        x_new_tensor = torch.Tensor(x_new)
        prob_pred = self.model.predict_proba(x_new_tensor.numpy())
        return prob_pred[:, 1]
