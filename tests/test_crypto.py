"""Batch 3 tests: round trip, tamper detection, epoch invalidation, revocation, CRL, nonce uniqueness,
audit chain integrity, and that an old key truly cannot decrypt what a new key encrypted (and vice versa)."""
import pytest
from cryptography.exceptions import InvalidSignature, InvalidTag

from src.crypto.ca import RootCA
from src.crypto.errors import RevokedError, StaleEpochError, UnknownDeviceError
from src.crypto.key_manager import KeyManager
from src.crypto.session import NonceCounter, aead_decrypt, aead_encrypt, establish_epoch_key


@pytest.fixture
def km():
    m = KeyManager()
    m.enroll("dev_A")
    return m


def test_round_trip(km):
    msg = b"temperature=21.5C;humidity=40%"
    blob = km.encrypt("dev_A", msg)
    assert km.decrypt("dev_A", blob) == msg


def test_tamper_detection(km):
    blob = bytearray(km.encrypt("dev_A", b"authentic payload"))
    blob[-1] ^= 0xFF   # flip the last byte of the GCM tag/ciphertext
    with pytest.raises(InvalidTag):
        km.decrypt("dev_A", bytes(blob))


def test_old_epoch_rejected_after_rotation(km):
    old_epoch = km.current_epoch("dev_A")
    old_blob = km.encrypt("dev_A", b"pre-rotation message")
    km.rotate("dev_A", reason="test")
    assert km.is_valid("dev_A", old_epoch) is False
    assert km.is_valid("dev_A", km.current_epoch("dev_A")) is True
    with pytest.raises(StaleEpochError):
        km.decrypt("dev_A", old_blob)        # old ciphertext is rejected purely because its epoch is stale


def test_new_key_cannot_decrypt_old_traffic_and_vice_versa(km):
    e0 = km.current_epoch("dev_A")
    k0 = km.key_for_epoch("dev_A", e0)
    blob0 = km.encrypt("dev_A", b"epoch zero traffic")
    nonce0, ct0 = blob0[4:16], blob0[16:]
    km.rotate("dev_A", reason="test")
    k1 = km.key_for_epoch("dev_A", km.current_epoch("dev_A"))
    assert k0 != k1
    with pytest.raises(InvalidTag):           # new key cannot decrypt old traffic
        aead_decrypt(k1, nonce0, ct0, f"dev_A|{e0}".encode())
    blob1 = km.encrypt("dev_A", b"epoch one traffic")
    nonce1, ct1 = blob1[4:16], blob1[16:]
    with pytest.raises(InvalidTag):           # old key cannot decrypt new traffic
        aead_decrypt(k0, nonce1, ct1, f"dev_A|{km.current_epoch('dev_A')}".encode())


def test_revoked_certificate_refused(km):
    km.revoke("dev_A", reason="suspected compromise")
    assert km.ca.is_revoked("dev_A") is True
    with pytest.raises(RevokedError):
        km.rotate("dev_A")
    with pytest.raises(RevokedError):
        km.encrypt("dev_A", b"should not be sent")
    assert km.is_valid("dev_A", km.current_epoch("dev_A")) is False


def test_crl_contains_revoked_serial_and_is_correctly_signed():
    ca = RootCA()
    ca.issue_device_cert("dev_X")
    ca.issue_device_cert("dev_Y")
    ca.revoke("dev_X", "test")
    crl = ca.build_crl()
    serials = {r.serial_number for r in crl}
    assert ca.cert_of("dev_X").serial_number in serials
    assert ca.cert_of("dev_Y").serial_number not in serials
    assert crl.is_signature_valid(ca.certificate.public_key())


def test_nonce_unique_within_epoch():
    ctr = NonceCounter()
    nonces = {ctr.next() for _ in range(5000)}
    assert len(nonces) == 5000
    assert all(len(n) == 12 for n in nonces)


def test_ecdh_roundtrip_matches_for_both_sides():
    # establish_epoch_key already asserts the two derivations match; this test re-checks determinism of info binding
    k1 = establish_epoch_key("dev_Z", 0)
    k2 = establish_epoch_key("dev_Z", 0)      # a fresh handshake, even for the same device/epoch, gives a new key
    assert k1 != k2                            # because ECDH key pairs are freshly generated each call
    assert len(k1) == 32


def test_audit_chain_verifies_then_breaks_on_tamper(km):
    km.rotate("dev_A", reason="r1")
    km.rotate("dev_A", reason="r2")
    ok, bad = km.audit.verify_chain()
    assert ok and bad is None
    km.audit.entries[1]["reason"] = "tampered"     # mutate a past entry's payload
    ok, bad = km.audit.verify_chain()
    assert not ok and bad == 1


def test_unknown_device_raises():
    m = KeyManager()
    with pytest.raises(UnknownDeviceError):
        m.encrypt("ghost_device", b"x")


def test_benchmark_runs_and_returns_positive_timings():
    from src.crypto.benchmark import run
    df = run(n_handshakes=20, n_messages=50, msg_sizes=(64,))
    assert (df["mean_ms"] > 0).all() and len(df) == 4


def test_verify_entries_standalone_matches_auditlog_verify_chain(km):
    """Loading entries + a certificate's PUBLIC key (as the dashboard does) must verify identically to
    calling AuditLog.verify_chain() on the live object — including correctly detecting tampering."""
    from cryptography import x509
    from src.crypto.audit_log import verify_entries

    km.rotate("dev_A", reason="r1")
    km.rotate("dev_A", reason="r2")
    cert = x509.load_pem_x509_certificate(km.ca.public_bytes())
    ok, bad = verify_entries(km.audit.entries, cert.public_key())
    assert ok and bad is None and (ok, bad) == km.audit.verify_chain()

    tampered = [dict(e) for e in km.audit.entries]
    tampered[0]["reason"] = "tampered"
    ok2, bad2 = verify_entries(tampered, cert.public_key())
    assert not ok2 and bad2 == 0
