from __future__ import annotations

from src.models.autoencoder import AutoencoderDetector
from src.models.iforest import IsolationForestDetector
from src.models.ocsvm import OneClassSVMDetector
from src.models.rf_reference import RandomForestReference

MODEL_REGISTRY = {
    "iforest": IsolationForestDetector,
    "ocsvm": OneClassSVMDetector,
    "ae": AutoencoderDetector,
    "rf": RandomForestReference,
}

# parameters that belong to the data preparation, not the model constructor
NON_MODEL_PARAMS = {"rf": {"windows_per_label"}}


def build(name: str, params: dict | None = None, seed: int = 42):
    params = dict(params or {})
    for k in NON_MODEL_PARAMS.get(name, ()):
        params.pop(k, None)
    return MODEL_REGISTRY[name](random_state=seed, **params)
