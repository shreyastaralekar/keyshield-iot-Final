"""KeyManager: implements the contract in src/contracts.py. Ties the CA (certs, CRL) to the session layer
(ECDH/HKDF/AES-GCM) and an audit log. AI code never touches this file's cryptography; it only calls
rotate()/revoke() (see src/engine in later batches)."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from src.crypto.audit_log import AuditLog
from src.crypto.ca import RootCA
from src.crypto.errors import RevokedError, StaleEpochError, UnknownDeviceError
from src.crypto.session import NonceCounter, aead_decrypt, aead_encrypt, establish_epoch_key

_HEADER = struct.Struct(">I")   # 4-byte epoch prefix on every ciphertext blob


@dataclass
class _DeviceState:
    epoch: int = -1
    key: bytes | None = None
    nonce_ctr: NonceCounter | None = None
    history: dict = field(default_factory=dict)   # epoch -> key (kept ONLY so tests can show old/new keys differ)


class KeyManager:
    def __init__(self, ca: RootCA | None = None, audit: AuditLog | None = None) -> None:
        self.ca = ca or RootCA()
        self.audit = audit or AuditLog(self.ca)
        self._devices: dict[str, _DeviceState] = {}

    def _get(self, device_id: str) -> _DeviceState:
        if device_id not in self._devices:
            raise UnknownDeviceError(device_id)
        return self._devices[device_id]

    def _check_live(self, device_id: str) -> _DeviceState:
        st = self._get(device_id)
        if self.ca.is_revoked(device_id):
            raise RevokedError(device_id)
        return st

    def enroll(self, device_id: str) -> None:
        self.ca.issue_device_cert(device_id)
        self._devices[device_id] = _DeviceState()
        self.audit.append(device_id, "ENROLL", epoch=-1, reason="initial enrolment")
        self.establish_session(device_id)

    def establish_session(self, device_id: str) -> int:
        st = self._check_live(device_id)
        st.epoch += 1
        st.key = establish_epoch_key(device_id, st.epoch)
        st.nonce_ctr = NonceCounter()
        st.history[st.epoch] = st.key
        self.audit.append(device_id, "SESSION", epoch=st.epoch, reason="session established")
        return st.epoch

    def rotate(self, device_id: str, reason: str = "anomaly_score_high") -> int:
        st = self._check_live(device_id)
        st.epoch += 1
        st.key = establish_epoch_key(device_id, st.epoch)
        st.nonce_ctr = NonceCounter()
        st.history[st.epoch] = st.key
        self.audit.append(device_id, "ROTATE", epoch=st.epoch, reason=reason)
        return st.epoch

    def revoke(self, device_id: str, reason: str = "anomaly_score_critical") -> None:
        st = self._get(device_id)
        self.ca.revoke(device_id, reason)
        st.key = None
        self.audit.append(device_id, "REVOKE", epoch=st.epoch, reason=reason)

    def is_valid(self, device_id: str, epoch: int) -> bool:
        if device_id not in self._devices or self.ca.is_revoked(device_id):
            return False
        return self._devices[device_id].epoch == epoch

    def encrypt(self, device_id: str, plaintext: bytes) -> bytes:
        st = self._check_live(device_id)
        if st.key is None:
            raise StaleEpochError(f"{device_id} has no active session key")
        nonce = st.nonce_ctr.next()
        aad = f"{device_id}|{st.epoch}".encode()
        ct = aead_encrypt(st.key, nonce, plaintext, aad)
        return _HEADER.pack(st.epoch) + nonce + ct

    def decrypt(self, device_id: str, blob: bytes) -> bytes:
        st = self._get(device_id)
        (epoch,) = _HEADER.unpack(blob[:4])
        nonce, ct = blob[4:16], blob[16:]
        if not self.is_valid(device_id, epoch):
            raise StaleEpochError(f"{device_id} epoch {epoch} is not the current valid epoch")
        aad = f"{device_id}|{epoch}".encode()
        return aead_decrypt(st.key, nonce, ct, aad)

    # --- test / benchmarking helpers (not part of the Protocol contract) ---
    def key_for_epoch(self, device_id: str, epoch: int) -> bytes:
        return self._get(device_id).history[epoch]

    def current_epoch(self, device_id: str) -> int:
        return self._get(device_id).epoch
