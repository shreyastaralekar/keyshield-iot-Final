from __future__ import annotations

import numpy as np
from sklearn.svm import OneClassSVM

from src.models.base import BaseDetector


class OneClassSVMDetector(BaseDetector):
    """Unsupervised kernel novelty detector. O(n^2) training, so benign training rows are subsampled."""
    name = "ocsvm"

    def __init__(self, nu=0.02, gamma="scale", max_train=30000, random_state=42, chunk=5000):
        self.nu, self.gamma, self.max_train = nu, gamma, max_train
        self.random_state, self.chunk = random_state, chunk
        self.model = None

    def fit(self, X, y=None):
        if len(X) > self.max_train:
            idx = np.random.default_rng(self.random_state).choice(len(X), self.max_train, replace=False)
            X = X[idx]
        self.model = OneClassSVM(kernel="rbf", nu=self.nu, gamma=self.gamma).fit(X)
        return self

    def score(self, X):
        out = [-self.model.decision_function(X[i:i + self.chunk]) for i in range(0, len(X), self.chunk)]
        return np.concatenate(out)
