# Day 5 — Hybrid ECDH + ML-KEM-768 Prototype

## Objective
Build a Python proof of concept combining classical ECDH with post-quantum ML-KEM-768 to derive a hybrid session key.

## Implementation
- **Classical key exchange:** ECDH using the NIST P-256 curve.
- **Post-quantum key establishment:** ML-KEM-768.
- **Key derivation:** HKDF with SHA-256 derives a 32-byte session key from both shared secrets.
- **Authenticated encryption:** AES-256-GCM demonstrates encryption and recovery of a test message.
- **Automated test:** `tests/test_hybrid_key_exchange.py` verifies that the exchange and encryption checks succeed.

## Test Results
Command:

```bash
python -m unittest discover -s tests -v
Observed result:
- 1 test passed.
- ECDH shared secrets matched.
- ML-KEM-768 shared secrets matched.
- Hybrid session keys matched.
- AES-GCM successfully recovered the test message.

The ML-KEM-768 ciphertext observed in this environment was 1,088 bytes, and the derived session key was 32 bytes.

## Limitations
- This is a local proof of concept, not a production protocol.
- The demo does not authenticate peer identities or protect the exchange against an active man-in-the-middle attack.
- The combined-secret construction requires protocol review before production use
- The prototype is not integrated into Kubernetes or Istio traffic.
- Istio's configured mTLS does not automatically use ML-KEM through this Python prototype.
- No performance benchmark has been conducted.

## Remaining Work
1. Review the hybrid key derivation construction and add explicit domain separation and context binding.
2. Expand failure-path tests and repeat benchmarks under controlled conditions.
3. Investigate a supported way to integrate post-quantum key establishment into the service communication layer.
4. Validate the complete Kubernetes service path and document the evidence and limitations.

## Security Test and Performance Results

### Security Tests
Command: `python -m unittest discover -s tests -v`

- 2 tests passed.
- The hybrid exchange and authenticated-encryption demonstration succeeded.
- AES-GCM rejected modified ciphertext with an authentication failure.

### Local Microbenchmark
Command: `python src/benchmark_hybrid.py`

- Iterations per method: 30
- Classical ECDH + HKDF median: 0.066 ms
- Hybrid ECDH + ML-KEM-768 + HKDF median: 0.216 ms
- Hybrid/classical median ratio: 3.29x

These results are specific to the current Kali VM and software environment. The hybrid measurement includes ML-KEM key generation, encapsulation, and decapsulation; the classical measurement includes ECDH and HKDF. This is a prototype microbenchmark, not a production or end-to-end network latency measurement.
