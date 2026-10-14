# Proposed Hybrid Key-Exchange Architecture

> **Status: mixed implementation and proposal.** The classical X25519 and
> HKDF baseline described below is implemented and tested. ML-KEM-768, the
> hybrid combiner, authentication, and deployment remain planned. This is not
> an implemented or deployed production system.

## Parties and responsibilities

- **Service A** is the initiating workload. It will create an ephemeral
  X25519 key pair and participate in the ML-KEM-768 encapsulation workflow.
- **Service B** is the responding workload. It will create its ephemeral
  X25519 key pair and publish or authenticate an ML-KEM-768 public key for
  encapsulation.
- **The authenticated transport/control plane** is responsible for identity,
  authorization, replay protection, transcript binding, and policy checks. A
  KEM alone does not provide all of those properties.

## Proposed workflow

```mermaid
sequenceDiagram
    autonumber
    participant A as Service A
    participant B as Service B
    participant Z as Zero-Trust control plane

    Note over A,B: Proposed design; not implemented or deployed
    A->>Z: Request connection and present workload identity
    Z-->>A: Policy decision and authenticated peer metadata
    A->>B: Send X25519 public key and ML-KEM-768 ciphertext
    B->>B: X25519 exchange with A's public key
    B->>B: ML-KEM-768 decapsulation
    B-->>A: Send X25519 public key and authenticated response
    A->>A: X25519 exchange
    A->>A: Retain ML-KEM shared secret
    Note over A,B: Both sides derive the same session key with HKDF
    A<<->>B: Future AEAD-protected application traffic
```

The exact message order, authentication mechanism, transcript fields, error
handling, and key confirmation are intentionally deferred until the protocol
design is reviewed. Public values must be authenticated and bound to the
intended peers and context; simply concatenating values is not a complete
protocol.

## Implemented Day 2 classical baseline

The repository now contains a runnable educational flow for Service A and
Service B:

```mermaid
sequenceDiagram
    autonumber
    participant A as Service A
    participant B as Service B

    Note over A,B: Implemented and tested classical baseline
    A->>A: Generate X25519 private/public key pair
    B->>B: Generate X25519 private/public key pair
    A->>B: Send A public key
    B->>A: Send B public key
    A->>A: X25519(A private, B public) = shared secret A
    B->>B: X25519(B private, A public) = shared secret B
    A->>A: HKDF-SHA-256(shared secret A, salt, info)
    B->>B: HKDF-SHA-256(shared secret B, salt, info)
    A-->>B: Verify session keys match
```

`src/classical_ecdh.py` implements key-pair generation, typed public-key
exchange, X25519 shared-secret derivation, and 32-byte HKDF-SHA-256 session-key
derivation. `scripts/demo_ecdh.py` exercises both simulated services without
printing key material, and `tests/test_ecdh.py` covers agreement, context
separation, reproducibility, independent exchanges, and invalid inputs.

X25519 and HKDF are implemented for this classical baseline. The demonstration
does not authenticate either service; certificates or an authenticated TLS or
application protocol are still required for protection against active
man-in-the-middle attacks.

## Cryptographic roles

### X25519

X25519 is the classical elliptic-curve Diffie–Hellman component. Each party
creates an ephemeral private key, exchanges a public key, and computes the same
X25519 shared secret. The raw result should be passed into a key-derivation
function rather than used directly as an encryption key.

### ML-KEM-768

ML-KEM-768 is the post-quantum component standardized in NIST FIPS 203. It is
a **key-encapsulation mechanism (KEM)**: a recipient has a public/private key
pair, an initiator encapsulates to the public key to produce a ciphertext and
shared secret, and the recipient decapsulates the ciphertext to recover the
same shared secret.

ML-KEM is not a direct replacement for every part of TLS or for every use of
ECDH. It does not, by itself, authenticate a service identity, negotiate a
complete secure-channel protocol, enforce authorization, provide certificate
validation, or replace the symmetric authenticated encryption used for
application data. Those responsibilities remain part of the surrounding
protocol and zero-trust control plane.

## Future hybrid HKDF combiner

Day 2 currently derives a session key from the X25519 shared secret alone.
After ML-KEM-768 is implemented and both components are successfully
authenticated and computed, a future milestone will combine the independent
X25519 and ML-KEM shared secrets with a domain-separated HKDF construction.
The design should make the protocol context explicit, for example by including
a versioned label, both public-key transcripts, peer identities, and any
negotiated parameters in `info`. The hybrid construction must be specified and
reviewed before implementation.

The derived session key could later feed an AEAD such as AES-GCM or
ChaCha20-Poly1305 for application data. Nonces, rekeying, key lifetime,
failure handling, and key erasure also require explicit protocol decisions.

## Relationship to the wider Kubernetes zero-trust project

This component is one cryptographic building block in the wider architecture:

- workload identity and certificate validation establish who is connecting;
- OPA and Kubernetes NetworkPolicies provide authorization and segmentation;
- Envoy or another service-mesh data plane can carry and observe the traffic;
- secrets management protects long-lived configuration and credentials;
- monitoring records policy and handshake outcomes without logging key material.

The hybrid key exchange must not bypass those controls. A successful
cryptographic handshake is not an authorization decision, and a policy
decision must not expose private keys or shared secrets to logs or telemetry.

## Implementation boundary for Day 2

Day 1 verified that the local Python environment exposes X25519 and ML-KEM-768
through the selected `cryptography` package. Day 2 implements and tests only
the classical X25519/HKDF baseline. ML-KEM-768, the hybrid combiner,
certificates, benchmarks, Kubernetes deployment, and any claim of
post-quantum security remain out of scope.
