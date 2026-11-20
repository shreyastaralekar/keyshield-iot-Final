"""Common base for all detectors (follows the Detector contract in src/contracts.py).
Convention: score() returns a value where HIGHER = MORE ANOMALOUS."""
from __future__ import annotations

import joblib


class BaseDetector:
    name = "base"
    supervised = False

    def fit(self, X, y=None):
        raise NotImplementedError

    def score(self, X):
        raise NotImplementedError

    def save(self, path) -> None:
        joblib.dump(self, path)

    def load(self, path) -> None:
        self.__dict__.update(joblib.load(path).__dict__)
