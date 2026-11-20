from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from src.models.base import BaseDetector


class IsolationForestDetector(BaseDetector):
    """Unsupervised, tree-based. Fast, needs no labels. Trained on BENIGN windows only."""
    name = "iforest"

    def __init__(self, n_estimators=200, max_samples=1024, random_state=42, n_jobs=-1):
        self.n_estimators, self.max_samples = n_estimators, max_samples
        self.random_state, self.n_jobs = random_state, n_jobs
        self.model = None

    def fit(self, X, y=None):
        ms = min(int(self.max_samples), len(X))
        self.model = IsolationForest(n_estimators=self.n_estimators, max_samples=ms, contamination="auto",
                                     random_state=self.random_state, n_jobs=self.n_jobs).fit(X)
        return self

    def score(self, X):
        return -self.model.decision_function(X)
