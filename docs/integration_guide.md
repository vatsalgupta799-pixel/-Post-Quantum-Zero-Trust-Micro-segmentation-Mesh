# Task 4 Integration Guide

## Status and scope

Task 4 currently provides an educational, in-process demonstration of a hybrid
X25519 plus ML-KEM-768 key-establishment flow. It is verified locally, but it
is not a network protocol, TLS implementation, mTLS deployment, identity
system, authorization mechanism, or Kubernetes integration.

The Day 6 interface in `src/integration.py` is a deliberately small boundary
for other application code. It runs the existing two-service simulation,
verifies every component agreement, and returns non-sensitive metadata only.
It does not send messages to a peer or expose a final session key.

## Component responsibilities

| Component | Responsibility | Not supplied by this component |
| --- | --- | --- |
| Task 4 hybrid prototype | Local X25519 and ML-KEM-768 establishment, transcript-bound HKDF, safe status metadata | Remote networking, peer identity, authorization, TLS, or durable key management |
| Certificate-authentication teammate | Workload identities, certificate issuance, trust anchors, SAN validation, and mTLS client/server authentication | Post-quantum key exchange by itself |
| OPA teammate | Policy decisions about whether an identified workload may perform an action | Transport encryption or network isolation |
| Kubernetes teammate | Pod-to-pod restrictions through NetworkPolicies | Workload identity, L7 authorization, or encryption |
| Envoy/service-mesh teammate | TLS/mTLS transport, certificate wiring, connection policy, and service-to-service routing | A direct adapter for this Python prototype |
| Vault or secrets-management teammate | Long-lived credential storage, access controls, rotation, revocation, and audit trails | A replacement for authenticated key establishment or transport security |
| Monitoring teammate | Non-secret operational and security events, such as success/failure codes and policy decisions | Private keys, shared secrets, final session keys, or raw key-exchange material |

These controls complement one another. A successful key exchange does not
authenticate a service or authorize an action, and an authorization decision
does not encrypt traffic.

## Integration interface

Import the public façade:

    from src.integration import HybridIntegrationError, establish_hybrid_session

    try:
        result = establish_hybrid_session()
    except HybridIntegrationError as error:
        # error.code is safe to log; do not log exception causes.
        handle_failure(error.code)

The optional `expected_protocol_version` keyword validates that the caller
expects the implemented `hybrid-v1` format. It accepts only that non-empty
string; it is an integration compatibility guard, not negotiated input. The
current interface accepts no public keys, hostnames, certificates, or network
addresses because the current workflow is intentionally in memory.

### Safe success result

`establish_hybrid_session()` returns an immutable `HybridSessionResult`:

| Field | Meaning |
| --- | --- |
| `success` | Always `True` for a returned result |
| `protocol_version` | `hybrid-v1` |
| `algorithms` | `("X25519", "ML-KEM-768")` |
| `session_key_length` | Verified derived-key length, currently 32 bytes |
| `duration_ms` | Informational local elapsed time for one run; not a benchmark result |
| `verification_checks` | Names of the checks that passed |

It deliberately does not include private keys, component shared secrets, the
public transcript, or final session-key bytes. The implementation discards the
secret-bearing internal result after validation. Python does not provide a
guarantee of immediate memory zeroization; no sensitive data is logged,
serialized, or returned by this interface.

### Failure behavior

The interface raises `HybridIntegrationError` instead of returning a false
success result. The error message is sanitized, while `error.code` identifies
the safe category:

| Code | Meaning |
| --- | --- |
| `INVALID_PROTOCOL_VERSION` | The caller supplied an empty, malformed, or incompatible protocol version |
| `UNSUPPORTED_ALGORITHM` | The selected cryptographic backend cannot provide a required algorithm |
| `KEY_ESTABLISHMENT_FAILED` | A component, transcript, or final agreement check failed |
| `INTERNAL_ERROR` | An unexpected internal failure occurred |

The interface never selects a classical-only or ML-KEM-only fallback.

## Demonstration and tests

From the repository root on Windows:

    .\.venv\Scripts\python.exe scripts\check_environment.py
    .\.venv\Scripts\python.exe scripts\demo_hybrid.py
    .\.venv\Scripts\python.exe -m pytest -v tests\test_integration.py
    .\.venv\Scripts\python.exe -m pytest -v

The demonstration imports the integration façade instead of the lower-level
secret-bearing exchange result. It reports the protocol, algorithms, verified
components, matching-session-key status, and key length without printing key
material.

## Day 5 artifacts

Day 6 preserves the recorded Day 5 benchmark artifacts:

- `results/benchmark_results.csv` — 6,000 measured local timing samples;
- `results/benchmark_summary.csv` — 500 samples for each measured operation;
- `results/benchmark_environment.json` — machine and library metadata;
- `docs/benchmark_report.md` — interpretation and limitations;
- `results/latency_comparison.png` and `results/payload_size_comparison.png`.

These are local, in-process cryptographic measurements. They do not measure
Envoy, TLS, Kubernetes, certificate validation, or network latency. The Day 6
work does not overwrite them.

## Week 2 integration plan

### 1. Keep three stages separate

1. **Current prototype:** The verified Python simulation proves only that its
   two local services derive matching hybrid keys.
2. **Future networked application interface:** Define a reviewed wire format,
   endpoint ownership, replay handling, authentication binding, key
   confirmation, key lifecycle, and a deliberately designed key-consumption
   API. Do not transmit this prototype's raw session key as a general-purpose
   application value.
3. **Future standardized TLS/mTLS deployment:** Use a supported Envoy/TLS
   implementation and its supported named group. Do not insert this Python
   function into an Envoy TLS handshake.

### 2. Validate an Envoy PQC path before configuring it

Current Envoy TLS documentation states that the BoringSSL backend supports the
standard TLS hybrid group `X25519MLKEM768` and exposes TLS-group selection
through `TlsParameters.ecdh_curves`. That is a useful candidate for future
integration, not evidence that this repository has deployed or tested it.
Pin the exact Envoy image/build and TLS provider, then verify the documented
group on both sides with an end-to-end mTLS handshake before enabling it.

Compatibility work must confirm:

1. the exact Envoy release and TLS provider in the deployment;
2. support for `X25519MLKEM768` in that build and in both peers;
3. TLS version, named-group policy, certificate chain, trusted CA, SNI, and
   SAN validation;
4. whether policy requires a fail-closed hybrid group or permits standards-
   based negotiation to X25519/P-256 for legacy peers;
5. how the negotiated group and handshake failures are observed without
   logging secret material;
6. the behavior of the chosen image in the project's required compliance or
   FIPS mode.

Envoy documents upstream and downstream TLS contexts, certificate validation,
and client-certificate requirements. Its current documentation also describes
the hybrid group and its negotiation behavior. Read the version-matched
documentation before deployment because defaults and supported groups can
change:

- [Envoy TLS architecture and PQC support](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/security/ssl.html)
- [Envoy TLS configuration and mTLS validation](https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/securing.html)
- [Envoy TLS parameters, including ECDH curves](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/transport_sockets/tls/v3/common.proto.html)

### 3. Sequence the wider integration

1. Certificate teammate: provision workload certificates and test mutual trust,
   SAN validation, and rotation in a non-production environment.
2. Envoy teammate: configure upstream and downstream mTLS contexts and run
   positive and negative handshake tests with the pinned build.
3. Kubernetes teammate: apply default-deny and explicit allow policies, then
   test that unauthorized pod paths remain blocked.
4. OPA teammate: bind authorization decisions to authenticated workload
   identity and request context; do not use key establishment as an identity
   signal.
5. Monitoring teammate: capture safe event metadata such as component name,
   success/failure code, policy decision, and correlation ID; exclude private
   keys, shared secrets, transcripts containing sensitive values, and session
   keys.
6. Secrets-management teammate: define storage, access, rotation, revocation,
   and audit expectations for long-lived credentials; do not treat the local
   in-memory session key as a persisted secret-management integration.
7. Team: perform an integrated, reproducible test that verifies negotiated
   TLS group, mTLS identity validation, policy enforcement, microsegmentation,
   and safe observability independently.

## Reproducibility checklist

Another developer can reproduce the supported local workflow without changing
system-wide settings:

1. Obtain the repository source and open the repository root.
2. Create a project-local virtual environment:

       python -m venv .venv

3. Install declared dependencies into that environment:

       .\.venv\Scripts\python.exe -m pip install -r requirements.txt

4. Verify the environment:

       .\.venv\Scripts\python.exe scripts\check_environment.py

5. Run the integration demonstration:

       .\.venv\Scripts\python.exe scripts\demo_hybrid.py

6. Run the full regression suite:

       .\.venv\Scripts\python.exe -m pytest -v

7. Read the preserved local benchmark report at
   `docs/benchmark_report.md` and data under `results/`.

### What Day 6 actually verified

Day 6 used the existing project `.venv`, ran the environment checker, ran the
integration demonstration, ran focused integration tests, and ran the full
suite. A newly created clean virtual environment was not created for this
milestone, so fresh-install behavior remains a documented reproducibility
procedure rather than an executed Day 6 result.

## Security boundary

The educational hybrid construction remains subject to cryptographic review.
It does not authenticate peers, provide a secure channel, replace TLS/mTLS,
prove post-quantum security, or establish production readiness. For a real
deployment, use reviewed standardized hybrid TLS support and preserve separate
identity, authorization, segmentation, and monitoring controls.

See `docs/security_limitations.md` for the complete prototype and deployment
boundary, including ML-KEM implicit rejection and key-lifecycle limits.
