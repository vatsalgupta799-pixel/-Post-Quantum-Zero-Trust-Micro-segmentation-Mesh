"""Standalone ML-KEM-768 key establishment using :mod:`cryptography`.

ML-KEM is a post-quantum key-encapsulation mechanism (KEM).  A recipient
creates a key pair, an initiator encapsulates to the recipient's public key,
and the recipient decapsulates the resulting ciphertext to recover the same
shared secret.  This module intentionally does not authenticate either party
and does not combine ML-KEM with X25519; those are later protocol milestones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM768PublicKey,
)


MLKEM768_SHARED_SECRET_LENGTH: Final[int] = 32


@dataclass(frozen=True)
class EncapsulationResult:
    """The non-key-pair values produced when an initiator encapsulates.

    ``ciphertext`` is sent to the key-pair owner. ``shared_secret`` must be
    treated as secret key material and is intentionally never formatted or
    logged by this module.
    """

    ciphertext: bytes
    shared_secret: bytes


def generate_key_pair() -> tuple[MLKEM768PrivateKey, MLKEM768PublicKey]:
    """Generate a fresh ML-KEM-768 private/public key pair.

    The private key remains with the receiving service. Callers should share
    only the returned public key with an initiating service.
    """

    private_key = MLKEM768PrivateKey.generate()
    return private_key, private_key.public_key()


def encapsulate_shared_secret(public_key: MLKEM768PublicKey) -> EncapsulationResult:
    """Encapsulate a shared secret for ``public_key``.

    ``TypeError`` is raised when a caller supplies a key of the wrong type.
    Backend capability errors, including ``UnsupportedAlgorithm``, are allowed
    to propagate instead of silently selecting another algorithm.
    """

    if not isinstance(public_key, MLKEM768PublicKey):
        raise TypeError("public_key must be an MLKEM768PublicKey")

    shared_secret, ciphertext = public_key.encapsulate()
    return EncapsulationResult(ciphertext=ciphertext, shared_secret=shared_secret)


def decapsulate_shared_secret(
    private_key: MLKEM768PrivateKey,
    ciphertext: bytes,
) -> bytes:
    """Recover the shared secret associated with ``ciphertext``.

    ``TypeError`` is raised for the wrong key or ciphertext type. A malformed
    ciphertext length is validated by the selected library and raises its
    documented ``ValueError``. ML-KEM uses implicit rejection for a
    same-length modified ciphertext, so successful decapsulation alone is not
    evidence that a ciphertext was authentic.
    """

    if not isinstance(private_key, MLKEM768PrivateKey):
        raise TypeError("private_key must be an MLKEM768PrivateKey")
    if not isinstance(ciphertext, bytes):
        raise TypeError("ciphertext must be bytes")

    return private_key.decapsulate(ciphertext)
