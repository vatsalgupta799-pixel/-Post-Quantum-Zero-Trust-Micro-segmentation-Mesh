"""Run the Day 6 hybrid key-establishment integration demonstration."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.integration import (  # noqa: E402
    HybridIntegrationError,
    VERIFICATION_CHECKS,
    establish_hybrid_session,
)


def main() -> int:
    """Run the safe integration interface and print only public metadata."""

    print("=== Hybrid Key Exchange Integration Demo ===")
    print()

    try:
        result = establish_hybrid_session()
    except HybridIntegrationError as error:
        print(f"[FAIL] Hybrid key establishment did not complete ({error.code})")
        return 1

    if not result.success or result.verification_checks != VERIFICATION_CHECKS:
        print("[FAIL] Hybrid verification metadata is incomplete")
        return 1

    print(f"[PASS] Protocol version: {result.protocol_version}")
    print(f"[PASS] Algorithms: {' + '.join(result.algorithms)}")
    print("[PASS] X25519 component verified")
    print("[PASS] ML-KEM-768 component verified")
    print("[PASS] Hybrid key derivation completed")
    print("[PASS] Simulated Service A and Service B completed the exchange")
    print("[PASS] Both session keys match")
    print(f"[PASS] Session key length: {result.session_key_length} bytes")
    print("[PASS] Result contains public metadata only")

    print()
    print("Integration demonstration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
