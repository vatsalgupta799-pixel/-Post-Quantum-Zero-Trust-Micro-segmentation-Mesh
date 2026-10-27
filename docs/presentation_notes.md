# Task 4 Presentation Notes

## Suggested 5–7 minute outline

### 1. Problem statement — 40 seconds

Modern services need confidentiality for data that may remain sensitive for
years. A future cryptographically relevant quantum computer could threaten
some currently deployed public-key systems, so long-lived traffic deserves a
post-quantum migration plan.

### 2. Motivation: Harvest Now, Decrypt Later — 40 seconds

Harvest Now, Decrypt Later (HNDL) describes an attacker collecting encrypted
traffic today and attempting to decrypt it later if stronger computing
capabilities become available. The project explores a hybrid key-establishment
approach so the local prototype relies on both a classical and a
post-quantum component.

### 3. Proposed approach — 45 seconds

Task 4 combines:

- **X25519** for classical elliptic-curve Diffie–Hellman key establishment;
- **ML-KEM-768** for post-quantum key encapsulation;
- **HKDF-SHA-256** to turn both shared secrets into one 32-byte session key.

The project uses the installed `cryptography` library rather than implementing
cryptographic mathematics manually.

### 4. Architecture — 60 seconds

Service A and Service B each create an X25519 key pair and derive the same
classical secret. Service B also creates an ML-KEM-768 key pair. Service A
encapsulates to B's ML-KEM public key, and B decapsulates the ciphertext to
obtain the same post-quantum secret.

The prototype builds a canonical public transcript from the protocol and
algorithm identifiers, public keys, and ML-KEM ciphertext. It length-prefixes
the two secrets, hashes the transcript, and uses HKDF-SHA-256 to derive a
32-byte key. The actual sequence diagram is in `docs/architecture.md`.

### 5. Demonstration — 40 seconds

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe scripts\demo_hybrid.py
```

Explain that the audience should see the protocol version, `X25519 +
ML-KEM-768`, completion by both simulated services, matching session-key
status, and a 32-byte key length. The script intentionally does not print any
private key, component secret, or final session key.

### 6. Results — 60 seconds

Use only the recorded 500-iteration local benchmark from
`docs/benchmark_report.md` (2026-10-18, Windows 11, Python 3.13.12,
`cryptography` 50.0.2):

| Complete local exchange | Median latency | Simulated cryptographic payload |
| --- | ---: | ---: |
| X25519 + HKDF | 0.176800 ms | 64 bytes |
| ML-KEM-768 | 0.330650 ms | 2272 bytes |
| Hybrid X25519 + ML-KEM-768 | 0.573650 ms | 2336 bytes |

The hybrid median was 0.396850 ms above the classical median, a 224.462670%
increase in this specific local process. These are in-process cryptographic
measurements—not network latency, TLS handshakes, Envoy performance, or
Kubernetes performance.

### 7. Security limitations — 45 seconds

This is not production-ready TLS or mTLS. Successful key agreement does not
authenticate the participants. The project has no certificate validation,
network protocol, key confirmation, replay protection, key lifecycle, Vault
integration, or independent cryptographic audit. Refer to
`docs/security_limitations.md` rather than overstating the result.

### 8. Wider Zero-Trust project integration — 40 seconds

Task 4 is one layer only:

- certificates and mTLS establish workload identity;
- OPA decides whether an authenticated request is authorized;
- Kubernetes NetworkPolicies restrict permitted pod-to-pod paths;
- Envoy provides supported transport configuration; and
- monitoring records safe outcomes without logging secret material.

These controls complement the prototype; they are not integrated or claimed
as implemented by Task 4.

### 9. Conclusion and future work — 30 seconds

The project verifies a reproducible local hybrid key-establishment
demonstration, automated tests, and measured local overhead. Next steps are a
reviewed hybrid TLS path, certificate-based authentication, deliberate key
lifecycle design, end-to-end integration testing, and deployment validation.

## Likely viva questions and concise answers

1. **What is the difference between X25519 and ML-KEM-768?**
   X25519 is a classical elliptic-curve Diffie–Hellman key-agreement method;
   ML-KEM-768 is a post-quantum key-encapsulation mechanism. They establish
   shared secrets in different ways and have different threat assumptions.

2. **Why combine classical and post-quantum key establishment?**
   Hybrid composition aims to retain the classical component while adding a
   post-quantum component, so the local prototype does not silently depend on
   only one of them.

3. **What does HKDF do here?**
   HKDF-SHA-256 derives a fixed-size, domain-separated session key from the
   two component secrets and the public handshake context. It is not an
   authentication mechanism.

4. **Why bind a transcript to key derivation?**
   Binding the protocol identifier, algorithm identifiers, public keys, and
   ciphertext ensures changed public exchange data derives a different key.
   It does not replace authentication or key confirmation.

5. **What is the HNDL threat?**
   It is the risk that attackers store encrypted traffic today in the hope of
   decrypting it later with improved cryptanalytic capabilities, including
   future quantum capabilities.

6. **Does successful key agreement prove the participants' identities?**
   No. Matching keys show matching cryptographic inputs in this simulation;
   certificates, signatures, or another authenticated protocol are needed to
   establish identity.

7. **Why is this not automatically post-quantum TLS?**
   The prototype is an in-memory Python flow, not a standardized TLS
   handshake. TLS/mTLS requires a supported implementation, certificate
   validation, negotiation, authentication, and deployment testing.

8. **What does the benchmark actually measure?**
   It measures serial, in-process Python and installed-library cryptographic
   operations with `time.perf_counter_ns`. It does not measure the network,
   certificates, TLS, Envoy, Kubernetes, or application latency.

9. **What happens when ML-KEM ciphertext validation uses implicit rejection?**
   A same-length altered ciphertext can produce a replacement secret rather
   than an explicit error. Higher-level authenticated transcript binding and
   key confirmation are needed; the local test verifies that the altered
   exchange does not produce matching hybrid keys.

10. **What further work is required before production deployment?**
    Use a reviewed standardized hybrid TLS implementation, authenticate
    workloads with certificates, design key storage and rotation, enforce OPA
    and NetworkPolicies, validate monitoring, threat-model the system, and
    perform real integration and deployment testing.
