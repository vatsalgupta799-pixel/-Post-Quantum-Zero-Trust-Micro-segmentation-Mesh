"""Safe integration-facing interface for the local hybrid exchange prototype.

This module intentionally exposes metadata only. It reuses the verified
in-memory hybrid workflow and does not implement authentication, networking,
TLS, or a transport protocol.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Final, Literal

from cryptography.exceptions import UnsupportedAlgorithm

from src.classical_ecdh import DEFAULT_SESSION_KEY_LENGTH
from src.hybrid_exchange import (
    HYBRID_PROTOCOL_ID,
    MLKEM768_ALGORITHM_ID,
    X25519_ALGORITHM_ID,
    _HybridExchangeSecrets,
    _perform_hybrid_exchange as perform_hybrid_exchange,
)


PROTOCOL_VERSION: Final[str] = HYBRID_PROTOCOL_ID.decode("ascii").rsplit("/", 1)[-1]
ALGORITHMS: Final[tuple[str, str]] = (
    X25519_ALGORITHM_ID.decode("ascii"),
    MLKEM768_ALGORITHM_ID.decode("ascii"),
)
VERIFICATION_CHECKS: Final[tuple[str, ...]] = (
    "x25519_component_agreement",
    "mlkem_768_component_agreement",
    "transcript_consistency",
    "hybrid_session_key_agreement",
)

INVALID_PROTOCOL_VERSION: Final[str] = "INVALID_PROTOCOL_VERSION"
UNSUPPORTED_ALGORITHM: Final[str] = "UNSUPPORTED_ALGORITHM"
KEY_ESTABLISHMENT_FAILED: Final[str] = "KEY_ESTABLISHMENT_FAILED"
INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"


class HybridIntegrationError(RuntimeError):
    """A sanitized integration failure with a stable, non-secret error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HybridSessionResult:
    """Public metadata from a verified local hybrid exchange.

    The result deliberately excludes all private keys, component shared
    secrets, transcripts, and final session-key bytes. A future networked
    application needs a separately reviewed key-management interface if it
    needs to consume the derived session key.
    """

    protocol_version: str
    algorithms: tuple[str, str]
    session_key_length: int
    duration_ms: float
    verification_checks: tuple[str, ...]
    success: Literal[True] = True


def _validate_protocol_version(expected_protocol_version: str) -> None:
    """Reject an incompatible or malformed integration expectation."""

    if not isinstance(expected_protocol_version, str) or not expected_protocol_version:
        raise HybridIntegrationError(
            INVALID_PROTOCOL_VERSION,
            "expected_protocol_version must be a non-empty string",
        )
    if expected_protocol_version != PROTOCOL_VERSION:
        raise HybridIntegrationError(
            INVALID_PROTOCOL_VERSION,
            "unsupported hybrid protocol version",
        )


def _verify_exchange_result(result: _HybridExchangeSecrets) -> None:
    """Check all component agreements without exposing their values."""

    if result.x25519_shared_secret_a != result.x25519_shared_secret_b:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        )
    if result.mlkem_shared_secret_a != result.mlkem_shared_secret_b:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        )
    if not result.transcript:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        )
    if result.session_key_a != result.session_key_b:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        )
    if len(result.session_key_a) != DEFAULT_SESSION_KEY_LENGTH:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        )


def establish_hybrid_session(
    *,
    expected_protocol_version: str = PROTOCOL_VERSION,
) -> HybridSessionResult:
    """Execute and verify the existing in-memory hybrid workflow.

    Args:
        expected_protocol_version: The caller's expected version identifier.
            Only the currently implemented `hybrid-v1` value is accepted.

    Returns:
        Non-sensitive metadata after both simulated parties agree on a
        32-byte session key.

    Raises:
        HybridIntegrationError: If the requested protocol is invalid, a
            cryptographic capability is unavailable, any component fails, or
            an unexpected internal error occurs. The exception message is
            deliberately sanitized and its `code` is safe to log.
    """

    _validate_protocol_version(expected_protocol_version)
    started_at = time.perf_counter_ns()
    try:
        exchange_result = perform_hybrid_exchange()
        _verify_exchange_result(exchange_result)
    except HybridIntegrationError:
        raise
    except UnsupportedAlgorithm as error:
        raise HybridIntegrationError(
            UNSUPPORTED_ALGORITHM,
            "required cryptographic algorithm is unavailable",
        ) from None
    except (RuntimeError, TypeError, ValueError) as error:
        raise HybridIntegrationError(
            KEY_ESTABLISHMENT_FAILED,
            "hybrid key establishment failed",
        ) from None
    except Exception as error:
        raise HybridIntegrationError(
            INTERNAL_ERROR,
            "unexpected hybrid integration failure",
        ) from None

    return HybridSessionResult(
        protocol_version=PROTOCOL_VERSION,
        algorithms=ALGORITHMS,
        session_key_length=DEFAULT_SESSION_KEY_LENGTH,
        duration_ms=(time.perf_counter_ns() - started_at) / 1_000_000,
        verification_checks=VERIFICATION_CHECKS,
    )
