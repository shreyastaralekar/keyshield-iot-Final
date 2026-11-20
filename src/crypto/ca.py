"""A minimal certificate authority: issues EC (P-256) device certificates and maintains a real X.509 CRL.

This is for SIMULATION only (private keys live in process memory). Never reuse this code to protect real
devices. Uses only the standard `cryptography` library primitives; no custom cryptographic code is written.
"""
from __future__ import annotations

import datetime as dt

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CURVE = ec.SECP256R1()


class RootCA:
    def __init__(self, cn: str = "KeyShield-IoT Root CA") -> None:
        self.private_key = ec.generate_private_key(CURVE)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
        now = dt.datetime.now(dt.timezone.utc)
        self.certificate = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(self.private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=1))
            .not_valid_after(now + dt.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(self.private_key, hashes.SHA256())
        )
        self._device_certs: dict[str, x509.Certificate] = {}
        self._device_keys: dict[str, ec.EllipticCurvePrivateKey] = {}
        self._revoked: dict[int, dict] = {}   # serial -> {device_id, reason, revoked_at}
        self._crl_number = 0

    def issue_device_cert(self, device_id: str, days_valid: int = 365) -> x509.Certificate:
        key = ec.generate_private_key(CURVE)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, device_id)])
        now = dt.datetime.now(dt.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(self.certificate.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=1))
            .not_valid_after(now + dt.timedelta(days=days_valid))
            .sign(self.private_key, hashes.SHA256())
        )
        self._device_certs[device_id] = cert
        self._device_keys[device_id] = key
        return cert

    def cert_of(self, device_id: str) -> x509.Certificate:
        return self._device_certs[device_id]

    def revoke(self, device_id: str, reason: str = "key_compromise") -> None:
        cert = self._device_certs[device_id]
        self._revoked[cert.serial_number] = {"device_id": device_id, "reason": reason,
                                             "revoked_at": dt.datetime.now(dt.timezone.utc)}

    def is_revoked(self, device_id: str) -> bool:
        cert = self._device_certs.get(device_id)
        return cert is not None and cert.serial_number in self._revoked

    def build_crl(self) -> x509.CertificateRevocationList:
        """A real, ECDSA-signed X.509 CRL. Call after any revoke() to get the current list."""
        self._crl_number += 1
        now = dt.datetime.now(dt.timezone.utc)
        builder = (x509.CertificateRevocationListBuilder()
                  .issuer_name(self.certificate.subject)
                  .last_update(now).next_update(now + dt.timedelta(days=1)))
        for serial, info in self._revoked.items():
            builder = builder.add_revoked_certificate(
                x509.RevokedCertificateBuilder().serial_number(serial).revocation_date(info["revoked_at"]).build()
            )
        return builder.sign(private_key=self.private_key, algorithm=hashes.SHA256())

    def public_bytes(self) -> bytes:
        return self.certificate.public_bytes(serialization.Encoding.PEM)
