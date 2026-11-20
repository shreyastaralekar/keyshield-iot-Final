"""A fast, dependency-free stand-in for KeyManager (src/contracts.py) used to test policies and the
mitigation state machine in isolation, without running real cryptography on every window."""
from __future__ import annotations


class MockKeyManager:
    def __init__(self):
        self.calls: list[tuple] = []
        self._epoch: dict[str, int] = {}
        self._revoked: set[str] = set()

    def enroll(self, device_id: str) -> None:
        self._epoch[device_id] = 0
        self.calls.append(("enroll", device_id))

    def establish_session(self, device_id: str) -> int:
        self._epoch[device_id] = self._epoch.get(device_id, -1) + 1
        self.calls.append(("establish_session", device_id))
        return self._epoch[device_id]

    def rotate(self, device_id: str, reason: str = "") -> int:
        self._epoch[device_id] = self._epoch.get(device_id, -1) + 1
        self.calls.append(("rotate", device_id, reason))
        return self._epoch[device_id]

    def revoke(self, device_id: str, reason: str = "") -> None:
        self._revoked.add(device_id)
        self.calls.append(("revoke", device_id, reason))

    def is_valid(self, device_id: str, epoch: int) -> bool:
        return device_id not in self._revoked and self._epoch.get(device_id) == epoch

    def encrypt(self, device_id: str, plaintext: bytes) -> bytes:
        return plaintext

    def decrypt(self, device_id: str, blob: bytes) -> bytes:
        return blob

    def n_calls(self, op: str) -> int:
        return sum(1 for c in self.calls if c[0] == op)
