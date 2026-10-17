import statistics
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pqcrypto.kem import ml_kem_768


ITERATIONS = 30


def derive_key(secret, salt, info):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    ).derive(secret)


def measure(operation):
    samples = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def classical_ecdh():
    receiver = ec.generate_private_key(ec.SECP256R1())
    sender = ec.generate_private_key(ec.SECP256R1())
    secret = sender.exchange(ec.ECDH(), receiver.public_key())
    derive_key(secret, b"\x01" * 32, b"classical-ecdh-benchmark")


def hybrid_exchange():
    receiver_ec = ec.generate_private_key(ec.SECP256R1())
    sender_ec = ec.generate_private_key(ec.SECP256R1())
    receiver_kem_public, receiver_kem_secret = ml_kem_768.keygen()

    classical_secret = sender_ec.exchange(
        ec.ECDH(), receiver_ec.public_key()
    )
    ciphertext, sender_pq_secret = ml_kem_768.encaps(receiver_kem_public)
    receiver_pq_secret = ml_kem_768.decaps(receiver_kem_secret, ciphertext)

    if sender_pq_secret != receiver_pq_secret:
        raise RuntimeError("ML-KEM secrets do not match")

    derive_key(
        classical_secret + sender_pq_secret,
        b"\x02" * 32,
        b"hybrid-benchmark",
    )


if __name__ == "__main__":
    # Warm-up to reduce first-call effects.
    classical_ecdh()
    hybrid_exchange()

    classical_ms = measure(classical_ecdh)
    hybrid_ms = measure(hybrid_exchange)

    print(f"Iterations per method: {ITERATIONS}")
    print(f"Classical ECDH + HKDF median: {classical_ms:.3f} ms")
    print(f"Hybrid ECDH + ML-KEM-768 + HKDF median: {hybrid_ms:.3f} ms")
    print(f"Hybrid/classical ratio: {hybrid_ms / classical_ms:.2f}x")
    print("Note: local microbenchmark, not a production performance result.")
