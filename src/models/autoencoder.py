from __future__ import annotations

import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor

from src.models.base import BaseDetector


class AutoencoderDetector(BaseDetector):
    """Deep (dense) autoencoder trained to reconstruct BENIGN windows; score = reconstruction error (MSE).
    Implemented with scikit-learn's MLPRegressor (input -> bottleneck -> input), so it runs on any CPU without PyTorch."""
    name = "ae"

    def __init__(self, hidden=(64, 32, 16, 32, 64), max_iter=200, random_state=42, alpha=1e-4):
        self.hidden, self.max_iter, self.random_state, self.alpha = tuple(hidden), max_iter, random_state, alpha
        self.model = None

    def fit(self, X, y=None):
        self.model = MLPRegressor(hidden_layer_sizes=self.hidden, activation="relu", solver="adam", alpha=self.alpha,
                                  batch_size=256, learning_rate_init=1e-3, max_iter=self.max_iter,
                                  early_stopping=True, validation_fraction=0.1, n_iter_no_change=10,
                                  random_state=self.random_state)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.model.fit(X, X)
        return self

    def score(self, X):
        recon = self.model.predict(X)
        return ((recon - X) ** 2).mean(axis=1)
