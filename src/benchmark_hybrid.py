import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classical_ecdh import derive_session_key, derive_shared_secret, generate_key_pair
from src.hybrid_exchange import perform_hybrid_exchange


ITERATIONS = 30


def measure(operation):
    samples = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def classical_ecdh():
    receiver_private, receiver_public = generate_key_pair()
    sender_private, sender_public = generate_key_pair()
    secret = derive_shared_secret(sender_private, receiver_public)
    if secret != derive_shared_secret(receiver_private, sender_public):
        raise RuntimeError("X25519 secrets do not match")
    derive_session_key(secret, b"\x01" * 32, b"classical-x25519-benchmark")


def hybrid_exchange():
    perform_hybrid_exchange()


if __name__ == "__main__":
    # Warm-up to reduce first-call effects.
    classical_ecdh()
    hybrid_exchange()

    classical_ms = measure(classical_ecdh)
    hybrid_ms = measure(hybrid_exchange)

    print(f"Iterations per method: {ITERATIONS}")
    print(f"Classical X25519 + HKDF median: {classical_ms:.3f} ms")
    print(f"Hybrid X25519 + ML-KEM-768 + HKDF median: {hybrid_ms:.3f} ms")
    print(f"Hybrid/classical ratio: {hybrid_ms / classical_ms:.2f}x")
    print("Note: local microbenchmark, not a production performance result.")
