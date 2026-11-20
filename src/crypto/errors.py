"""Exceptions raised by the crypto layer. Kept separate so tests and the engine can catch them precisely."""


class RevokedError(Exception):
    """Raised when an operation is attempted for a device whose certificate has been revoked."""


class StaleEpochError(Exception):
    """Raised when decrypt() is asked to use a key epoch that is no longer the device's current epoch
    (i.e. the device has since been rotated). This is intentional: it enforces that a rotated-away key
    cannot keep being used, even if the ciphertext itself is otherwise valid."""


class UnknownDeviceError(Exception):
    """Raised for any operation on a device_id that was never enrolled."""
