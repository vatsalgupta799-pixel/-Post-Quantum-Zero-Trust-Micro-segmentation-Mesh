"""Run the Day 4 hybrid X25519 and ML-KEM-768 demonstration."""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hybrid_exchange import (  # noqa: E402
    perform_hybrid_exchange,
)
from src.classical_ecdh import DEFAULT_SESSION_KEY_LENGTH  # noqa: E402


def main() -> int:
    """Run a local two-service hybrid exchange and print only safe results."""

    print("=== Hybrid Key Establishment Demo ===")
    print()

    try:
        result = perform_hybrid_exchange()
    except UnsupportedAlgorithm as error:
        print(f"[BLOCKED] Required cryptographic backend unavailable: {error}")
        return 2
    except (RuntimeError, TypeError, ValueError) as error:
        print(f"[FAIL] Hybrid key establishment failed: {error}")
        return 1

    print("[PASS] X25519 key exchange completed")
    print("[PASS] X25519 shared secrets match")
    print("[PASS] ML-KEM-768 encapsulation completed")
    print("[PASS] ML-KEM-768 decapsulation completed")
    print("[PASS] ML-KEM shared secrets match")
    print("[PASS] Handshake transcripts match")
    print("[PASS] Hybrid session keys match")

    if len(result.session_key_a) != DEFAULT_SESSION_KEY_LENGTH:
        print("[FAIL] Unexpected hybrid session key length")
        return 1
    print(f"[PASS] Hybrid session key length: {len(result.session_key_a)} bytes")

    print()
    print("Hybrid key-establishment demonstration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
