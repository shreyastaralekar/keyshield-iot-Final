"""Ephemeral ECDH -> HKDF-SHA256 -> AES-256-GCM session cryptography.

Each key *epoch* gets a fresh ECDH exchange (forward secrecy: compromising one epoch's key does not expose
other epochs). All primitives come from the `cryptography` library; no custom crypto math.
"""
from __future__ import annotations

import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.crypto.ca import CURVE


def ephemeral_keypair() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(CURVE)


def derive_session_key(priv: ec.EllipticCurvePrivateKey, peer_pub: ec.EllipticCurvePublicKey,
                       device_id: str, epoch: int) -> bytes:
    """ECDH shared secret -> HKDF-SHA256 -> 32-byte AES-256 key, bound to device_id and epoch."""
    shared = priv.exchange(ec.ECDH(), peer_pub)
    info = f"keyshield-iot|{device_id}|epoch={epoch}".encode()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(shared)


def establish_epoch_key(device_id: str, epoch: int) -> bytes:
    """Simulated handshake: both sides' ephemeral key pairs are generated here (single simulated process),
    but a REAL ECDH exchange is performed, so the derived key is cryptographically identical to what a
    genuine two-party handshake would produce. Documented as a simplification in the report."""
    a, b = ephemeral_keypair(), ephemeral_keypair()
    k1 = derive_session_key(a, b.public_key(), device_id, epoch)
    k2 = derive_session_key(b, a.public_key(), device_id, epoch)
    assert k1 == k2, "ECDH shared secrets did not match"
    return k1


class NonceCounter:
    """96-bit AES-GCM nonce = 4-byte random session salt + 8-byte big-endian counter.
    Guarantees uniqueness within an epoch as long as the counter does not wrap (2**64 messages)."""

    def __init__(self, salt: bytes | None = None) -> None:
        import os
        self.salt = salt or os.urandom(4)
        self.counter = 0

    def next(self) -> bytes:
        n = self.salt + struct.pack(">Q", self.counter)
        self.counter += 1
        return n


def aead_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    return AESGCM(key).encrypt(nonce, plaintext, aad)


def aead_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(nonce, ciphertext, aad)
