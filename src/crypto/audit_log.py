"""A hash-chained, ECDSA-signed audit log for every key event (ENROLL/SESSION/ROTATE/REVOKE).

Each entry's hash covers the previous entry's hash, so editing or deleting any past entry breaks every
hash after it; each entry is also individually signed with the CA's private key, so an entry cannot be
forged even if the whole chain were replaced. This is a cheap, standard tamper-evidence construction
(comparable to a Merkle/blockchain-style log), not a novel cryptographic contribution.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from src.crypto.ca import RootCA

GENESIS_HASH = "0" * 64


def _entry_digest(device_id: str, event: str, epoch: int, reason: str, ts: str, prev_hash: str) -> bytes:
    payload = json.dumps({"device_id": device_id, "event": event, "epoch": epoch, "reason": reason,
                          "ts": ts, "prev_hash": prev_hash}, sort_keys=True).encode()
    return hashlib.sha256(payload).digest()


def verify_entries(entries: list[dict], public_key) -> tuple[bool, int | None]:
    """Standalone chain+signature check, usable on entries loaded from a JSONL file with only the CA's
    PUBLIC key (e.g. from its certificate) — no private key or live RootCA needed. This is what lets the
    dashboard's "Verify chain" button do a real cryptographic check on a persisted log, not a re-run."""
    prev_hash = GENESIS_HASH
    for i, e in enumerate(entries):
        if e["prev_hash"] != prev_hash:
            return False, i
        digest = _entry_digest(e["device_id"], e["event"], e["epoch"], e["reason"], e["ts"], e["prev_hash"])
        if digest.hex() != e["hash"]:
            return False, i
        try:
            public_key.verify(bytes.fromhex(e["signature"]), digest, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            return False, i
        prev_hash = e["hash"]
    return True, None


class AuditLog:
    def __init__(self, ca: RootCA) -> None:
        self.ca = ca
        self.entries: list[dict] = []

    def append(self, device_id: str, event: str, epoch: int, reason: str) -> dict:
        prev_hash = self.entries[-1]["hash"] if self.entries else GENESIS_HASH
        ts = dt.datetime.now(dt.timezone.utc).isoformat()
        digest = _entry_digest(device_id, event, epoch, reason, ts, prev_hash)
        signature = self.ca.private_key.sign(digest, ec.ECDSA(hashes.SHA256()))
        entry = {"device_id": device_id, "event": event, "epoch": epoch, "reason": reason, "ts": ts,
                 "prev_hash": prev_hash, "hash": digest.hex(), "signature": signature.hex()}
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> tuple[bool, int | None]:
        """Returns (ok, first_bad_index). Checks: hash chain links AND the ECDSA signature of every entry."""
        return verify_entries(self.entries, self.ca.certificate.public_key())

    def to_jsonl(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for e in self.entries:
                f.write(json.dumps(e) + "\n")
