"""Tests for the Day 4 hybrid X25519 and ML-KEM-768 exchange."""

import pytest

from src.classical_ecdh import (
    derive_shared_secret,
    generate_key_pair as generate_x25519_key_pair,
)
from src.hybrid_exchange import (
    HYBRID_HKDF_CONTEXT,
    build_handshake_transcript,
    derive_hybrid_session_key,
    perform_hybrid_exchange,
)
from src.pqc_mlkem import (
    decapsulate_shared_secret,
    encapsulate_shared_secret,
    generate_key_pair as generate_mlkem_key_pair,
)


def test_complete_hybrid_exchange_succeeds() -> None:
    result = perform_hybrid_exchange()

    assert result.transcript
    assert result.session_key_a == result.session_key_b
    assert len(result.session_key_a) == 32


def test_x25519_shared_secrets_match_in_the_hybrid_exchange() -> None:
    result = perform_hybrid_exchange()

    assert result.x25519_shared_secret_a == result.x25519_shared_secret_b


def test_mlkem_shared_secrets_match_in_the_hybrid_exchange() -> None:
    result = perform_hybrid_exchange()

    assert result.mlkem_shared_secret_a == result.mlkem_shared_secret_b


def test_hybrid_session_keys_match_and_are_32_bytes() -> None:
    result = perform_hybrid_exchange()

    assert result.session_key_a == result.session_key_b
    assert len(result.session_key_a) == 32


def test_independent_hybrid_exchanges_produce_different_session_keys() -> None:
    first = perform_hybrid_exchange()
    second = perform_hybrid_exchange()

    # This is an overwhelmingly likely uniqueness check, not a proof that a
    # collision is mathematically impossible.
    assert first.session_key_a != second.session_key_a


def test_hkdf_context_separates_hybrid_session_keys() -> None:
    result = perform_hybrid_exchange()

    default_key = derive_hybrid_session_key(
        result.x25519_shared_secret_a,
        result.mlkem_shared_secret_a,
        result.transcript,
    )
    alternate_key = derive_hybrid_session_key(
        result.x25519_shared_secret_a,
        result.mlkem_shared_secret_a,
        result.transcript,
        context=HYBRID_HKDF_CONTEXT + b"/alternate",
    )

    assert default_key != alternate_key


def test_transcript_binding_changes_the_derived_key() -> None:
    result = perform_hybrid_exchange()
    altered_transcript = result.transcript + b"altered"

    original_key = derive_hybrid_session_key(
        result.x25519_shared_secret_a,
        result.mlkem_shared_secret_a,
        result.transcript,
    )
    altered_key = derive_hybrid_session_key(
        result.x25519_shared_secret_a,
        result.mlkem_shared_secret_a,
        altered_transcript,
    )

    assert original_key != altered_key


def test_tampered_mlkem_ciphertext_prevents_hybrid_key_agreement() -> None:
    private_a, public_a = generate_x25519_key_pair()
    private_b, public_b = generate_x25519_key_pair()
    private_mlkem_b, public_mlkem_b = generate_mlkem_key_pair()
    x25519_secret_a = derive_shared_secret(private_a, public_b)
    x25519_secret_b = derive_shared_secret(private_b, public_a)
    encapsulation = encapsulate_shared_secret(public_mlkem_b)
    tampered_ciphertext = (
        bytes([encapsulation.ciphertext[0] ^ 1]) + encapsulation.ciphertext[1:]
    )
    implicit_rejection_secret = decapsulate_shared_secret(
        private_mlkem_b,
        tampered_ciphertext,
    )

    service_a_key = derive_hybrid_session_key(
        x25519_secret_a,
        encapsulation.shared_secret,
        build_handshake_transcript(
            public_a,
            public_b,
            public_mlkem_b,
            encapsulation.ciphertext,
        ),
    )
    service_b_key = derive_hybrid_session_key(
        x25519_secret_b,
        implicit_rejection_secret,
        build_handshake_transcript(
            public_a,
            public_b,
            public_mlkem_b,
            tampered_ciphertext,
        ),
    )

    assert implicit_rejection_secret != encapsulation.shared_secret
    assert service_a_key != service_b_key


def test_invalid_inputs_are_rejected_without_component_fallback() -> None:
    result = perform_hybrid_exchange()
    _, valid_x25519_public = generate_x25519_key_pair()
    _, valid_mlkem_public = generate_mlkem_key_pair()

    with pytest.raises(TypeError):
        build_handshake_transcript(
            object(),  # type: ignore[arg-type]
            valid_x25519_public,
            valid_mlkem_public,
            b"ciphertext",
        )
    with pytest.raises(ValueError):
        derive_hybrid_session_key(
            b"",
            result.mlkem_shared_secret_a,
            result.transcript,
        )
    with pytest.raises(ValueError):
        derive_hybrid_session_key(
            b"short",
            result.mlkem_shared_secret_a,
            result.transcript,
        )
    with pytest.raises(TypeError):
        derive_hybrid_session_key(
            result.x25519_shared_secret_a,
            "not bytes",  # type: ignore[arg-type]
            result.transcript,
        )


def test_hybrid_demo_output_is_sanitized(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.demo_hybrid import main

    assert main() == 0
    assert capsys.readouterr().out == (
        "=== Hybrid Key Exchange Integration Demo ===\n"
        "\n"
        "[PASS] Protocol version: hybrid-v1\n"
        "[PASS] Algorithms: X25519 + ML-KEM-768\n"
        "[PASS] X25519 component verified\n"
        "[PASS] ML-KEM-768 component verified\n"
        "[PASS] Hybrid key derivation completed\n"
        "[PASS] Both session keys match\n"
        "[PASS] Session key length: 32 bytes\n"
        "[PASS] Result contains public metadata only\n"
        "\n"
        "Integration demonstration completed successfully.\n"
    )
