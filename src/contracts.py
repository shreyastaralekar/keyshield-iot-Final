"""Interfaces (contracts) shared by all tracks. Do not change casually: every track codes against this file.

Tracks: Data -> Detection -> Crypto -> Engine -> Evaluation. They are merged in Phase 5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

Action = Literal["NONE", "WARN", "ROTATE", "REVOKE"]


@dataclass
class Window:
    device_id: str
    t: int                  # window index; 1 window = 60 simulated seconds (see configs/default.yaml)
    x: np.ndarray           # float32 feature vector, shape (F,)
    label: int              # 0 benign, 1 attack (ground truth, never shown to detectors at test time)
    attack_cat: str         # 'Benign' or an attack category


class Detector(Protocol):
    def fit(self, X_benign: np.ndarray) -> None: ...
    def score(self, X: np.ndarray) -> np.ndarray: ...   # higher = more anomalous
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...


class KeyManager(Protocol):
    def enroll(self, device_id: str) -> None: ...
    def establish_session(self, device_id: str) -> int: ...      # returns epoch
    def rotate(self, device_id: str, reason: str) -> int: ...    # returns new epoch
    def revoke(self, device_id: str, reason: str) -> None: ...
    def is_valid(self, device_id: str, epoch: int) -> bool: ...
    def encrypt(self, device_id: str, plaintext: bytes) -> bytes: ...
    def decrypt(self, device_id: str, blob: bytes) -> bytes: ...


class TriggerPolicy(Protocol):
    def decide(self, state: dict, score: float, t: int) -> Action: ...
