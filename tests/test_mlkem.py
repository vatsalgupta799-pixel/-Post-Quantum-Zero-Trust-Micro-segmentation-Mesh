"""Tests for the standalone ML-KEM-768 key-establishment module."""

import pytest
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM768PublicKey,
)

from scripts.demo_mlkem import main as run_demo
from src.pqc_mlkem import (
    MLKEM768_SHARED_SECRET_LENGTH,
    EncapsulationResult,
    decapsulate_shared_secret,
    encapsulate_shared_secret,
    generate_key_pair,
)


def test_key_generation_returns_mlkem768_key_types() -> None:
    private_key, public_key = generate_key_pair()

    assert isinstance(private_key, MLKEM768PrivateKey)
    assert isinstance(public_key, MLKEM768PublicKey)


def test_encapsulation_returns_ciphertext_and_shared_secret() -> None:
    _, public_key = generate_key_pair()

    result = encapsulate_shared_secret(public_key)

    assert isinstance(result, EncapsulationResult)
    assert isinstance(result.ciphertext, bytes)
    assert isinstance(result.shared_secret, bytes)
    assert result.ciphertext
    assert len(result.shared_secret) == MLKEM768_SHARED_SECRET_LENGTH


def test_decapsulation_returns_a_shared_secret() -> None:
    private_key, public_key = generate_key_pair()
    result = encapsulate_shared_secret(public_key)

    recovered_secret = decapsulate_shared_secret(private_key, result.ciphertext)

    assert isinstance(recovered_secret, bytes)
    assert len(recovered_secret) == MLKEM768_SHARED_SECRET_LENGTH


def test_service_a_and_service_b_agree_on_the_shared_secret() -> None:
    private_b, public_b = generate_key_pair()
    service_a_result = encapsulate_shared_secret(public_b)

    service_b_secret = decapsulate_shared_secret(
        private_b,
        service_a_result.ciphertext,
    )

    assert service_a_result.shared_secret == service_b_secret


def test_independent_exchanges_produce_different_shared_secrets() -> None:
    private_b_one, public_b_one = generate_key_pair()
    private_b_two, public_b_two = generate_key_pair()
    exchange_one = encapsulate_shared_secret(public_b_one)
    exchange_two = encapsulate_shared_secret(public_b_two)

    assert (
        decapsulate_shared_secret(private_b_one, exchange_one.ciphertext)
        == exchange_one.shared_secret
    )
    assert (
        decapsulate_shared_secret(private_b_two, exchange_two.ciphertext)
        == exchange_two.shared_secret
    )
    # This is an overwhelmingly likely uniqueness check, not a proof that a
    # collision is mathematically impossible.
    assert exchange_one.shared_secret != exchange_two.shared_secret


def test_invalid_inputs_follow_the_documented_library_behavior() -> None:
    private_key, public_key = generate_key_pair()

    with pytest.raises(TypeError):
        encapsulate_shared_secret(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        decapsulate_shared_secret(object(), b"ciphertext")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        decapsulate_shared_secret(private_key, "ciphertext")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        decapsulate_shared_secret(private_key, b"malformed")

    # ML-KEM uses implicit rejection: a correct-length altered ciphertext can
    # yield a replacement secret instead of an exception. This confirms that
    # actual behavior without claiming it authenticates the ciphertext.
    valid_result = encapsulate_shared_secret(public_key)
    altered_ciphertext = bytes([valid_result.ciphertext[0] ^ 1]) + valid_result.ciphertext[1:]
    implicit_rejection_secret = decapsulate_shared_secret(
        private_key,
        altered_ciphertext,
    )

    assert isinstance(implicit_rejection_secret, bytes)
    assert len(implicit_rejection_secret) == MLKEM768_SHARED_SECRET_LENGTH
    assert implicit_rejection_secret != valid_result.shared_secret


def test_demo_output_is_sanitized(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_demo() == 0

    assert capsys.readouterr().out == (
        "=== ML-KEM-768 Key Establishment Demo ===\n"
        "\n"
        "[PASS] ML-KEM-768 implementation available\n"
        "[PASS] Service B key pair generated\n"
        "[PASS] Public key made available to Service A\n"
        "[PASS] Service A encapsulated a shared secret\n"
        "[PASS] Ciphertext made available to Service B\n"
        "[PASS] Service B decapsulated the ciphertext\n"
        "[PASS] Both shared secrets match\n"
        "[PASS] Shared secret length: 32 bytes\n"
        "\n"
        "Post-quantum key establishment demonstration completed.\n"
    )
