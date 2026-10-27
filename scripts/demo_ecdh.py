"""Run the Day 2 classical X25519 and HKDF demonstration."""

from __future__ import annotations

import secrets
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classical_ecdh import (  # noqa: E402
    DEFAULT_HKDF_INFO,
    DEFAULT_SESSION_KEY_LENGTH,
    derive_session_key,
    derive_shared_secret,
    generate_key_pair,
)


def main() -> int:
    """Simulate two services and report only non-sensitive results."""

    print("=== Classical X25519 Key Exchange Demo ===")
    print()

    try:
        private_a, public_a = generate_key_pair()
        private_b, public_b = generate_key_pair()
        print("[PASS] Service A key pair generated")
        print("[PASS] Service B key pair generated")

        shared_secret_a = derive_shared_secret(private_a, public_b)
        shared_secret_b = derive_shared_secret(private_b, public_a)
        print("[PASS] Public keys exchanged")

        if shared_secret_a != shared_secret_b:
            print("[FAIL] Shared secrets do not match")
            return 1
        print("[PASS] Shared secrets match")

        # This public salt is generated for the simulated session and would be
        # transmitted as handshake metadata in a real protocol.
        session_salt = secrets.token_bytes(16)
        session_key_a = derive_session_key(
            shared_secret_a,
            salt=session_salt,
            info=DEFAULT_HKDF_INFO,
        )
        session_key_b = derive_session_key(
            shared_secret_b,
            salt=session_salt,
            info=DEFAULT_HKDF_INFO,
        )

        if session_key_a != session_key_b:
            print("[FAIL] HKDF session keys do not match")
            return 1
        print("[PASS] HKDF session keys match")
        print(f"[PASS] Session key length: {len(session_key_a)} bytes")
        if len(session_key_a) != DEFAULT_SESSION_KEY_LENGTH:
            print("[FAIL] Unexpected session key length")
            return 1
    except (TypeError, ValueError) as error:
        print(f"[FAIL] Demonstration input or exchange error: {error}")
        return 1

    print()
    print("Classical key exchange demonstration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
