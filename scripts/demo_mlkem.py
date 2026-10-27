"""Run the Day 3 standalone ML-KEM-768 key-establishment demonstration."""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pqc_mlkem import (  # noqa: E402
    MLKEM768_SHARED_SECRET_LENGTH,
    decapsulate_shared_secret,
    encapsulate_shared_secret,
    generate_key_pair,
)


def main() -> int:
    """Simulate an ML-KEM exchange without exposing secret key material."""

    print("=== ML-KEM-768 Key Establishment Demo ===")
    print()

    try:
        private_b, public_b = generate_key_pair()
        print("[PASS] ML-KEM-768 implementation available")
        print("[PASS] Service B key pair generated")

        # Only the public key is made available to the initiating service.
        service_a_public_key = public_b
        print("[PASS] Public key made available to Service A")

        service_a_result = encapsulate_shared_secret(service_a_public_key)
        print("[PASS] Service A encapsulated a shared secret")

        # The ciphertext is safe to transfer; Service B's private key stays
        # local and is used only for decapsulation.
        service_b_ciphertext = service_a_result.ciphertext
        print("[PASS] Ciphertext made available to Service B")

        service_b_secret = decapsulate_shared_secret(
            private_b,
            service_b_ciphertext,
        )
        print("[PASS] Service B decapsulated the ciphertext")

        if service_a_result.shared_secret != service_b_secret:
            print("[FAIL] Both shared secrets do not match")
            return 1
        print("[PASS] Both shared secrets match")

        if len(service_a_result.shared_secret) != MLKEM768_SHARED_SECRET_LENGTH:
            print("[FAIL] Unexpected shared secret length")
            return 1
        print(
            "[PASS] Shared secret length: "
            f"{len(service_a_result.shared_secret)} bytes"
        )
    except UnsupportedAlgorithm as error:
        print(f"[BLOCKED] ML-KEM-768 backend unavailable: {error}")
        return 2
    except (TypeError, ValueError) as error:
        print(f"[FAIL] ML-KEM-768 operation failed: {error}")
        return 1

    print()
    print("Post-quantum key establishment demonstration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
