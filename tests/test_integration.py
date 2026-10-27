"""Tests for the Day 6 safe integration-facing hybrid exchange interface."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from cryptography.exceptions import UnsupportedAlgorithm

import src.integration as integration
from src.hybrid_exchange import perform_hybrid_exchange


def test_integration_interface_runs_the_real_hybrid_workflow() -> None:
    result = integration.establish_hybrid_session()

    assert result.success is True
    assert result.protocol_version == integration.PROTOCOL_VERSION
    assert result.algorithms == integration.ALGORITHMS
    assert result.duration_ms >= 0


def test_result_reports_verified_session_key_agreement_and_length() -> None:
    result = integration.establish_hybrid_session()

    assert result.session_key_length == 32
    assert result.verification_checks == integration.VERIFICATION_CHECKS
    assert "hybrid_session_key_agreement" in result.verification_checks


def test_result_structure_contains_only_public_metadata() -> None:
    result = integration.establish_hybrid_session()
    metadata = asdict(result)

    assert set(metadata) == {
        "protocol_version",
        "algorithms",
        "session_key_length",
        "duration_ms",
        "verification_checks",
        "success",
    }
    assert not any(isinstance(value, bytes) for value in metadata.values())
    assert "private_key" not in metadata
    assert "session_key" not in metadata
    assert "shared_secret" not in metadata


def test_demo_output_is_sanitized_and_reports_actual_verification(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts.demo_hybrid import main

    assert main() == 0
    output = capsys.readouterr().out

    assert "[PASS] X25519 component verified" in output
    assert "[PASS] ML-KEM-768 component verified" in output
    assert "[PASS] Simulated Service A and Service B completed the exchange" in output
    assert "[PASS] Both session keys match" in output
    assert "[PASS] Result contains public metadata only" in output
    assert "private key" not in output.lower()
    assert "shared secret" not in output.lower()
    assert "session key:" not in output.lower()


@pytest.mark.parametrize(
    "field_name",
    ("x25519_shared_secret_b", "mlkem_shared_secret_b"),
)
def test_component_disagreement_never_returns_success(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
) -> None:
    real_result = perform_hybrid_exchange()
    inconsistent_result = replace(real_result, **{field_name: b"x" * 32})
    monkeypatch.setattr(
        integration,
        "perform_hybrid_exchange",
        lambda: inconsistent_result,
    )

    with pytest.raises(integration.HybridIntegrationError) as error:
        integration.establish_hybrid_session()

    assert error.value.code == integration.KEY_ESTABLISHMENT_FAILED
    assert str(error.value) == "hybrid key establishment failed"


def test_underlying_failure_is_sanitized_and_propagated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_exchange() -> None:
        raise RuntimeError("do not expose internal key material")

    monkeypatch.setattr(integration, "perform_hybrid_exchange", fail_exchange)

    with pytest.raises(integration.HybridIntegrationError) as error:
        integration.establish_hybrid_session()

    assert error.value.code == integration.KEY_ESTABLISHMENT_FAILED
    assert str(error.value) == "hybrid key establishment failed"
    assert "key material" not in str(error.value)


def test_unsupported_algorithm_has_a_safe_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_exchange() -> None:
        raise UnsupportedAlgorithm("backend-specific detail")

    monkeypatch.setattr(integration, "perform_hybrid_exchange", unavailable_exchange)

    with pytest.raises(integration.HybridIntegrationError) as error:
        integration.establish_hybrid_session()

    assert error.value.code == integration.UNSUPPORTED_ALGORITHM
    assert str(error.value) == "required cryptographic algorithm is unavailable"


@pytest.mark.parametrize("version", (None, "", "hybrid-v0"))
def test_invalid_protocol_versions_are_rejected(version: object) -> None:
    with pytest.raises(integration.HybridIntegrationError) as error:
        integration.establish_hybrid_session(  # type: ignore[arg-type]
            expected_protocol_version=version
        )

    assert error.value.code == integration.INVALID_PROTOCOL_VERSION


def test_importing_integration_module_has_no_output_or_demo_side_effect() -> None:
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-c", "import src.integration"],
        cwd=project_root,
        capture_output=True,
        check=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""
