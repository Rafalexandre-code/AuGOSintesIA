"""MLP (Multi-Layer Perceptron) classifier using Keras."""

import torch
import numpy as np
from keras import backend as K
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping
from sklearn.metrics import accuracy_score

from util import convert_vector_to_matrix


class MLP:
    """Multi-Layer Perceptron classifier with standardized train/test interface."""

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

        self.mlp_parameters = {
            "hidden_dim": 91,
            "epochs": 95,
            "activation": "relu",
            "batch_size": 100,
        }

    def create_model(self):
        K.clear_session()

        hidden_dim = int(self.mlp_parameters["hidden_dim"])
        act_fn = self.mlp_parameters["activation"]
        data_dim = self.x_train.shape[1]

        self.model = Sequential()
        self.model.add(Dense(hidden_dim, input_dim=data_dim, activation=act_fn))
        self.model.add(Dense(hidden_dim, activation=act_fn))
        self.model.add(Dense(2, activation="softmax"))

        self.model.compile(
            loss="categorical_crossentropy", optimizer="adam", metrics=["acc"]
        )

    def fit(self):
        if len(self.y_train.shape) == 1:
            y_train = convert_vector_to_matrix(self.y_train)

        idx = np.random.permutation(len(self.x_train[:, 0]))
        train_idx = idx[: int(len(idx) * 0.9)]
        valid_idx = idx[int(len(idx) * 0.9) :]

        x_valid = self.x_train[valid_idx, :]
        y_valid = y_train[valid_idx, :]
        x_train = self.x_train[train_idx, :]
        y_train = y_train[train_idx, :]

        es = EarlyStopping(
            monitor="val_loss",
            mode="min",
            verbose=1,
            restore_best_weights=True,
            patience=50,
        )

        self.model.fit(
            x_train,
            y_train,
            validation_data=(x_valid, y_valid),
            epochs=self.mlp_parameters["epochs"],
            batch_size=self.mlp_parameters["batch_size"],
            verbose=0,
            callbacks=[es],
        )

    def predict(self):
        y_test_hat = self.model.predict(self.x_test)
        y_test_pred = (y_test_hat[:, 0] < y_test_hat[:, 1]).astype(int)
        return accuracy_score(self.y_test.numpy(), y_test_pred)

    def sample_model(self, unlab):
        unlab_tensor = torch.Tensor(np.array(unlab))
        result = self.model.predict(unlab_tensor)
        return (result[:, 0] < result[:, 1]).astype(int)

    def probability_model(self, unlab):
        unlab_tensor = torch.Tensor(np.array(unlab))
        result = self.model.predict(unlab_tensor)
        return result[:, 1]
