"""Classical X25519 key exchange with HKDF-SHA-256 session keys.

This module is an educational baseline for the later hybrid design. X25519
establishes a shared secret, while HKDF derives a fixed-size session key from
that secret. Neither operation authenticates the communicating parties.
"""

from __future__ import annotations

from typing import Final

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


DEFAULT_HKDF_INFO: Final[bytes] = b"post-quantum-zero-trust-mesh/classical-ecdh/v1"
DEFAULT_SESSION_KEY_LENGTH: Final[int] = 32
_MAX_HKDF_LENGTH: Final[int] = 255 * hashes.SHA256().digest_size
_BYTES_LIKE = (bytes, bytearray, memoryview)


def generate_key_pair() -> tuple[X25519PrivateKey, X25519PublicKey]:
    """Generate and return a fresh X25519 private/public key pair."""

    private_key = X25519PrivateKey.generate()
    return private_key, private_key.public_key()


def derive_shared_secret(
    private_key: X25519PrivateKey,
    peer_public_key: X25519PublicKey,
) -> bytes:
    """Derive an X25519 shared secret using a peer's public key.

    ``TypeError`` is raised for the wrong key object types. Backend errors such
    as a rejected low-order public key are deliberately allowed to propagate.
    """

    if not isinstance(private_key, X25519PrivateKey):
        raise TypeError("private_key must be an X25519PrivateKey")
    if not isinstance(peer_public_key, X25519PublicKey):
        raise TypeError("peer_public_key must be an X25519PublicKey")
    return private_key.exchange(peer_public_key)


def _to_bytes(value: bytes | bytearray | memoryview, name: str) -> bytes:
    """Convert supported byte containers to immutable bytes."""

    if not isinstance(value, _BYTES_LIKE):
        raise TypeError(f"{name} must be bytes-like")
    return bytes(value)


def derive_session_key(
    shared_secret: bytes | bytearray | memoryview,
    salt: bytes | bytearray | memoryview | None,
    info: bytes | bytearray | memoryview = DEFAULT_HKDF_INFO,
    length: int = DEFAULT_SESSION_KEY_LENGTH,
) -> bytes:
    """Derive a session key from an ECDH secret using HKDF-SHA-256.

    ``salt`` is a public, per-session handshake value. It may be generated
    with a cryptographically secure random generator and sent alongside the
    public keys; it is not a password or a replacement for authentication.
    Both parties must use the same salt and context ``info``.
    """

    secret_bytes = _to_bytes(shared_secret, "shared_secret")
    if not secret_bytes:
        raise ValueError("shared_secret must not be empty")

    if salt is not None:
        salt = _to_bytes(salt, "salt")
    info = _to_bytes(info, "info")

    if isinstance(length, bool) or not isinstance(length, int):
        raise TypeError("length must be an integer")
    if not 1 <= length <= _MAX_HKDF_LENGTH:
        raise ValueError(f"length must be between 1 and {_MAX_HKDF_LENGTH} bytes")

    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    ).derive(secret_bytes)
