# Week 1 handover update — 28 October 2026

This update supersedes older Week 1 environment and test claims below. It records local verification in the `main-checkout`; no teammate infrastructure or historical result was modified.

- A new project `.venv` was created using Python 3.13.12. The first `python -m venv .venv` attempt failed at `ensurepip` because the default temporary directory was not writable; the partially created environment was preserved. Setting `TEMP` and `TMP` to `.tmp/week1-install-temp-20261028` and running `.\.venv\Scripts\python.exe -m ensurepip --upgrade --default-pip` succeeded. The requirements installation command `.\.venv\Scripts\python.exe -m pip install -r requirements.txt --disable-pip-version-check` completed successfully. All 40 declared requirements matched; `.\.venv\Scripts\python.exe -m pip check` found no broken installed requirements.
- Installed versions: Python 3.13.12, pip 25.3, cryptography 50.0.2, pytest 8.4.2, Matplotlib 3.11.2; Python SSL OpenSSL 3.0.18. This is one Windows installation, not a complete lockfile or a cross-platform verification.
- `.\.venv\Scripts\python.exe scripts\check_environment.py`: 5 passed, 0 failed, 0 blocked. `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/week1-baseline-20261028-unique --tb=short`: 126 passed in 1.30 s before changes. After adding component-failure tests, the same command with the fresh `.tmp/week1-final-20261028-unique` base produced **128 passed in 1.08 s**, 0 failures, skips, errors or reported warnings. Use a new nonexistent basetemp each time.
- `.\.venv\Scripts\python.exe scripts\demo_ecdh.py`, `scripts\demo_mlkem.py`, `scripts\demo_hybrid.py`, and `src\hybrid_key_exchange.py` all completed successfully using the same interpreter. The final demo includes local AES-GCM. Normal outputs and public result tests did not reveal secret bytes.
- Code inspection confirms both components contribute to HKDF, component mismatches abort and neither component has a fallback path. Added tests inject a failure into X25519 and ML-KEM operations and confirm the public exchange raises. Existing agreement, tampering and secret-representation tests pass. Internal educational callers still access key material; Python does not guarantee erasure.
- The preserved Week 1 raw CSV has 500 complete-exchange samples per mode; recalculated medians are 0.176800 ms classical, 0.330650 ms ML-KEM and 0.573650 ms hybrid, matching the historical report. No new performance run was made. These are in-process cryptographic timings, not network or TLS timings.

**Week 1 readiness:** The educational prototype, demos, tests and Windows reproduction are ready for a scoped review. It remains unauthenticated and is not production TLS or mTLS; cross-platform reproduction and independent security review have not been performed. For the mid-project review, use [presentation notes](presentation_notes.md), explain the recorded benchmark scope, and coordinate deployment and integration evidence with the owning teammates. Week 2 session evidence, negative TLS tests and a matched performance comparison remain separate and incomplete.

---

> **Merge verification update:** A later isolated local OpenSSL 4.1.0 server run succeeded for both groups, with certificate and hostname validation: 2/2 measured attempts per mode after one warm-up. See [smoke evidence](../evidence/merge-tls-20261028/README.md). This supersedes the earlier local connectivity blocker only; session freshness, the negative cases, a meaningful comparison, and integrated mesh evidence remain unverified.

# Rectification update — 28 October 2026

**Readiness: NOT READY for a comparative handshake or integrated mesh claim.** This update supersedes conflicting current or historical audit passages below, which are preserved. The root is not a Git working tree, so changes since the earlier audit cannot be established through Git. No teammate infrastructure was changed.

## Verified local work

- Before edits: `python -m pytest -q -p no:cacheprovider --basetemp .tmp/rectify-baseline-20261028-unique --tb=short`: **108 passed**, no skips, errors or warnings, 1.16 s. After edits the same command with fresh `.tmp/rectify-final2-20261028`: **114 passed**, 1.14 s, no skips, errors or warnings. Never reuse a basetemp: pytest can remove it.
- `python scripts/check_environment.py`: 4 passed, 1 failed (no active project `.venv`). `python -m pip check`: no broken installed requirements; comparison with requirements.txt found 5 matching, 24 missing and 11 mismatched packages, including pytest 9.1.1 against <9. This is not a clean dependency installation.
- `python scripts/demo_ecdh.py`, `python scripts/demo_mlkem.py`, `python scripts/demo_hybrid.py`, and `python src/hybrid_key_exchange.py` completed successfully without printing keys or component secret bytes. The latter demonstrates AES-GCM; the hybrid exchange remains an unauthenticated educational construction.
- Public `perform_hybrid_exchange` returns only success and key length. Educational/benchmark callers explicitly use an internal secret-bearing result; its representation redacts the six secret fields. Python cannot guarantee memory zeroization or stop deliberate internal access. Agreement and component failure tests remain in place.
- The OpenSSL CLI verdict now requires certificate verification, exact TLS 1.3, an exact group and a completed connection. `CONNECTED` alone is insufficient. The benchmark records session reuse as unknown, retains excluded warm-up attempts in metadata and does not fabricate freshness. The comparison analyzer rejects unknown session status. New tests cover these cases and the public result. Integration errors suppress underlying exception chains in normal tracebacks to avoid exposing internal details.

## TLS and benchmark evidence

The OpenSSL CLI reports 4.1.0; Python SSL reports 3.0.18. The attempts in [local TLS evidence](../evidence/rectify-20261028/local-tls-cases.json) and [repeat](../evidence/rectify-20261028-b/local-tls-cases.json) all failed to connect. A separate Python loopback connection produced `PermissionError: [WinError 10013]` despite a successful bind. Therefore these are **not** positive TLS or meaningful wrong-host, untrusted-certificate or wrong-group tests. A further isolated attempt with elevated local access produced five 10-second client timeouts; its [record](../evidence/rectify-20261028-c/local-tls-cases.json) also does not establish a handshake or a meaningful negative case. The cause of those timeouts was not established. Both group tests and all negative cases must be rerun in an environment permitting loopback connections.

No new comparison was collected. The old smoke process duration includes Python verification wrapper, OpenSSL startup, TCP, TLS and certificate checks, output capture, shutdown and parsing, measured by `perf_counter_ns`; it is not handshake-only latency. Five `openssl version` process measurements were approximately 23–28 ms, but do not isolate TLS or explain the roughly one-second smoke duration; there is no evidence for a specific cause. Preflight and warm-ups precede measurements; warm-ups are now retained separately. Individual successful attempts require direct group and certificate evidence, but actual session freshness is unknown and analysis rejects it. Server version, configuration and network path must be supplied as provenance. The legacy Python baseline must not be combined with the old smoke. No 1,000-sample experiment or chart regeneration was possible.

## Status and priority

| Item | Status | Next action | Priority |
| --- | --- | --- | --- |
| Educational hybrid API | Implemented and unit tested | Independent security review if used beyond demonstration | P1 |
| TLS identity and exact group | Unit tested only | Run trusted positive and negative live checks for both groups | P0 |
| Session evidence | Unknown, explicitly recorded | Obtain independently observed new/reused session telemetry and update analyzer | P0 |
| Timing and matched comparison | Blocked | Diagnose shutdown delay, establish boundaries, then collect 1,000 attempts per mode if feasible | P1 |
| Envoy/OPA/Kubernetes/PCAP | Team inputs missing | Collect the items below and validate integration | P1 |
| Dependencies | Nonconforming global environment | Reproduce in a requirements-consistent environment | P2 |

Request from Person 1: reproducible PQC-capable Envoy build and version, exact configuration, endpoint, trust material and negotiated-group telemetry. Person 2: OPA policy, Envoy ext_authz configuration, and allow/deny evidence. Person 3: deployment manifests, sidecars, certificates and trust configuration, and pod connectivity/isolation evidence. Person 5: capture procedure and run-linked PCAP, timestamps and endpoints, plus supporting TLS group telemetry. Historical Envoy text and network policies are not integrated proof. Authorization overhead belongs in a separately measured experiment.

For the mid-project review, demonstrate the standalone prototype with its limitations; obtain working local access and session telemetry, then gather a controlled matched dataset and coordinate the integration evidence. No Envoy benchmark, mTLS validation, or integrated mesh completion is claimed.

---

# Current audit update — 28 October 2026

**Status: NOT READY — BLOCKERS REMAIN** for a defensible comparative Envoy handshake benchmark and integrated mesh demonstration. This update supersedes the older audit below wherever they differ; it is retained to preserve the prior work. In particular, the earlier claims that the current verifier lacks hostname checking or exact group matching are now stale. This audit did not modify application code or teammate configuration.

## Environment and scope

This workspace is Windows 11 AMD64, Python 3.13.12, cryptography 50.0.2, pytest 9.1.1 and Matplotlib 3.11.2. Python's SSL backend reports OpenSSL 3.0.18; the separately installed CLI at `C:\Program Files\OpenSSL-Win64\bin\openssl.exe` reports OpenSSL 4.1.0. No project `.venv` exists; the environment checker reports 4 passed and 1 failed for that reason. The global pytest is outside the `pytest>=8,<9` requirement; no clean requirements installation was verified. Envoy, Docker, kubectl and OPA were not found on PATH; availability on another machine or outside PATH is unknown. Git reports this is not a repository, so current changes and history cannot be established. No private key contents were inspected.

## Week 1 and test evidence

[X25519](../src/classical_ecdh.py) and [ML-KEM-768](../src/pqc_mlkem.py) both work in the installed library. The latter uses the library's standardized ML-KEM-768 API; this is not an independent FIPS validation. [Tests](../tests/test_mlkem.py) distinguish malformed lengths from same-length tampering and implicit rejection. [Hybrid exchange](../src/hybrid_exchange.py) length-prefixes both 32-byte component secrets and the transcript fields, uses the SHA-256 transcript hash and versioned context with HKDF-SHA-256, and checks agreement without classical fallback. Tests exercise altered transcript/context and component failures. The construction is an unauthenticated in-memory educational prototype, not reviewed TLS or mTLS; transcript binding does not authenticate peers. The low-level `HybridExchangeResult` contains secrets and session keys, and its default dataclass representation can expose them; [integration.py](../src/integration.py) instead returns metadata. Demos do not print key bytes. A separate [AES-GCM demo](../src/hybrid_key_exchange.py) exists, so broad README statements that symmetric encryption is absent need review.

| Command | Actual result |
| --- | --- |
| `python -m pytest -v` | 108 collected; 98 passed, 10 setup errors, 0 failed, 0 skipped, 0 collection errors; no warnings reported. `tmp_path` could not create numbered directories in the default temporary location. |
| `python -m pytest -v --basetemp=.tmp/audit-pytest-20261028-unique -rA --tb=short` | 108 collected and passed, 0 failed, 0 skipped, 0 errors, no warnings reported. |
| `python -m pytest -q --basetemp=.tmp/audit-pytest-20261028-second --tb=short` | 108 passed in 0.98 s. Use a fresh, nonexistent basetemp path: pytest can remove an existing basetemp. |
| `python scripts/check_environment.py` | 4 passed, 1 failed: `.venv` absent. |
| `python scripts/demo_ecdh.py`, `python scripts/demo_mlkem.py`, `python scripts/demo_hybrid.py` | All completed successfully with sanitized output. |

These results do not verify live TLS, Envoy, Kubernetes, authorization or independent cryptographic certification.

## TLS negotiation and benchmark evidence

The current [TLS verifier](../scripts/verify_tls_group.py) invokes `openssl s_client` with TLS 1.3, the requested group, certificate-chain checking and explicit hostname or IP verification. It normalizes a trailing comma and compares the group exactly; nonzero client exit is rejected. Unit tests cover exact-group matching and nonzero exit. No live endpoint was tested in this audit, and wrong-name/untrusted-CA end-to-end behavior remains unverified. `new_handshake` and `session_reused` are assigned rather than independently observed; a fresh process, no session input and `-no_ticket` limit resumption but are not independent session telemetry.

The saved [local OpenSSL smoke run](../results/week2/openssl41-local-smoke/) predates hostname verification. Its preflight output reports TLS 1.3, certificate-chain verification and, respectively, `Peer Temp Key: X25519` and `Negotiated TLS1.3 group: X25519MLKEM768`. Three rows per mode report the same groups, 3 successes and 0 failures. Preflight output and CSV are retained, but full individual client transcripts are not. The old runs do not demonstrate peer-name checking or the strengthened verifier. They are OpenSSL loopback observations, not Envoy results.

| Smoke statistic | Classical (ms) | Hybrid (ms) | Difference (ms) | Relative |
| --- | ---: | ---: | ---: | ---: |
| p50 | 1042.3057 | 1066.1231 | +23.8174 | +2.2851% |
| p95 | 1054.0361 | 1088.6357 | +34.5996 | +3.2826% |
| p99 | 1055.0788 | 1090.6368 | +35.5580 | +3.3702% |
| mean | 1044.8879 | 1062.8202 | +17.9323 | +1.7162% |
| sample standard deviation | 9.4295 | 30.1045 | — | — |
| min / max | 1037.0184 / 1055.3395 | 1031.2004 / 1091.1371 | — | — |

Values are traceable to the six [raw rows](../results/week2/openssl41-local-smoke/classical/raw.csv) and [hybrid rows](../results/week2/openssl41-local-smoke/hybrid/raw.csv), with linear interpolation at `(n-1)*p` and sample standard deviation. The values in the saved [summary](../results/week2/openssl41-local-smoke/comparison/combined_summary.csv) match. Three samples do not support meaningful p95/p99 or overhead conclusions. `perf_counter_ns` times the subprocess operation, including process startup, TCP, TLS, verification, process exit and parsing: it is not isolated handshake latency. Investigate the roughly one-second duration before interpreting performance. Warm-ups are excluded; measured attempts and failures are recorded without evident retries, while warm-up failures are discarded. Historical metadata labels Python SSL as `openssl_backend`, not the actual CLI; current code also records `openssl_client_version`. Server version, configuration and independent resumption evidence need stronger provenance.

The older [classical-full](../results/week2/classical-full/) has 1,000 samples but only configuration-restricted group evidence and uses a different Python timing path. It must not be compared to the hybrid smoke. [Python operation benchmark results](../results/benchmark_summary.csv) are not TLS measurements. Smoke charts exist; visual inspection and fresh regeneration were not performed during this audit. The generated smoke report's analysis paths do not match its preceding output paths. The [Week 2 guide](week2_benchmarking_guide.md) and [report](week2_benchmark_report.md) document the smoke and hostname limitation, but portions of the report retain outdated blocked-hybrid setup and the README has stale or non-existent analysis inputs; all commands were not independently validated.

## Broader integration

[Envoy evidence](../evidence/envoy-pqc-build-verification.txt) records a separate machine's Envoy 1.41.0-dev/BoringSSL and a direct X25519MLKEM768 TLS handshake with a self-signed certificate warning. It is historical textual evidence, not a locally reproduced run or proof of mTLS. Binary, configuration and provenance are not available in this workspace. [authz.rego](../authz.rego) defaults to deny and permits an admin role; no runnable ext_authz wiring or authorization tests were established here. Three [Kubernetes NetworkPolicies](../kubernetes/network-policies/) exist, but no verified sidecar deployments, trust configuration or pod connectivity were found. No PCAP was found in the file inventory; request capture provenance from Person 5, with endpoint/run IDs and group telemetry, since a PCAP alone is not necessarily proof of the negotiated group. Keep authorization out of the primary handshake comparison or report it separately.

## Current master status matrix

P0 invalidates a core result; P1 is required for the planned review; P2 improves reproducibility; P3 is optional.

| ID | Work item | Status | Evidence | Missing work | Priority |
| --- | --- | --- | --- | --- | --- |
| 1 | Python environment | PARTIALLY COMPLETE | Global interpreter and checker | `.venv`, requirements-consistent reproduction | P2 |
| 2 | X25519 | VERIFIED COMPLETE | Demo and unit tests | None for educational demo | P3 |
| 3 | ML-KEM-768 | VERIFIED COMPLETE | Demo and implicit-rejection test | Independent validation outside scope | P3 |
| 4 | Hybrid derivation | PARTIALLY COMPLETE | Agreement and failure tests | Secret-bearing low-level result and repr | P1 |
| 5 | Context/transcript | VERIFIED COMPLETE | Code and altered-input tests | Peer authentication remains absent | P2 |
| 6 | Crypto unit tests | VERIFIED COMPLETE | Full suite passes with writable temp | Clean dependency environment | P2 |
| 7 | Hybrid demos | VERIFIED COMPLETE | All three ran successfully | None for local demo | P3 |
| 8 | Python benchmark | IMPLEMENTED — NOT VERIFIED | Results, code and charts exist | Fresh run and chart review | P2 |
| 9 | Classical TLS baseline | PARTIALLY COMPLETE | 1,000 legacy and 3 direct smoke rows | Comparable verified current run | P1 |
| 10 | Hybrid TLS benchmark | PARTIALLY COMPLETE | 3 local smoke rows | Matched larger Envoy run | P1 |
| 11 | Group and identity verification | PARTIALLY COMPLETE | Saved group preflights; current code and unit tests | Live validation of current verifier and negative cases | P0 |
| 12 | p50/p95/p99 analysis | PARTIALLY COMPLETE | Code, tests and smoke summaries | Adequate sample size and controlled timing | P1 |
| 13 | Raw CSV and metadata | PARTIALLY COMPLETE | Saved six smoke rows, metadata | Run provenance, actual server and session evidence | P1 |
| 14 | Charts | PARTIALLY COMPLETE | Smoke charts present | Meaningful data and visual validation | P2 |
| 15 | Benchmark report | PARTIALLY COMPLETE | Reports with smoke data | Reconcile stale setup and valid results | P1 |
| 16 | Envoy build/config | PARTIALLY COMPLETE | Historical direct handshake text | Accessible reproducible build/config and endpoint | P1 |
| 17 | OPA integration | PARTIALLY COMPLETE | Rego rule | ext_authz and behavior tests | P1 |
| 18 | Kubernetes integration | PARTIALLY COMPLETE | NetworkPolicies | Deployments, sidecars, trust and connectivity proof | P1 |
| 19 | PCAP evidence | NOT IMPLEMENTED | No capture found | Run-linked capture and negotiated-group evidence | P1 |
| 20 | Security limitations | PARTIALLY COMPLETE | [Security document](security_limitations.md) | Explicit secret-bearing interface and trust boundaries | P1 |
| 21 | Documentation | PARTIALLY COMPLETE | Guides and [README](../README.md) exist | Correct stale claims and execute commands | P1 |
| 22 | Mid-project package | PARTIALLY COMPLETE | [Presentation notes](presentation_notes.md), evidence | Valid benchmark and team integration evidence | P1 |

## Prioritized work and estimates

Estimates are active hours, excluding waiting for teammates and run time. They are planning ranges, not measured durations.

### Must complete

| Missing work and why | Component / exact next action | Verification | Dependency | Hours | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| End-to-end verifier proof: prevent false identity/group claims | `scripts/verify_tls_group.py`, TLS tests: run both groups with trusted endpoint and add wrong-host, untrusted-CA and wrong-group live tests | Correct cases pass; negatives fail closed | Person 1 endpoint and trust material or local OpenSSL | 2–4 | Yes for trusted claims |
| Meaningful timing: process duration obscures TLS cost | `scripts/benchmark_tls.py`: diagnose one-second duration, quantify overhead; use supported handshake-level instrumentation if feasible or label connection timing explicitly | Compare controlled repetitions and establish timer boundaries | Compatible TLS client / Person 1 | 3–6 | Yes for handshake-latency claims |
| Matched comparative runs: 3 samples do not support tails | `results/week2`, harness: agree sample count, warm-up and equal config; run hundreds, preferably 1,000, attempts per mode, preserving all outcomes and fresh-session evidence | Recalculate statistics from raw rows and verify every group's identity | Person 1, Person 3 for cluster | 3–6 plus runtime | Yes |
| Safe result boundary: low-level result exposes secrets | `src/hybrid_exchange.py`, callers and tests: design restricted interface and non-secret representation with scope agreed | Tests check returned public metadata and logs | User approval for implementation | 2–4 | Yes for requested secrecy criterion; educational review possible with disclosure |
| Integrated proof: components not demonstrated together | Request version-pinned Envoy config, OPA/ext_authz evidence, manifests, trust settings and endpoint from Persons 1–3 | Group, identity, allow/deny, network isolation and connectivity checks; measure auth separately | Persons 1–3 | 4–10 coordination/validation; implementation extra | Yes for integrated-mesh claims |
| Review evidence: connect results to a real run | `evidence/`, presentation: request PCAP and capture instructions, timestamps, endpoint, run IDs and client/server group logs | Cross-check provenance against raw data and deployment | Person 5 and endpoint owner | 2–4 | Yes if integrated review requires PCAP |

### Should complete

| Missing work and why | Component / exact next action | Verification | Dependency | Hours | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| Accurate reproducibility | README and Week 2 guide/report: correct paths, old claims and actual TLS timing; regenerate analysis | Run instructions in fresh output dirs; trace metrics and charts to rows | Valid datasets | 2–4 | Yes for defensible benchmark presentation |
| Isolated dependencies | Create `.venv`, install requirements and record CLI/library versions | Checker, dependency check and full suite | Package access | 1–2 | Not for preliminary demo; yes for reproduction claim |
| Security and handover | Security limitations and presentation notes: document unauthenticated protocol, secret-bearing low-level API and integration boundary | Review against current code and evidence | Final implementation/team evidence | 1–2 | No if disclosed |

### Optional improvements

| Missing work and why | Component / exact next action | Verification | Dependency | Hours | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| Additional statistical confidence | Analysis scripts: repeated randomized runs, uncertainty and extra plots | Recompute from raw data and compare repetitions | Valid base dataset | 2–5 | No |

Essential work is approximately **16–34 active hours**, excluding teammate implementation, waiting, and benchmark run time; scope and timing method may change this estimate. Review can cover the working standalone prototype now with limitations, but the requested Envoy comparison and integrated mesh claims remain blocked.

**Next three actions:** (1) establish a trusted compatible endpoint and exercise the current verifier, including negative cases; (2) fix or quantify the process-inclusive timing boundary; (3) coordinate and collect matched datasets with run-linked evidence before publishing charts and conclusions.

---

## Preserved prior audit (superseded where inconsistent with the update above)

# Project audit — Week 2

**Audit date:** 2026-10-28 (Asia/Calcutta). **Scope:** this workspace. The [previous audit](project_audit_week2_20261027_historical.md) is preserved as historical context. No application code or team configuration was changed.

## Executive summary

**NOT READY — BLOCKERS REMAIN** for a defensible Week 2 performance comparison or integrated mesh review. The educational X25519/ML-KEM-768 hybrid demo works in the current global Python environment; 105 tests and three demos pass. A real TLS 1.3 harness and saved local hybrid-group smoke evidence exist, but the current client does not verify the peer hostname, accepts a substring when checking the negotiated group, and times an external process rather than just the handshake. Three samples per mode are insufficient for tail-latency or overhead conclusions. No current comparable Envoy measurements or integrated deployment evidence are present.

## Repository and environment

The root contains Python code, tests, scripts, documentation, Week 1 and Week 2 results, a Rego policy, three NetworkPolicies and [historical Envoy evidence](../evidence/envoy-pqc-build-verification.txt). The root is not a Git working tree: git status returned “not a git repository”; commit identity, changes and provenance cannot be established. Temporary copies are not treated as authoritative source. No private-key contents were read.

| Observation | Evidence and consequence |
| --- | --- |
| Windows 11, AMD64, Python 3.13.12 | Runtime platform information; global Python interpreter. |
| Project .venv absent | Test-Path .venv returned False. The environment checker reported 4 passed, 1 failed (virtual environment), 0 blocked. |
| cryptography 50.0.2, pytest 9.1.1, Matplotlib 3.11.2 | Runtime metadata. pytest is outside the project's pytest>=8,<9 constraint. Pip check does not establish conformity to the project requirements. A clean requirements install was not attempted. |
| Python SSL OpenSSL 3.0.18; OpenSSL CLI 4.1.0 | Python SSL and the installed CLI have different backends. The CLI is not on PATH. The benchmark metadata field openssl_backend records Python SSL, not the actual CLI version; cryptography also has its own backend. |
| Envoy, Docker, kubectl and OPA not found on PATH | Current integrated deployment cannot be verified here. Loopback socket bind succeeded; this alone does not demonstrate endpoint availability. |

## Week 1 cryptography

[classical_ecdh.py](../src/classical_ecdh.py) uses native X25519 and HKDF-SHA-256; matching secrets, 32-byte keys, context separation and invalid inputs are exercised by passing tests and demo. [pqc_mlkem.py](../src/pqc_mlkem.py) uses the library ML-KEM-768 API; key generation, encapsulation and decapsulation work. [test_mlkem.py](../tests/test_mlkem.py) distinguishes malformed ciphertext length from same-length tampering, for which implicit rejection yields a replacement secret. Using the standardized API does not establish independent FIPS validation.

[hybrid_exchange.py](../src/hybrid_exchange.py) length-prefixes both secrets and public transcript fields; it binds the SHA-256 transcript hash and versioned context to HKDF-SHA-256 and derives a 32-byte key. Tests cover agreement, context and transcript changes, tampering and component failures. This construction is custom, local and unauthenticated; agreement does not authenticate a peer or prevent MITM. Its low-level HybridExchangeResult **contains component secrets and session keys**, and its default dataclass representation can expose them if logged. This fails the requested ordinary-result secrecy property. The separate [integration.py](../src/integration.py) result exposes metadata only, and normal demos do not print key bytes.

[hybrid_key_exchange.py](../src/hybrid_key_exchange.py) also demonstrates AES-GCM encryption/decryption, with a passing tamper test. It remains an in-memory demonstration. README statements that symmetric encryption is not implemented are therefore too broad.

## Actual test results

Executed before changing the report using the global interpreter:

| Command | Observed |
| --- | --- |
| python -m pytest -v -p no:cacheprovider --basetemp .tmp/audit_20261028 | 105 collected, 105 passed, 0 failed, 0 skipped, 0 collection errors, no warnings reported, 1.31 s. Temporary test output was isolated. |
| python scripts/check_environment.py | 4 passed, 1 failed because .venv is absent, 0 blocked. |
| python scripts/demo_ecdh.py | Passed; matching secrets and 32-byte keys. |
| python scripts/demo_mlkem.py | Passed; matching ML-KEM secrets. |
| python scripts/demo_hybrid.py | Passed; matching hybrid keys, 32 bytes, metadata-only output. |
| python -m pip check | No broken installed package requirements; does not validate the project requirements file. |

Passing unit tests do not demonstrate a running Envoy, a cluster, peer-hostname verification, a valid performance study or PCAP provenance. No live TLS endpoint was started in this audit; below we distinguish saved evidence from a fresh run.

## TLS negotiation and measurement audit

[verify_tls_group.py](../scripts/verify_tls_group.py) invokes OpenSSL with TLS 1.3, one requested group, chain-validation failure handling, CA settings and optional client credentials. It requires reported protocol, certificate-chain success and group for benchmark samples. However:

1. **P0 identity:** -servername sets SNI; there is no -verify_hostname or -verify_ip. Verification: OK does not establish that the certificate identifies the requested peer. Stored certificate-verification claims establish chain verification, not hostname authentication.
2. **P0 group check:** the comparison uses substring matching. Classical X25519 is therefore accepted inside X25519MLKEM768 or another longer label. Exact matching after appropriate syntax normalization is needed. The saved classical preflight explicitly reports Peer Temp Key: X25519, 253 bits, and the saved hybrid preflight explicitly reports Negotiated TLS1.3 group: X25519MLKEM768; these particular records show the named groups despite the generic check's flaw.
3. The program sets session_reused=False and new_handshake=True instead of deriving them from independent telemetry. A new process, no supplied session and -no_ticket constrain resumption, but the boolean is not independent proof.
4. Each sample times the complete verify_tls_group subprocess call with perf_counter_ns. Process start, TCP setup, TLS, process termination and output parsing are included. This is connection-establishment process duration, not isolated handshake latency. Investigate the roughly one-second values before drawing conclusions.
5. Warm-ups are excluded from measured rows but their failures are discarded. Measured attempts are retained and failures counted; no retries are visible. Metadata omits actual CLI/server versions, server configuration and identity verification.

### Saved data and statistics

[openssl41-local-smoke](../results/week2/openssl41-local-smoke/) contains three measured attempts after one warm-up per mode on local ports 18445/18444: 3 successes and 0 failures each. Preflight output reports TLS 1.3, the expected named groups and chain verification. CSV records per-sample group labels but not full raw per-sample OpenSSL output. The [comparison report](../results/week2/openssl41-local-smoke/comparison/comparison_report.md) and summary match the six raw rows:

| Process-inclusive latency | X25519 (ms) | X25519MLKEM768 (ms) | Difference (ms) | Relative |
| --- | ---: | ---: | ---: | ---: |
| p50 | 1042.3057 | 1066.1231 | 23.8174 | 2.2851% |
| p95 | 1054.0361 | 1088.6357 | 34.5996 | 3.2826% |
| p99 | 1055.0788 | 1090.6368 | 35.5580 | 3.3702% |
| mean | 1044.8879 | 1062.8202 | 17.9323 | 1.7162% |
| sample standard deviation | 9.4295 | 30.1045 | — | — |
| minimum / maximum | 1037.0184 / 1055.3395 | 1031.2004 / 1091.1371 | — | — |

Percentiles use linear interpolation at (n - 1) times p, consistently in both modes. Running python scripts/analyze_tls_results.py with the two smoke raw.csv files and output directory .tmp/audit_comparison_20261028 succeeded and reproduced these figures and charts. No visual verification of every chart or independent validation of historical provenance was performed. **These are smoke observations, not meaningful overhead or p99 estimates.**

The historical [classical-full](../results/week2/classical-full/) records 1,000/1,000 successes, p50 15.3588 ms, p95 22.0534 ms and p99 28.3162 ms, using a different Python timing path and a configuration-only group label. It cannot be compared fairly to the process-inclusive hybrid smoke or used as direct group proof. The [Week 1 report](benchmark_report.md) and results/benchmark_results.csv describe in-process cryptographic measurements, not TLS.

## Broader team integration

| Responsibility | Status | Evidence and boundary |
| --- | --- | --- |
| Person 1: PQC Envoy | PARTIALLY COMPLETE | Historical text records Envoy 1.41.0-dev/BoringSSL and a direct hybrid TLS handshake on another machine, with a self-signed certificate warning. Binary, exact configuration, build provenance and live endpoint are unavailable here; this is not a reproducible current deployment. |
| Person 2: OPA | PARTIALLY COMPLETE | [authz.rego](../authz.rego) defaults to deny and permits admin role. No verified Envoy ext_authz configuration or executed policy test in this audit; OPA absent from PATH. No isolated authorization-overhead measurement. |
| Person 3: Kubernetes | PARTIALLY COMPLETE | Three [NetworkPolicies](../kubernetes/network-policies/) exist. No application/sidecar deployment, trust configuration or live pod connectivity is demonstrated here. |
| Person 5: testing and review | PARTIALLY COMPLETE | Written evidence and presentation notes exist. No PCAP found under project evidence, results, docs or Kubernetes directories; no capture provenance ties endpoint and run to packet evidence. Client/server negotiated-group telemetry should accompany any capture. |

## Documentation and submission readiness

[README](../README.md), [architecture](architecture.md), [integration guide](integration_guide.md), [security limitations](security_limitations.md), [reproducibility checklist](reproducibility_checklist.md), [presentation notes](presentation_notes.md), [Week 2 guide](week2_benchmarking_guide.md) and [Week 2 report](week2_benchmark_report.md) exist, but existence does not establish readiness. The README analysis example names classical-full and hybrid-full although the latter is absent and the former lacks accepted direct-group evidence; the generated smoke report similarly gives paths inconsistent with its output commands. The Week 2 report retains obsolete “hybrid blocked” and “no comparison possible” passages alongside smoke results, and describes the historical Python timing boundary as though it applied to the current CLI harness. Its certificate claims omit missing hostname validation. Current .venv instructions do not match the actual environment. Security documentation should distinguish metadata-only integration from the secret-bearing lower-level result. Every documented command was not independently executed.

## Master status matrix

P0 invalidates core evidence; P1 is needed for planned review; P2 supports reproducibility; P3 is optional.

| ID | Work item | Status | Evidence | Missing work | Priority |
| --- | --- | --- | --- | --- | --- |
| 1 | Python environment | PARTIALLY COMPLETE | Global Python works; checker 4/5 | Isolated environment and compatible requirements | P2 |
| 2 | X25519 | VERIFIED COMPLETE | Demo and tests pass | Production review outside demo scope | P3 |
| 3 | ML-KEM-768 | VERIFIED COMPLETE | Demo and implicit-rejection tests pass | No independent validation claim | P3 |
| 4 | Hybrid derivation | PARTIALLY COMPLETE | Matching 32-byte HKDF keys and failure tests | Secret-bearing ordinary result and repr | P1 |
| 5 | Transcript/context binding | VERIFIED COMPLETE | Length-prefixed transcript and changed-context tests | Authentication remains separate | P2 |
| 6 | Crypto tests | VERIFIED COMPLETE | Passing suite includes crypto tests | Security review and deployment tests separate | P2 |
| 7 | Hybrid demos | VERIFIED COMPLETE | Three demos and AES-GCM test pass | None for local demo | P3 |
| 8 | Python benchmark | IMPLEMENTED — NOT VERIFIED | Raw, summary, metadata and charts exist | Fresh full rerun and visual QA not performed | P2 |
| 9 | Classical TLS baseline | PARTIALLY COMPLETE | 1,000 legacy samples and 3 direct smoke samples | Matched run with corrected validation | P1 |
| 10 | Hybrid TLS benchmark | PARTIALLY COMPLETE | 3 saved direct-group smoke samples | Matched, sufficiently sized study | P1 |
| 11 | Group and identity verification | PARTIALLY COMPLETE | Saved preflight strings name groups | Exact group match and hostname/IP verification | P0 |
| 12 | p50/p95/p99 analysis | PARTIALLY COMPLETE | Smoke calculations regenerated | Valid sample size and robust timing | P1 |
| 13 | Raw CSV and metadata | PARTIALLY COMPLETE | Smoke and historical files | CLI/server versions, identity, provenance and paired run | P1 |
| 14 | Charts | PARTIALLY COMPLETE | Smoke comparison charts regenerated | Valid dataset and visual review | P2 |
| 15 | Benchmark report | PARTIALLY COMPLETE | Reports exist | Resolve contradictions and report sound results | P1 |
| 16 | Envoy build/config | PARTIALLY COMPLETE | Historical direct-handshake text | Accessible build, config, provenance and verified endpoint | P1 |
| 17 | OPA integration | PARTIALLY COMPLETE | Rego policy | ext_authz and behavior tested with team | P1 |
| 18 | Kubernetes integration | PARTIALLY COMPLETE | NetworkPolicies | Deployments, sidecars, trust and connectivity | P1 |
| 19 | PCAP evidence | NOT IMPLEMENTED | No captures found in specified project locations | Capture, provenance and telemetry | P1 |
| 20 | Security limitations | PARTIALLY COMPLETE | Security document exists | Low-level secret result and TLS identity gaps | P1 |
| 21 | Documentation | PARTIALLY COMPLETE | Guides exist | Correct commands, scope and contradictions | P1 |
| 22 | Mid-project package | PARTIALLY COMPLETE | Presentation notes and evidence file | Defensible measurements, team evidence and review narrative | P1 |

## Missing work and prioritized plan

Estimates are active engineering time, not guarantees; team wait time is excluded.

### Must complete

| Task and why | Components and exact next action | Verification | Dependency | Effort | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| Enforce identity and exact group; prevent false success | verify_tls_group.py, benchmark_tls.py and TLS tests: add hostname/IP checks, exact normalized group matching, strict success handling and CLI version capture | Negative wrong-host, untrusted-CA and similar-group tests plus real TLS for both groups | Test endpoint and trusted certificate | 3–6 h | Yes for trusted benchmark |
| Establish meaningful timing | TLS harness: investigate one-second process cost, isolate handshake timing or clearly define connection timing, quantify process overhead and retain warm-up failures | Controlled repeatability and timing-boundary inspection | Suitable TLS instrumentation, Person 1 | 3–6 h | Yes for handshake-latency claims |
| Obtain matched datasets | Benchmark scripts and results/week2: use same endpoint, TLS, certificates, software and network, warm up and collect hundreds, preferably 1,000, attempts per mode including failures | Recompute statistics and confirm groups, identities and session evidence | Person 1; Person 3 if cluster target | 3–6 h active plus run time | Yes |
| Remove ordinary secret exposure | hybrid_exchange.py, callers and tests: design safe public/internal interface and suppress secret repr while keeping demo functional | Tests prove ordinary return/logging avoids secrets and failure behavior remains | Agree implementation scope with user | 2–4 h | Yes for stated safe-result criterion; prototype can be reviewed with limitation disclosed |
| Complete integrated proof | Obtain Envoy build/config, ext_authz policy tests, manifests, trust and reachable endpoint; measure authorization separately | Version-pinned successful TLS, allow/deny and pod connectivity/isolation checks | Persons 1–3 own infrastructure | 4–10 h coordination/validation, team implementation extra | Yes for integrated-mesh claims |
| Assemble review evidence | evidence and presentation docs: collect run-linked client/server telemetry and PCAP if required; document endpoint, timing and capture procedure | Match run ID, endpoint and timestamps; do not rely on PCAP alone for group proof | Person 5 and endpoint owner | 2–4 h | Yes if integration/PCAP required |

### Should complete

| Task and why | Components and exact next action | Verification | Dependency | Effort | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| Correct report and reproduction commands | README and Week 2 docs: reconcile harness, paths, authentication and smoke limitations; regenerate results only after valid runs | Execute commands in a clean directory; trace figures to raw data | Corrected harness and datasets | 2–4 h | Yes for defensible benchmark presentation |
| Reproduce environment | Create project-local .venv, install compatible requirements and document exact versions and CLI path | Environment checker, pip check and full suite | Dependency availability | 1–2 h | No for preliminary review; yes for clean reproduction claim |
| Strengthen security and handover docs | Security limitations and presentation notes: document unauthenticated construction, low-level secret result and trust boundaries | Review against actual APIs and team evidence | Final implementation and team inputs | 1–2 h | No if clearly disclosed |

### Optional improvements

| Task and why | Components and exact next action | Verification | Dependency | Effort | Blocks review? |
| --- | --- | --- | --- | ---: | --- |
| Extra plots and independent runs | Analysis/results: uncertainty, randomized order or separate load experiments | Recompute figures from raw observations and compare repetitions | Valid base benchmark | 2–5 h | No |

**Estimated essential active effort:** 17–36 hours including team validation and the safe-result fix; teammate infrastructure implementation, endpoint availability and execution wait time are additional. A preliminary standalone prototype review can proceed with these limitations disclosed, but it must not be represented as a completed mesh benchmark.

## Next three actions

1. Correct and test hostname/IP validation and exact group matching; independently verify the timing boundary.
2. Coordinate a version-pinned, trusted test endpoint with Person 1 and, if required, Person 3; preserve group and session evidence.
3. Run matched classical and hybrid measurements, analyze raw observations and update the report and presentation with real limitations.

## Final readiness assessment

The local Week 1 educational functionality and current tests are demonstrable. Saved TLS smoke data is capability evidence with validation and timing limitations; the historical Envoy note is evidence from another machine, not current integration proof. Until identity/group verification and experimental methodology are corrected and matched results plus team evidence are obtained, **NOT READY — BLOCKERS REMAIN** for the planned Week 2 benchmark and integrated review claims.

