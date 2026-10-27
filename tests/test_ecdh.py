"""Tests for the classical X25519 and HKDF baseline."""

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from src.classical_ecdh import (
    DEFAULT_HKDF_INFO,
    derive_session_key,
    derive_shared_secret,
    generate_key_pair,
)


TEST_SALT = b"day-2-public-session-salt"


def test_key_generation_returns_x25519_key_types() -> None:
    private_key, public_key = generate_key_pair()

    assert isinstance(private_key, X25519PrivateKey)
    assert isinstance(public_key, X25519PublicKey)


def test_two_services_derive_the_same_shared_secret() -> None:
    private_a, public_a = generate_key_pair()
    private_b, public_b = generate_key_pair()

    shared_a = derive_shared_secret(private_a, public_b)
    shared_b = derive_shared_secret(private_b, public_a)

    assert shared_a == shared_b
    assert len(shared_a) == 32


def test_two_services_derive_the_same_32_byte_session_key() -> None:
    private_a, public_a = generate_key_pair()
    private_b, public_b = generate_key_pair()
    shared_a = derive_shared_secret(private_a, public_b)
    shared_b = derive_shared_secret(private_b, public_a)

    session_a = derive_session_key(shared_a, TEST_SALT, DEFAULT_HKDF_INFO)
    session_b = derive_session_key(shared_b, TEST_SALT, DEFAULT_HKDF_INFO)

    assert session_a == session_b
    assert len(session_a) == 32


def test_independent_exchanges_produce_different_session_keys() -> None:
    private_a1, public_a1 = generate_key_pair()
    private_b1, public_b1 = generate_key_pair()
    private_a2, public_a2 = generate_key_pair()
    private_b2, public_b2 = generate_key_pair()

    shared_a1 = derive_shared_secret(private_a1, public_b1)
    shared_b1 = derive_shared_secret(private_b1, public_a1)
    shared_a2 = derive_shared_secret(private_a2, public_b2)
    shared_b2 = derive_shared_secret(private_b2, public_a2)

    session_1 = derive_session_key(shared_a1, TEST_SALT, DEFAULT_HKDF_INFO)
    session_1_peer = derive_session_key(shared_b1, TEST_SALT, DEFAULT_HKDF_INFO)
    session_2 = derive_session_key(shared_a2, TEST_SALT, DEFAULT_HKDF_INFO)
    session_2_peer = derive_session_key(shared_b2, TEST_SALT, DEFAULT_HKDF_INFO)

    assert session_1 == session_1_peer
    assert session_2 == session_2_peer
    assert session_1 != session_2


def test_hkdf_context_separates_derived_keys() -> None:
    shared_secret = b"test shared secret material"

    first = derive_session_key(shared_secret, TEST_SALT, b"context/a")
    second = derive_session_key(shared_secret, TEST_SALT, b"context/b")

    assert first != second


def test_invalid_inputs_are_rejected() -> None:
    private_key, public_key = generate_key_pair()

    with pytest.raises(TypeError):
        derive_shared_secret(object(), public_key)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        derive_shared_secret(private_key, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        derive_session_key("not bytes", TEST_SALT)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        derive_session_key(b"", TEST_SALT)
    with pytest.raises(ValueError):
        derive_session_key(b"secret", TEST_SALT, length=0)
    with pytest.raises(TypeError):
        derive_session_key(b"secret", TEST_SALT, length=True)


def test_same_inputs_reproduce_the_same_session_key() -> None:
    shared_secret = b"reproducible shared secret"

    first = derive_session_key(shared_secret, TEST_SALT, DEFAULT_HKDF_INFO)
    second = derive_session_key(shared_secret, TEST_SALT, DEFAULT_HKDF_INFO)

    assert first == second
