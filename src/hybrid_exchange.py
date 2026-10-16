"""Educational hybrid X25519 and ML-KEM-768 key establishment.

This module composes the independently implemented Day 2 and Day 3 primitives.
It is a prototype, not an authenticated protocol, TLS implementation, or a
production-ready hybrid construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.classical_ecdh import (
    DEFAULT_SESSION_KEY_LENGTH,
    derive_session_key,
    derive_shared_secret,
    generate_key_pair as generate_x25519_key_pair,
)
from src.pqc_mlkem import (
    MLKEM768_SHARED_SECRET_LENGTH,
    decapsulate_shared_secret,
    encapsulate_shared_secret,
    generate_key_pair as generate_mlkem_key_pair,
)


HYBRID_PROTOCOL_ID: Final[bytes] = b"post-quantum-zero-trust-mesh/hybrid-v1"
HYBRID_HKDF_CONTEXT: Final[bytes] = b"post-quantum-zero-trust-mesh/hybrid-hkdf-v1"
X25519_ALGORITHM_ID: Final[bytes] = b"X25519"
MLKEM768_ALGORITHM_ID: Final[bytes] = b"ML-KEM-768"
X25519_SHARED_SECRET_LENGTH: Final[int] = 32


@dataclass(frozen=True)
class HybridExchangeResult:
    """In-memory results from a successful simulated hybrid exchange.

    Shared secrets and session keys are present solely so local callers can
    verify agreement. They must not be logged, persisted, or transmitted.
    """

    x25519_shared_secret_a: bytes
    x25519_shared_secret_b: bytes
    mlkem_shared_secret_a: bytes
    mlkem_shared_secret_b: bytes
    transcript: bytes
    session_key_a: bytes
    session_key_b: bytes


def _required_bytes(value: bytes, name: str) -> bytes:
    """Return a required byte string or raise a clear input error."""

    if not isinstance(value, bytes):
        raise TypeError(f"{name} must be bytes")
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _encode_fields(*fields: bytes) -> bytes:
    """Encode ordered fields as four-byte lengths followed by their values."""

    return b"".join(len(field).to_bytes(4, "big") + field for field in fields)


def build_handshake_transcript(
    service_a_x25519_public_key: X25519PublicKey,
    service_b_x25519_public_key: X25519PublicKey,
    service_b_mlkem_public_key: MLKEM768PublicKey,
    mlkem_ciphertext: bytes,
) -> bytes:
    """Build the canonical public transcript used by the hybrid derivation.

    Fields are length-prefixed in this exact order: protocol identifier,
    X25519 algorithm identifier, Service A X25519 public key, Service B
    X25519 public key, ML-KEM algorithm identifier, Service B ML-KEM public
    key, and the ML-KEM ciphertext. Private keys and shared secrets are never
    included.
    """

    if not isinstance(service_a_x25519_public_key, X25519PublicKey):
        raise TypeError("service_a_x25519_public_key must be an X25519PublicKey")
    if not isinstance(service_b_x25519_public_key, X25519PublicKey):
        raise TypeError("service_b_x25519_public_key must be an X25519PublicKey")
    if not isinstance(service_b_mlkem_public_key, MLKEM768PublicKey):
        raise TypeError("service_b_mlkem_public_key must be an MLKEM768PublicKey")

    ciphertext = _required_bytes(mlkem_ciphertext, "mlkem_ciphertext")
    return _encode_fields(
        HYBRID_PROTOCOL_ID,
        X25519_ALGORITHM_ID,
        service_a_x25519_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw),
        service_b_x25519_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw),
        MLKEM768_ALGORITHM_ID,
        service_b_mlkem_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw),
        ciphertext,
    )


def derive_hybrid_session_key(
    x25519_shared_secret: bytes,
    mlkem_shared_secret: bytes,
    transcript: bytes,
    context: bytes = HYBRID_HKDF_CONTEXT,
) -> bytes:
    """Derive a 32-byte hybrid session key with transcript-bound HKDF-SHA-256.

    Both 32-byte component secrets are length-prefixed before becoming HKDF
    input keying material. The SHA-256 transcript hash is public and used as
    the HKDF salt; ``context`` plus that hash become HKDF ``info``. ``TypeError``
    and ``ValueError`` reject invalid input rather than falling back to either
    individual component.
    """

    x25519_secret = _required_bytes(x25519_shared_secret, "x25519_shared_secret")
    mlkem_secret = _required_bytes(mlkem_shared_secret, "mlkem_shared_secret")
    transcript_bytes = _required_bytes(transcript, "transcript")
    context_bytes = _required_bytes(context, "context")

    if len(x25519_secret) != X25519_SHARED_SECRET_LENGTH:
        raise ValueError("x25519_shared_secret must be 32 bytes")
    if len(mlkem_secret) != MLKEM768_SHARED_SECRET_LENGTH:
        raise ValueError("mlkem_shared_secret must be 32 bytes")

    transcript_hash = sha256(transcript_bytes).digest()
    input_key_material = _encode_fields(x25519_secret, mlkem_secret)
    info = _encode_fields(context_bytes, transcript_hash)
    return derive_session_key(
        input_key_material,
        salt=transcript_hash,
        info=info,
        length=DEFAULT_SESSION_KEY_LENGTH,
    )


def perform_hybrid_exchange() -> HybridExchangeResult:
    """Run a complete local two-service hybrid key-establishment exchange.

    Cryptographic failures propagate to the caller. If either component or the
    final session keys disagree, the exchange aborts with ``RuntimeError``;
    it never silently continues with classical-only or ML-KEM-only material.
    """

    private_a, public_a = generate_x25519_key_pair()
    private_b, public_b = generate_x25519_key_pair()
    private_mlkem_b, public_mlkem_b = generate_mlkem_key_pair()

    x25519_secret_a = derive_shared_secret(private_a, public_b)
    x25519_secret_b = derive_shared_secret(private_b, public_a)
    if x25519_secret_a != x25519_secret_b:
        raise RuntimeError("X25519 shared secrets do not match")

    encapsulation = encapsulate_shared_secret(public_mlkem_b)
    mlkem_secret_b = decapsulate_shared_secret(
        private_mlkem_b,
        encapsulation.ciphertext,
    )
    if encapsulation.shared_secret != mlkem_secret_b:
        raise RuntimeError("ML-KEM shared secrets do not match")

    transcript_a = build_handshake_transcript(
        public_a,
        public_b,
        public_mlkem_b,
        encapsulation.ciphertext,
    )
    transcript_b = build_handshake_transcript(
        public_a,
        public_b,
        public_mlkem_b,
        encapsulation.ciphertext,
    )
    if transcript_a != transcript_b:
        raise RuntimeError("handshake transcripts do not match")

    session_key_a = derive_hybrid_session_key(
        x25519_secret_a,
        encapsulation.shared_secret,
        transcript_a,
    )
    session_key_b = derive_hybrid_session_key(
        x25519_secret_b,
        mlkem_secret_b,
        transcript_b,
    )
    if session_key_a != session_key_b:
        raise RuntimeError("hybrid session keys do not match")

    return HybridExchangeResult(
        x25519_shared_secret_a=x25519_secret_a,
        x25519_shared_secret_b=x25519_secret_b,
        mlkem_shared_secret_a=encapsulation.shared_secret,
        mlkem_shared_secret_b=mlkem_secret_b,
        transcript=transcript_a,
        session_key_a=session_key_a,
        session_key_b=session_key_b,
    )
