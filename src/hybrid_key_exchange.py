import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hybrid_exchange import _perform_hybrid_exchange as perform_hybrid_exchange


def main():
    print("=== Hybrid X25519 + ML-KEM-768 Demo ===")

    # Reuse the current transcript-bound X25519 + ML-KEM-768 workflow.
    exchange = perform_hybrid_exchange()

    print(
        "X25519 shared secrets match:",
        exchange.x25519_shared_secret_a == exchange.x25519_shared_secret_b,
    )
    print(
        "ML-KEM shared secrets match:",
        exchange.mlkem_shared_secret_a == exchange.mlkem_shared_secret_b,
    )
    print(
        "Hybrid session keys match:",
        exchange.session_key_a == exchange.session_key_b,
    )

    # Demonstrate authenticated encryption with the derived key.
    nonce = os.urandom(12)
    message = b"Zero-Trust hybrid session established"
    encrypted = AESGCM(exchange.session_key_a).encrypt(nonce, message, None)
    decrypted = AESGCM(exchange.session_key_b).decrypt(nonce, encrypted, None)

    print("AES-GCM message recovered:", decrypted == message)
    print("Recovered message:", decrypted.decode())
    print("AES-GCM ciphertext bytes:", len(encrypted))
    print("Hybrid session key length:", len(exchange.session_key_a), "bytes")


if __name__ == "__main__":
    main()
