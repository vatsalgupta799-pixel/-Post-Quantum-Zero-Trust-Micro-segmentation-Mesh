> **Week 2 update (28 October 2026):** Local OpenSSL positive and negative TLS checks succeeded; session freshness and a matched comparison remain unverified. Process-inclusive timings are not handshake latency. See the [current audit](project_audit_week2.md).

> **Week 1 handover:** The local X25519 + ML-KEM-768 construction is unauthenticated educational code, not production TLS or mTLS. Both components are required and errors abort the exchange. Public results expose metadata only; internal educational code handles secrets, which Python cannot guarantee to erase. See the [reproduction record](reproducibility_checklist.md).

> The public `perform_hybrid_exchange` result now contains metadata only. Internal educational and benchmark callers can still access secret bytes; its representation redacts secret fields. Python does not guarantee memory zeroization. See [the current audit](project_audit_week2.md).

# Security Limitations and Deployment Boundary

## Educational-prototype status

Task 4 is an educational, in-process demonstration of hybrid key
establishment. It uses maintained library APIs for X25519, ML-KEM-768, and
HKDF-SHA-256, but it is not an independently audited protocol, a formally
proven hybrid construction, or a production-ready security service.

The verified local workflow proves only that two simulated services can derive
matching 32-byte keys when supplied with the same valid exchange material. It
does not prove the identity of either participant, establish a network
connection, or protect application traffic.

## What the prototype implements

- X25519 establishes a classical shared secret between two simulated services.
- ML-KEM-768 establishes a second shared secret through encapsulation and
  decapsulation.
- The hybrid module length-prefixes both component secrets, binds a canonical
  public transcript, and uses HKDF-SHA-256 to derive the final 32-byte key.
- The public integration façade returns verification metadata rather than
  private keys, component secrets, transcript bytes, or final session-key
  bytes.

These implementation facts are not a claim of a complete authenticated key
exchange or post-quantum transport protocol.

## Authentication, transport, and replay limits

X25519 and ML-KEM key establishment alone do not authenticate a peer. An
active attacker who can replace unauthenticated public values can mount a
man-in-the-middle attack. The prototype also does not implement certificate
validation, signatures, peer-name validation, channel binding, replay
protection, explicit key confirmation messages, a wire format, AEAD-protected
application traffic, or a negotiated protocol version.

It is therefore not TLS, mTLS, Envoy configuration, or a replacement for a
reviewed protocol. A future deployment must use reviewed, version-matched
hybrid TLS support and separately validate workload identity and certificates.

## Custom hybrid-composition limitation

The prototype's HKDF construction is documented in
`docs/architecture.md`: it length-prefixes the X25519 and ML-KEM secrets, uses
the SHA-256 hash of a canonical public transcript as salt, and domain-separates
HKDF `info`. This is deliberate and testable, but this project makes no formal
security proof or independent cryptographic-review claim for that construction.

Production systems should use a reviewed, standardized hybrid key-exchange or
TLS implementation rather than treating this Python composition as a deployed
protocol design.

## ML-KEM implicit rejection

For a same-length altered ML-KEM ciphertext, ML-KEM may use implicit rejection
and return a replacement shared secret instead of raising an error. The tests
verify that behavior and verify that the resulting hybrid keys no longer match
in the local simulation. A production protocol still needs authenticated
transcript binding and key confirmation; decapsulation success is not proof
that a ciphertext is authentic.

## Key handling and lifecycle limits

The internal simulated exchange result contains shared secrets and session
keys so unit tests can verify agreement. It is not a general-purpose
application API. Other code should use `src.integration.establish_hybrid_session`,
which exposes only non-secret metadata.

This prototype has no hardware-backed storage, Vault integration, key rotation,
revocation, retention policy, backup policy, process isolation strategy, or
guaranteed memory zeroization. Python does not guarantee immediate erasure of
immutable byte strings from process memory. Long-lived credentials and future
application session keys need a separately designed lifecycle and access
control model.

## Dependency and implementation risks

The verified environment uses `cryptography` 50.0.2 within the declared
dependency range. That confirms installed API availability, not a security
certification of this application. Production work must track library and
platform security updates, lock and review dependency versions, validate the
chosen backend on target platforms, and assess side-channel, fault, memory,
and operational risks beyond the scope of Python unit tests.

## Logging and observability boundary

Normal demonstrations, benchmark artifacts, and the integration result do not
print or serialize private keys, component shared secrets, transcript bytes,
or final session keys. Monitoring for a future deployment should record only
safe metadata such as protocol version, operation outcome, sanitized failure
code, and correlation ID. It must exclude keys, raw KEM ciphertexts when not
needed, certificate private material, and sensitive request contents.

## Requirements before a real Zero-Trust deployment

A real deployment requires all of the following in addition to key
establishment:

1. certificate-backed workload identity and mTLS validation;
2. a reviewed hybrid TLS implementation supported by the exact Envoy/TLS build
   and both peers;
3. authenticated authorization decisions, for example through OPA, bound to
   the authenticated workload identity and request context;
4. default-deny Kubernetes NetworkPolicies and tested allowed paths;
5. approved secret-management, rotation, auditing, incident response, and
   monitoring practices; and
6. threat modelling, protocol review, integration tests, deployment testing,
   and operational approval for the target environment.

Until those conditions are met, this repository should be presented as a
verified educational prototype with documented limitations.
