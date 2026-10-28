# Project Audit — Week 2 Readiness

**Audit date:** 2026-10-27  
**Scope:** `G:\internship\-Post-Quantum-Zero-Trust-Micro-segmentation-Mesh-main`  
**Audit type:** read-first, execution-based review. No implementation files, checked-in results, or infrastructure configuration were changed.

**Follow-up note:** The legacy `pqcrypto` path described in this audit was
subsequently migrated to the current X25519 + native ML-KEM-768 implementation.
The audit-time findings below are retained as historical context; current test
results are recorded in the follow-up change.

## 1. Executive summary

**Final readiness: NOT READY — BLOCKERS REMAIN.**

The repository contains a functioning educational Python implementation of X25519, ML-KEM-768, and a transcript-bound hybrid HKDF derivation. The current demos pass, the focused Week 1 tests pass, and the current `cryptography` installation successfully performs ML-KEM-768 encapsulation and decapsulation.

Week 2 has a sound start: the repository contains a TLS 1.3 connection-establishment benchmark harness, a 1,000-sample classical loopback dataset, raw observations, metadata, and percentile calculations. However, no hybrid TLS dataset exists, no classical-versus-hybrid comparison can be calculated, and the repository cannot provide direct negotiated-group evidence for either experiment from the current environment. The recorded classical rows identify the group as `CONFIGURED:X25519`, which is useful configuration evidence but is not a direct TLS instrumentation result.

The primary blockers are:

1. This machine's Python SSL backend is OpenSSL 3.0.18 and rejects `X25519MLKEM768`; therefore the hybrid experiment cannot start.
2. No compatible Envoy binary, compatible OpenSSL CLI, Docker, Kubernetes tooling, or checked-in Envoy configuration is available locally.
3. There is no hybrid raw CSV, comparison output, or Week 2 comparison chart.
4. At audit time, the full suite was not green because a legacy demo used an
   undeclared `pqcrypto` dependency. That path has since been migrated without
   adding the dependency.
5. The broader zero-trust deployment is represented only partially in this checkout: three NetworkPolicies and a small standalone Rego policy exist, but no deployed Envoy/OPA/Kubernetes/mTLS configuration or PCAP evidence is present.

## 2. Repository and environment overview

### Repository contents and provenance

The root contains Python source, tests, scripts, documentation, Day 5 in-process benchmark artifacts, Week 2 classical TLS artifacts, three Kubernetes NetworkPolicy manifests, one Rego file, and one historical Envoy evidence text file.

The supplied directory is **not a Git working tree**: both `git status --short` and `git log -5 --oneline --decorate` returned `fatal: not a git repository`. Consequently, this audit cannot establish commit identity, authorship, change history, or whether existing files were modified after the recorded runs.

### Current execution environment

| Item | Observed value | Audit implication |
| --- | --- | --- |
| OS / architecture | Windows 11 / AMD64 | Current execution target |
| Python | 3.13.12 | Runs the current Python implementation |
| Project `.venv` | Absent | Commands use the global interpreter, not the documented isolated environment |
| `cryptography` | 50.0.2 | X25519 and `MLKEM768*` APIs are available and exercised |
| pytest | 9.1.1 | Outside `requirements.txt` constraint `pytest>=8.0,<9.0` |
| Matplotlib | 3.11.2 | Available for existing Day 5 chart tooling |
| Python SSL backend | OpenSSL 3.0.18 30 Sep 2025 | Accepts X25519 configuration but rejects `X25519MLKEM768` |
| Envoy, Docker, Kubernetes, Istio, OPA, OpenSSL CLI, packet tools | Not found on `PATH` | Current checkout cannot live-verify service-mesh, policy, PCAP, or direct OpenSSL group negotiation |

`python scripts/check_environment.py` reported four passing checks (Python, `cryptography`, X25519, and ML-KEM-768) and one failure because the active interpreter is not under `.venv`.

The current audit sandbox also denied loopback socket use (`WinError 10013`) while attempting an isolated local TLS smoke run. This is an execution-environment restriction, not evidence that the stored historical classical run is invalid. It does mean the stored TLS result cannot be re-executed from this audit session.

## 3. Verified Week 1 cryptographic status

### X25519 and HKDF-SHA-256

The current X25519 implementation in [`src/classical_ecdh.py`](../src/classical_ecdh.py) generates native X25519 keys, validates key object types, derives a shared secret with `X25519PrivateKey.exchange`, and derives a configurable 32-byte session key with HKDF-SHA-256. The default HKDF `info` gives the classical flow a domain-separated context.

Evidence:

- `python scripts/demo_ecdh.py` completed with matching shared secrets and matching 32-byte HKDF keys.
- The focused current cryptography tests, together with ML-KEM, hybrid, and integration tests, passed: `36 passed in 0.42s`.
- The code does not print private keys or secret bytes in the normal demonstration path.

### ML-KEM-768

[`src/pqc_mlkem.py`](../src/pqc_mlkem.py) uses `cryptography.hazmat.primitives.asymmetric.mlkem.MLKEM768PrivateKey` and `MLKEM768PublicKey`, not a custom KEM. Key generation, encapsulation, and decapsulation executed successfully with the installed `cryptography` 50.0.2 backend. It validates input types and documents ML-KEM implicit rejection; the tests exercise malformed-length ciphertext and a same-length modified ciphertext that produces a different replacement secret.

Evidence:

- `python scripts/demo_mlkem.py` completed successfully.
- The environment checker performed an actual ML-KEM-768 encapsulation/decapsulation agreement check.
- `tests/test_mlkem.py` is included in the 36 focused passing tests.

This establishes availability and functional use of the library's ML-KEM-768 API. It does **not** establish that this application has an independent FIPS validation, a protocol security proof, or production authorization.

### Hybrid construction and context binding

[`src/hybrid_exchange.py`](../src/hybrid_exchange.py) is the current Week 1 path. It:

- uses X25519 and ML-KEM-768 component secrets;
- length-prefixes both component secrets before deriving the hybrid input keying material;
- constructs a canonical public transcript containing the protocol identifier, algorithm identifiers, public keys, and ML-KEM ciphertext;
- hashes that transcript with SHA-256 for the HKDF salt and binds the context plus transcript hash into HKDF `info`;
- derives a 32-byte key; and
- aborts on component or final-key disagreement rather than silently falling back to one component.

`python scripts/demo_hybrid.py` passed, reporting X25519 and ML-KEM component agreement, hybrid derivation, matching 32-byte session keys, and public-only integration metadata.

### Authentication and key-handling boundary

This is an educational, in-process key-establishment prototype, not an authenticated protocol or TLS implementation. It has no certificates, signatures, peer identity, replay defense, wire protocol, key confirmation, or secure-channel transport. The limitation is accurately described in [`docs/security_limitations.md`](security_limitations.md) and [`docs/integration_guide.md`](integration_guide.md).

One design concern remains: `HybridExchangeResult` in [`src/hybrid_exchange.py`](../src/hybrid_exchange.py) includes component shared secrets and final session keys in an ordinary return object so unit tests can compare them. [`src/integration.py`](../src/integration.py) safely exposes only public metadata, but direct callers can still receive key material. The project should keep the integration façade as the only application-facing interface or redesign the low-level testing interface before a broader integration.

### Legacy path follow-up

The previously stale [`src/hybrid_key_exchange.py`](../src/hybrid_key_exchange.py),
[`src/benchmark_hybrid.py`](../src/benchmark_hybrid.py), and
[`tests/test_hybrid_key_exchange.py`](../tests/test_hybrid_key_exchange.py) now
reuse the current X25519 + native ML-KEM-768 workflow. The educational demo
still performs AES-GCM encryption and recovery, but prints only safe status,
length, and message metadata. `pqcrypto` remains intentionally absent from
`requirements.txt`.

## 4. Actual test and demonstration results

The table below preserves the audit-time observations from 2026-10-27. The
legacy `pqcrypto` failure is historical; the follow-up migration now reports
2 focused tests passed and 105 full-suite tests passed.

| Command | Result | Interpretation |
| --- | --- | --- |
| `python scripts/check_environment.py` | 4 passed, 1 failed | Crypto capabilities work; `.venv` is missing/inactive. |
| `python scripts/demo_ecdh.py` | Passed | Real local X25519/HKDF agreement; no secret values printed. |
| `python scripts/demo_mlkem.py` | Passed | Real local ML-KEM-768 encapsulation/decapsulation agreement. |
| `python scripts/demo_hybrid.py` | Passed | Current X25519 + ML-KEM-768 hybrid prototype agrees and returns sanitized metadata. |
| `python -m pytest -q tests\\test_ecdh.py tests\\test_mlkem.py tests\\test_hybrid.py tests\\test_integration.py` | 36 passed | Current Week 1 implementation tests pass. |
| `python -m pytest -q tests\\test_tls_benchmark.py --basetemp .tmp\\audit_tls_pytest_20261027` | 49 passed | Week 2 parser, schema, statistics, comparison, and validation unit tests pass using synthetic data. |
| `python -m pytest -v` | 99 collected; 89 passed, 1 failed, 9 errors | The 9 errors are pytest temporary-directory creation failures in the sandbox; the code failure is the stale `pqcrypto` path. |
| `python -m pytest -q --tb=short --basetemp .tmp\\audit_pytest_20261027_2308` | 98 passed, 1 failed | Confirms the nine original errors were temporary-directory infrastructure errors. Remaining failure: `TestHybridKeyExchange.test_hybrid_exchange_and_encryption`. |
| `python scripts/verify_tls_group.py --mode hybrid ...` | Exit 1 | Expected fail-closed result: OpenSSL 3.0.18 rejects `X25519MLKEM768`. |

There were no skipped tests in the collected full suite. At audit time, the
standard full suite was **not passing**, despite the current primary
cryptographic path passing.

## 5. Verified Week 2 TLS benchmarking status

### Benchmark data and methodology audit

[`scripts/benchmark_tls.py`](../scripts/benchmark_tls.py) implements separate classical and hybrid modes, fixes TLS to version 1.3, creates a fresh TCP socket for each measurement, uses `time.perf_counter_ns`, excludes warm-ups from the stored dataset, records success/failure rows, preserves raw CSV data, produces metadata, and computes mean, sample standard deviation, minimum, maximum, p50, p95, and p99 using linear interpolation.

The timing boundary starts before `socket.create_connection()` and ends after `SSLContext.wrap_socket()` completes. It is correctly described as **TLS connection-establishment latency** because it includes TCP setup; it is not a pure cryptographic or pure TLS-handshake timer.

The harness creates a new TCP+TLS connection per sample, but it does not record `SSLSocket.session_reused` or otherwise prove that TLS session resumption was disabled. The stored documentation calls the observations full handshakes; that claim remains unverified without session-reuse instrumentation or independent TLS traces.

### Classical data audit

The checked-in artifact [`results/week2/classical-full/raw.csv`](../results/week2/classical-full/raw.csv) contains exactly 1,000 rows under run ID `4752b3255573`. Recalculation from the raw CSV exactly matches [`metadata.json`](../results/week2/classical-full/metadata.json):

| Metric | Classical X25519 result |
| --- | ---: |
| Measured attempts | 1,000 |
| Successful rows | 1,000 |
| Failed rows | 0 |
| Success rate | 100.0% |
| TLS version labels | `TLSv1.3` only |
| Group label | `CONFIGURED:X25519` only |
| p50 | 15.3588 ms |
| p95 | 22.0534 ms |
| p99 | 28.3162 ms |
| Mean | 12.5092 ms |
| Standard deviation | 7.3165 ms |
| Minimum / maximum | 1.0869 / 33.0668 ms |

The metadata is good for a local baseline: it records host and port, warm-up count (100), sample count, timer boundary, Python/OpenSSL versions, OS, machine/processor, intended group, certificate-file location, and success/failure counts. The data should be described as an **observed TLS 1.3 loopback connection-establishment baseline under an X25519-only client configuration**, not as direct proof of the negotiated named group.

### TLS negotiation verification

The default benchmark labels every successful row `CONFIGURED:<expected group>`. This is transparent, but it is not direct negotiated-group telemetry. Python's SSL API does not expose the named group, and `scripts/benchmark_tls.py` does not invoke the stronger `--use-openssl` verification path before recording data.

[`scripts/verify_tls_group.py`](../scripts/verify_tls_group.py) correctly marks its Python-only method as `CONFIGURED_ONLY:<group>` and leaves `negotiated_group_verified` false. It can parse direct group output from `openssl s_client` when an appropriate CLI is available, but no OpenSSL CLI was found in this environment.

Therefore:

- the classical group's selection is a reasonable consequence of a one-group TLS 1.3 configuration, but is **not directly verified evidence** under this audit's standard;
- the hybrid group is not configured, negotiated, or verified locally; and
- statements in the README/Week 2 guide that a valid run must have actual group confirmation exceed what the default Python benchmark path currently enforces.

### Hybrid experiment and comparison

No `results/week2/hybrid-full/` directory exists. The hybrid verification command fails before network connection with:

```text
Python ssl cannot set group 'X25519MLKEM768': unknown elliptic curve name 'X25519MLKEM768'.
```

This is the correct fail-closed behavior. There are no hybrid raw observations, no comparison CSV or JSON, and no Week 2 charts in `results/week2/charts`, `results/week2/processed`, or `results/week2/raw`.

The existing `results/latency_comparison.png` and `results/payload_size_comparison.png` belong to the Day 5 in-process cryptographic benchmark, not real TLS. Visual inspection confirms that their displayed latency medians (0.1768, 0.3306, and 0.5736 ms) and payload values (64, 2,272, and 2,336 bytes) agree with `results/benchmark_summary.csv`; their titles explicitly say in-process/not network traffic. They are correct supporting charts for Day 5, but they cannot serve as Week 2 TLS comparison charts.

[`evidence/envoy-pqc-build-verification.txt`](../evidence/envoy-pqc-build-verification.txt) contains historical textual evidence of an Envoy 1.41.0-dev/BoringSSL build and an OpenSSL client negotiating `X25519MLKEM768` on another machine. The referenced binary and `/tmp/envoy-pqc.yaml` are not in this checkout, so the evidence is useful background but cannot verify this machine or make a reproducible benchmark here.

## 6. Broader Week 2 integration audit

| Area / owner | Status | Evidence and limitation |
| --- | --- | --- |
| Person 1 — PQC Envoy build | IMPLEMENTED — NOT VERIFIED | Historical text evidence names an external Envoy 1.41.0-dev/BoringSSL build and a successful direct handshake. No local binary, image, configuration, checksum, build recipe, or executable endpoint is available. |
| Person 2 — OPA/Rego | PARTIALLY COMPLETE | [`authz.rego`](../authz.rego) is a small rule that permits only `input.role == "admin"`. It is not connected to Envoy `ext_authz`, has no bundle/service/deployment, and could not be evaluated because `opa` is unavailable. The standalone instructional file claims a richer developer/resource/action policy that does not match the checked-in Rego. |
| Person 3 — Kubernetes deployment | PARTIALLY COMPLETE | Three ingress NetworkPolicies exist under [`kubernetes/network-policies`](../kubernetes/network-policies). No namespace, workload, Service, Deployment, sidecar, Istio, certificate, Secret, or PeerAuthentication manifests are present. `kubectl`, `minikube`, and `istioctl` are unavailable, so static files were not cluster-validated in this audit. |
| Certificates and workload identity | NOT IMPLEMENTED | No non-temporary certificate/key material, trust configuration, certificate manifest, or mTLS endpoint is checked in. Historical Day 4 notes are not reproducible from this workspace. |
| Person 5 — PCAP/evidence | NOT IMPLEMENTED | No `.pcap`/`.pcapng` files, capture procedure, or packet tooling is present. A PCAP alone would still need matching client/server group instrumentation to prove the named group. |
| Monitoring dashboard | NOT APPLICABLE to Week 1/2 deliverable | `app.py` presents simulated security-event data and is not connected to TLS, Envoy, OPA, or benchmark data. |

## 7. Documentation and submission readiness

Documentation coverage is substantial: architecture, integration, security limitations, reproducibility, presentation notes, Day 5 microbenchmark report, Week 2 guide, and Week 2 report all exist. The strongest documents distinguish the in-process prototype from TLS/mTLS and do not claim production readiness.

However, the documentation is not fully submission-ready because it contains other inconsistent historical material:

- [`docs/day-5-hybrid-cryptography.md`](day-5-hybrid-cryptography.md) has been updated to describe the current X25519 + ML-KEM-768 implementation and its in-process benchmark boundary.
- [`docs/reproducibility_checklist.md`](reproducibility_checklist.md) records a project `.venv` and pytest 8.4.2, while the current workspace has no `.venv` and uses pytest 9.1.1.
- The Week 2 guide correctly explains Python's group-verification limitation, but its statement that successful samples must verify the actual group does not match the default benchmark's `CONFIGURED:` labels.
- The Week 2 report is honest about the missing hybrid data, but should avoid calling classical samples “verified” in a way that implies direct named-group telemetry.
- Historic Istio/Minikube narrative documents do not have checked-in manifests or runnable current evidence, so they should be labelled historical/unverified until re-collected.

## 8. Master status matrix

| ID | Work item | Status | Evidence | Missing work | Priority |
| --- | --- | --- | --- | --- | --- |
| 1 | Python environment | PARTIALLY COMPLETE | Python 3.13.12 and `cryptography` 50.0.2 work; environment script 4/5 pass | Create/use `.venv`; reconcile pytest version | P2 |
| 2 | X25519 implementation | VERIFIED COMPLETE | Current source, demo, focused tests | None for educational prototype | P2 |
| 3 | ML-KEM-768 implementation | VERIFIED COMPLETE | `cryptography` MLKEM768 API, demo, focused tests | No independent validation/protocol proof claimed | P2 |
| 4 | Hybrid key derivation | VERIFIED COMPLETE | Length-prefixed two-secret HKDF, matching-key tests | Keep raw secret-bearing result internal | P2 |
| 5 | Transcript/context binding | VERIFIED COMPLETE | Canonical public transcript and changed-context tests | Add a known-answer/each-component mutation test | P2 |
| 6 | Cryptographic unit tests | VERIFIED COMPLETE | Current-path focused tests pass; legacy demo migrated | Add missing vectors/mutation coverage | P1 |
| 7 | Hybrid demonstration | VERIFIED COMPLETE | `demo_hybrid.py` passes, sanitized output | None for prototype | P2 |
| 8 | Python cryptographic benchmark | VERIFIED COMPLETE | 500-iteration Day 5 raw/summary/metadata/charts | Keep labelled as non-TLS | P2 |
| 9 | TLS classical baseline | PARTIALLY COMPLETE | 1,000-row raw CSV, metadata, TLSv1.3 labels | Re-run with direct group and session-reuse evidence in reproducible environment | P1 |
| 10 | TLS hybrid benchmark | BLOCKED | Harness refuses unsupported group; no hybrid artifacts | Compatible Envoy/BoringSSL or OpenSSL endpoint/client | P0 |
| 11 | Negotiated-group verification | PARTIALLY COMPLETE | Optional OpenSSL verifier exists; Python path labels `CONFIGURED` | Direct client/server/instrumentation evidence for both modes | P0 |
| 12 | p50/p95/p99 analysis | PARTIALLY COMPLETE | Classical statistics recompute from raw data; 49 analysis tests pass | Hybrid statistics and comparison | P0 |
| 13 | Raw CSV and metadata | PARTIALLY COMPLETE | Classical raw CSV and metadata complete | Equivalent hybrid artifacts plus direct-verification output | P0 |
| 14 | Benchmark charts | NOT IMPLEMENTED | No Week 2 comparison output; Day 5 charts are different | Generate charts from verified two-mode results | P1 |
| 15 | Week 2 benchmark report | PARTIALLY COMPLETE | Report and guide exist, classical metrics traceable | Update claims after direct verification and hybrid run | P1 |
| 16 | Envoy configuration | NOT IMPLEMENTED | Only historical external evidence text | Check in version-pinned config/image/build instructions and validate | P0 |
| 17 | OPA integration | PARTIALLY COMPLETE | Standalone simple Rego policy | Add/test `ext_authz` wiring, decision contract, identity binding | P1 |
| 18 | Kubernetes integration | PARTIALLY COMPLETE | Three ingress NetworkPolicies | Add/deploy workloads, services, sidecars, mTLS and validation evidence | P1 |
| 19 | PCAP evidence | NOT IMPLEMENTED | No capture files/procedure/tools | Capture authorized run; pair with direct TLS group evidence | P2 |
| 20 | Security limitations | VERIFIED COMPLETE | Clear prototype/deployment boundaries in security docs | Update if implementation scope changes | P2 |
| 21 | Documentation | PARTIALLY COMPLETE | Broad documentation set exists; Day 5 legacy design reconciled | Reconcile environment and verification claims | P1 |
| 22 | Mid-project review package | PARTIALLY COMPLETE | Week 1 evidence and classical data exist | Hybrid measurement, direct negotiation evidence, integration evidence, clean tests | P0 |
| 23 | Legacy P-256/`pqcrypto` artifacts | VERIFIED COMPLETE | Active demo, benchmark, test, and Day 5 documentation use the current implementation | None | P1 |
| 24 | Git provenance | BLOCKED | Root is not a Git repository | Provide repository clone or exported commit metadata | P3 |

## 9. Prioritized missing work and effort estimate

### Blockers and dependencies

The hybrid comparison depends on an externally supplied, reproducible PQC-capable TLS endpoint and direct negotiated-group telemetry. Person 1/infrastructure controls the compatible Envoy or TLS build; certificate and workload-identity owners control the trusted test credentials; Person 4 can run the comparison only after those prerequisites exist. The broader integration evidence also depends on the owners of the Envoy, OPA, Kubernetes, and review/PCAP workstreams. No repository-only code change can substitute for those dependencies.

### Must complete

| Priority | Missing work | Why it matters | Files/components | Exact next action and verification | Dependency | Estimate | Blocks review? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Obtain a reproducible PQC-capable TLS environment | Without it, no hybrid result can be measured | Envoy/BoringSSL or supported OpenSSL client/server, pinned build info | Person 1 supplies a pinned binary/image, config, build/version output, and reachable endpoint; verify the group is available before benchmarking | Person 1 / infrastructure | 4–8 h after environment access | Yes |
| P0 | Directly verify the negotiated group for both modes | Configuration labels do not meet the required evidentiary standard | `verify_tls_group.py`, compatible CLI or server instrumentation | Run an independent client/server command that reports `X25519` and `X25519MLKEM768`; archive outputs with host/version/run ID | Person 1 and certificate owner | 2–4 h | Yes |
| P0 | Produce comparable classical and hybrid datasets | p50/p95/p99 overhead cannot be calculated without matched valid data | `benchmark_tls.py`, `analyze_tls_results.py`, `results/week2` | Use same host/path, certificate policy, warm-up, iteration count, timer boundary, and concurrency; save raw CSV, metadata, verification outputs, analysis and charts | Person 4 with PQC endpoint | 3–6 h | Yes |
| P1 | Repair the active full test suite | A review submission should not contain a known failing test | Historical legacy P-256/`pqcrypto` failure; follow-up now passes | Preserve the clean full-suite result | None, subject to owner approval for cleanup | 1–3 h | Yes for a defensible code review |
| P1 | Establish the actual integration boundary | Current claims cannot be reproduced from this checkout | Envoy config, OPA `ext_authz`, Kubernetes manifests, certificates, test endpoint | Either check in version-pinned manifests/evidence and test them, or mark those team deliverables explicitly pending in the review package | Persons 1–3 | 6–16 h | Yes if broader integration is presented as completed |

### Should complete

| Missing work | Why it matters | Exact next action | Verification | Estimate |
| --- | --- | --- | --- | --- |
| Create and use a project `.venv` with compatible package versions | Reproducibility and declared dependency compliance | Create the documented environment, install from requirements, record resulting versions | `check_environment.py` fully passes; full test suite runs in that interpreter | 0.5–1 h |
| Record session resumption state or disable/separate it | Fresh TCP does not by itself prove full TLS handshakes | Add/record `session_reused` or use supported TLS instrumentation and state methodology precisely | Metadata identifies every sample as full or resumed | 1–2 h |
| Reconcile report and README wording | Prevents overclaiming the group verification and benchmark scope | Change “verified group/full handshake” language to match direct evidence; update after new run | Reviewer can trace every claim to raw data and evidence | 1–2 h |
| Add component-sensitivity and HKDF known-answer tests | Increases confidence in the custom prototype derivation | Test independent changes to each component secret and a stable HKDF vector | New focused tests pass | 1–2 h |
| Capture authorized PCAP plus correlated logs | Supporting review evidence | Document capture command, target, time, run ID, filters, and group output | PCAP, client/server group evidence, and raw CSV share identifiers | 2–4 h |

### Optional improvements

- Add CPU, memory, and concurrency profiling after the valid serial comparison exists (4–8 h).
- Add additional load levels, remote-path measurements, and confidence intervals after methodology is approved (4–12 h).
- Refactor the simulated monitoring dashboard only if it becomes a review deliverable; it does not advance the blocked TLS comparison.

### Essential-work estimate

The work controlled by this repository is approximately **10–21 engineering hours** after a compatible PQC TLS endpoint is available. Environment acquisition/build time, access approvals, and teammate coordination are external dependencies and may extend that estimate substantially.

## 10. Recommended next three actions

1. **Secure the compatible hybrid TLS endpoint and its reproducible configuration.** Collect exact Envoy/BoringSSL or OpenSSL version, build/image identifier, TLS config, CA setup, and endpoint details.
2. **Run direct group-verification evidence before any timing run.** Save unambiguous `X25519` and `X25519MLKEM768` negotiation outputs for new full handshakes, with certificate validation enabled.
3. **Run matched two-mode measurements and regenerate the analysis.** Preserve raw CSVs, metadata, direct verification outputs, comparison CSV/JSON/charts, and update the report only from those artifacts.

After the TLS environment work, rerun the full suite and preserve the resulting
output alongside the benchmark evidence.

## 11. Final assessment

The Week 1 educational hybrid-key-establishment deliverable is genuinely working and carefully scoped. The Week 2 benchmark tooling and a classical local baseline are useful, traceable foundations. They are not yet a defensible classical-versus-hybrid TLS benchmark because the hybrid TLS group cannot be configured locally, the recorded group is not independently observed, and no paired hybrid results exist.

For a mid-project review, present the project as **a verified cryptographic prototype with a partially complete classical TLS baseline and a documented PQC-TLS environment blocker**. Do not present it as deployed PQC mTLS, an Envoy-integrated system, or a completed classical-versus-hybrid latency comparison until the P0 evidence is collected.
