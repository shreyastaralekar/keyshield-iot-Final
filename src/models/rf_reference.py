from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier

from src.models.base import BaseDetector


class RandomForestReference(BaseDetector):
    """SUPERVISED reference (closed-world upper bound). Needs labelled attacks, so it cannot be claimed for zero-day
    attacks. Score = predicted attack probability."""
    name = "rf"
    supervised = True

    def __init__(self, n_estimators=200, random_state=42, n_jobs=-1):
        self.n_estimators, self.random_state, self.n_jobs = n_estimators, random_state, n_jobs
        self.model = None

    def fit(self, X, y=None):
        self.model = RandomForestClassifier(n_estimators=self.n_estimators, class_weight="balanced_subsample",
                                            min_samples_leaf=2, random_state=self.random_state, n_jobs=self.n_jobs)
        self.model.fit(X, y)
        return self

    def score(self, X):
        return self.model.predict_proba(X)[:, 1]
