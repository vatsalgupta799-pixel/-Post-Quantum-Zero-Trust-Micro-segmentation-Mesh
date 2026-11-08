> **Week 3 Vault Part 1:** Vault 2.2.1 has started locally with persistent
> Raft storage and a loopback-only HTTP listener. Initialization, unsealing,
> and token authentication are verified; initialized state survived a restart,
> followed by unsealing and an operator-reported successful token check. See the
> [deployment guide](docs/vault_deployment.md) for the live status, commands,
> architecture and security limitations.

From the project root, if Vault is not already running, start it in a dedicated
PowerShell window with `./vault/bin/vault.exe server -config=vault/config/vault.hcl`.
In another PowerShell window, set `$env:VAULT_ADDR = 'http://127.0.0.1:8200'`,
run `./vault/bin/vault.exe status`, and unseal with two saved shares using
`./vault/bin/vault.exe operator unseal` twice. Run
`python scripts/verify_vault.py --token` to enter a token at a hidden prompt.
Never initialize the existing storage again or put recovery values in chat.

**Vault Part 2:** The local Vault instance has KV v2, a demonstration PKI,
and separate AppRoles for Service A, Service B, and the certificate manager.
See [secret storage](docs/vault_secret_storage.md), [PKI](docs/vault_pki_configuration.md),
[access tests](docs/vault_access_policies.md), and the [Member 4 handover](docs/vault_member4_handover.md).
The initial setup and real-server tests used `python scripts/vault_part2_setup.py kv`,
then `pki`, then `auth`, with the administrator token entered privately. These
phases refuse to overwrite existing mounts or policies and are not restart commands.
To inspect and use configured paths, use the separate application identities and
the API guidance in the handover; do not put tokens or Secret IDs in shell history.
For a read-only administrator inventory, run `python scripts/vault_part2_inventory.py`
and enter an administrator token at its hidden prompt. It records mount types,
authentication methods, and the relevant policy names in ignored `.tmp/`.
The following Vault CLI examples require an already authenticated token with
appropriate permissions; they have not been separately tested here. Use a
private session and never put the token itself in a command:

```powershell
./vault/bin/vault.exe secrets list
./vault/bin/vault.exe policy list
./vault/bin/vault.exe kv get -mount=secret application/service-a/database
# An administrator may create a new synthetic example at an unused path:
./vault/bin/vault.exe kv put -mount=secret application/service-a/new-demo username=demo-user
```

The last command writes data; select an unused path and use synthetic values only.
The service AppRoles deliberately cannot write. The access guide describes the
tested AppRole login and allow/deny tests; the handover describes CSR signing.

> **Week 2 Envoy benchmark:** Two 100-per-group TLS 1.3 handshake runs
> verified X25519 and X25519MLKEM768 against the team endpoint. The results
> include network effects from a Tailscale relay; see the [review handover](docs/week2_review_handover.md)
> for results, evidence, reproduction and limitations.

> **Week 1 reproduction (28 October 2026):** The declared requirements were installed into a new local `.venv` on Windows, and the tests and four demos were run using that environment. See the [reproduction checklist](docs/reproducibility_checklist.md) for exact commands and limitations. The in-memory hybrid exchange is unauthenticated educational code, not production TLS or mTLS; its in-process benchmark is not a TLS or network measurement.

> **Earlier local results:** See [the audit update](docs/project_audit_week2.md).
> Those process-duration observations measure a different interval from the
> later instrumented Envoy handshake study.

# Post-Quantum Zero-Trust Microsegmentation Mesh

## Task 4 — Hybrid Key Exchange Demonstration

A capstone workspace for Task 4 of a Post-Quantum Zero-Trust
Microsegmentation Mesh. It demonstrates local X25519, ML-KEM-768, and hybrid
key establishment, while documenting how a future system could integrate
identity, authorization, service-mesh transport, and microsegmentation. This
repository does not itself deploy mTLS, Envoy, or Kubernetes integration.

## Day 1 — Environment and Repository Setup

This repository is the Task 4 workspace for a college capstone project on a
Post-Quantum Zero-Trust Microsegmentation Mesh. The project now contains
independent classical X25519 and post-quantum ML-KEM-768 demonstrations plus
an educational hybrid key-establishment combiner. It is not an authenticated,
production-ready hybrid protocol.

## Problem statement and motivation

Zero-trust services should authenticate and authorize every connection rather
than assuming that a network location is trusted. A future service-to-service
handshake can combine a conventional elliptic-curve exchange with a
post-quantum KEM, then derive a session key with HKDF. This project is a
learning and prototyping exercise for that design. It is not a claim that the
current repository provides quantum-proof security.

## Scope of Task 4

Day 1 covers:

- project initialization and Git hygiene;
- a project-local `.venv` virtual environment;
- dependency selection and verification;
- X25519 availability checking;
- ML-KEM-768 availability checking;
- the proposed architecture and a recovery plan for unsupported platforms.

Symmetric encryption, certificates, Envoy, OPA, Vault, and service-mesh
integration remain future work. Local benchmarking and the safe integration
façade are implemented; the independent and hybrid key-establishment
components are documented below.

## Day 2 — Classical X25519 Key Exchange

Day 2 implements the classical baseline between two simulated services. Each
service generates an X25519 private key and derives a matching public key. The
services exchange only their public keys; each then uses its own private key
and the peer's public key to independently derive the same 32-byte ECDH
shared secret.

Private keys must remain secret and never leave their service. Public keys are
safe to send as handshake data, but exchanging public keys alone does not
authenticate either service. The wider project will need certificate-based
authentication and an appropriate TLS or protocol integration to address
man-in-the-middle risks.

The shared secret is input to HKDF-SHA-256 rather than being used directly as
an application key. The implementation uses the context
`post-quantum-zero-trust-mesh/classical-ecdh/v1` and accepts a public,
per-session salt. In the demonstration, the salt is generated with a secure
random generator and both simulated services use the same value. The salt is
not a password or a substitute for authentication.

Run the demonstration from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\demo_ecdh.py
```

On Linux/macOS, use `source .venv/bin/activate` before running the same Python
script. If activation is unavailable, invoke the environment interpreter
directly with `.\.venv\Scripts\python.exe scripts\demo_ecdh.py` on Windows or
`./.venv/bin/python scripts/demo_ecdh.py` on Linux/macOS.

Run the automated tests with:

```powershell
python -m pytest -v
```

The expected demonstration reports successful key-pair generation, public-key
exchange, matching shared secrets, matching HKDF session keys, and a 32-byte
session key. It does not print private keys, shared secrets, or session keys.

This is an educational classical baseline, not a production-ready secure
channel. Day 4 composes this result with an independently established ML-KEM
secret; authentication, certificates, and service-mesh integration remain
later milestones.

## Day 3 — Post-Quantum ML-KEM-768

Post-quantum cryptography uses algorithms designed to remain useful even
against future cryptanalysts with large quantum computers. ML-KEM-768 is the
NIST FIPS 203 key-encapsulation mechanism (KEM) used here for an independent,
educational key-establishment flow. It is not an encryption channel or an
authentication protocol by itself.

The verified implementation uses `cryptography` 50.0.2 (within the project's
`cryptography>=47.0.0,<51.0.0` requirement) and its standard
`MLKEM768PrivateKey` and `MLKEM768PublicKey` APIs. No `liboqs-python` package
or native dependency is needed on this machine.

In a KEM exchange, Service B first generates an ML-KEM-768 private/public key
pair and makes only its public key available to Service A. Service A uses that
public key to encapsulate, producing a ciphertext and a new shared secret.
Service A transfers the ciphertext to Service B; Service B uses its private
key to decapsulate and recover the matching shared secret. Private keys and
raw shared-secret bytes are never printed by the module or demonstration.

Run the verified demonstration from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\demo_mlkem.py
```

Run its focused tests, or the entire available test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -v tests\test_mlkem.py
.\.venv\Scripts\python.exe -m pytest -v
```

The normal demonstration reports successful availability, key generation,
public-key availability, encapsulation, ciphertext transfer, decapsulation,
matching secrets, and the 32-byte secret length without displaying sensitive
values. The tests also verify key types, independent exchanges, invalid object
types, malformed ciphertext length, the library's implicit-rejection behavior
for a same-length altered ciphertext, and sanitized demonstration output.

This is a standalone KEM demonstration, not post-quantum TLS or mTLS. It does
not authenticate Service A or Service B or authorize a connection. Day 4
combines its result with X25519 in an educational, transcript-bound HKDF
derivation.

## Day 4 — Hybrid X25519 + ML-KEM-768 Key Establishment

Day 4 combines two independently established secrets so the prototype does not
select either X25519 or ML-KEM-768 as a fallback. Service A and Service B first
derive the same X25519 shared secret using their ephemeral public keys. Service
A then encapsulates to Service B's ML-KEM-768 public key, and Service B
decapsulates the ciphertext to recover the same post-quantum shared secret.

`src/hybrid_exchange.py` reuses the existing Day 2 and Day 3 modules; it does
not implement X25519, ML-KEM, or HKDF mathematics itself. Both 32-byte secrets
are combined as separately four-byte-length-prefixed fields, making their
ordering and boundaries unambiguous.

Both services build the same canonical public transcript in this fixed order:
the `hybrid-v1` protocol identifier, the X25519 algorithm identifier, Service
A's X25519 public key, Service B's X25519 public key, the ML-KEM-768 algorithm
identifier, Service B's ML-KEM public key, and the ML-KEM ciphertext. Each
field has a four-byte length prefix. Private keys and shared secrets are never
included. The SHA-256 transcript hash is used as the public HKDF salt; the
HKDF `info` value length-prefixes the versioned
`post-quantum-zero-trust-mesh/hybrid-hkdf-v1` context and that hash. HKDF-SHA-256
produces a 32-byte session key.

Transcript binding ensures changed public handshake data changes the derived
key. The versioned HKDF context provides domain separation, so the same input
material used in another protocol context does not yield the same key.

Run the hybrid demonstration from the project root.

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\demo_hybrid.py
```

```bash
source .venv/bin/activate
python scripts/demo_hybrid.py
```

Run the focused hybrid tests or all tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -v tests\test_hybrid.py
.\.venv\Scripts\python.exe -m pytest -v
```

The normal demo confirms both component agreements, matching transcripts,
matching hybrid session keys, and a 32-byte key without printing key material.
The tests cover complete and independent exchanges, domain separation,
transcript binding, tampered ML-KEM ciphertext behavior, invalid inputs, and
sanitized output.

This is an educational combiner requiring cryptographic review before any
deployment. It does not authenticate either service, prevent a
man-in-the-middle attack, implement TLS/mTLS, establish a network connection,
or claim complete post-quantum security.

## Day 5 — Performance Benchmarking

Day 5 adds a reproducible, serial in-process benchmark for the three
implemented flows:

- X25519 plus HKDF-SHA-256;
- ML-KEM-768 key establishment;
- the existing hybrid X25519 plus ML-KEM-768 exchange.

The runner records separate timings for isolated operations and complete
exchanges, so the component rows are not added together or confused with the
end-to-end local flow. Every benchmark starts with warm-up iterations, uses
time.perf_counter_ns, verifies correctness outside the timed section, and
retains raw samples alongside mean, median, sample standard deviation, minimum,
maximum, and linearly interpolated 95th-percentile latency.

The checked-in Day 5 artifacts are preserved reference measurements. To run a
fresh benchmark from the project root without overwriting them, write it to an
ignored temporary directory:

~~~powershell
.\.venv\Scripts\python.exe scripts\benchmark.py --warmup 20 --iterations 500 --output-dir .tmp\benchmark-run --report-path .tmp\benchmark-report.md
~~~

The default is 20 warm-up and 500 measured iterations for each operation.
Use smaller values only for a quick smoke check. The runner refuses to replace
existing results unless --overwrite is supplied, so a meaningful historical run
is not lost accidentally. You can also select another result directory and
report path with --output-dir and --report-path.

Run the focused benchmark checks, or all project tests:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -v tests\test_benchmark.py
.\.venv\Scripts\python.exe -m pytest -v
~~~

Generate charts from the fresh measured summary CSV:

~~~powershell
.\.venv\Scripts\python.exe scripts\plot_benchmarks.py --summary-path .tmp\benchmark-run\benchmark_summary.csv --output-dir .tmp\benchmark-charts
~~~

On Linux/macOS, replace the interpreter path with `./.venv/bin/python` and
use forward-slash paths. To deliberately replace the checked-in reference
artifacts, review the difference first and use the explicit `--overwrite`
option; it is not needed for normal reproduction.

Both scripts use only actual results from the current machine. The benchmark
stores raw samples in results/benchmark_results.csv, summary statistics and
public payload sizes in results/benchmark_summary.csv, and non-sensitive
environment metadata in results/benchmark_environment.json. The chart script
creates results/latency_comparison.png and results/payload_size_comparison.png.
The measured analysis is written to docs/benchmark_report.md.

The payload figures describe the cryptographic public keys and ciphertexts
that the in-memory handshake would send; they are not total TLS handshake
sizes or observed network traffic. These local measurements include Python and
installed-library overhead but do not measure network latency, TLS, Envoy,
Kubernetes, certificates, or authentication.

## Week 2 — Real TLS Handshake Benchmarking

Week 2 adds a separate, fail-closed harness for real TLS 1.3
connection-establishment measurements. It compares X25519 only with
X25519MLKEM768 only; every successful sample is validated by an OpenSSL client
that reports the actual negotiated group and certificate-verification result.
It does not reinterpret Day 5 in-process results as TLS measurements.

**Stored classical baseline:** 1,000 fresh TLS 1.3 connections configured for
X25519 over localhost, 100% success rate, median (p50) latency 15.36 ms. It
is retained as a configuration-restricted baseline, not direct named-group
evidence, because that historical Python measurement did not expose the negotiated group.

**Hybrid smoke test complete:** Python remains linked to OpenSSL 3.0.18 and
cannot configure `X25519MLKEM768`, but the harness now uses an installed
OpenSSL 4.1.0 CLI for direct TLS evidence. A local, certificate-validated
three-sample smoke test negotiated `X25519MLKEM768` on every attempt. Its raw
observations and comparison are stored in
`results/week2/openssl41-local-smoke/`. This establishes local capability,
not a statistically meaningful performance result or an Envoy measurement.

### Quick start — local classical test

~~~powershell
# Terminal 1: start a local TLS 1.3 server (auto-generates self-signed cert)
python scripts\local_tls_server.py --port 18443 --group X25519

# Terminal 2: a compatible OpenSSL CLI is required for direct evidence.
$openssl = "C:\path\to\openssl.exe"
python scripts\verify_tls_group.py --mode classical --host 127.0.0.1 --port 18443 --server-name localhost --ca-file .tmp\tls-test\cert.pem --use-openssl --openssl-path $openssl
python scripts\benchmark_tls.py --mode classical --host 127.0.0.1 --port 18443 --server-name localhost --ca-file .tmp\tls-test\cert.pem --openssl-path $openssl --warmup 100 --iterations 1000 --timeout 10 --output-dir results\week2\classical-verified
~~~

### Running against an external endpoint

Replace placeholders with team-provided values:

~~~powershell
python scripts\verify_tls_group.py --mode classical --host HOST --port 8443 --server-name HOST --ca-file /path/to/ca.pem --use-openssl --openssl-path /path/to/openssl
python scripts\verify_tls_group.py --mode hybrid --host HOST --port 8443 --server-name HOST --ca-file /path/to/ca.pem --use-openssl --openssl-path /path/to/openssl
python scripts\benchmark_tls.py --mode classical --host HOST --port 8443 --server-name HOST --ca-file /path/to/ca.pem --openssl-path /path/to/openssl --warmup 100 --iterations 1000 --timeout 10 --output-dir results\week2\classical-verified
python scripts\benchmark_tls.py --mode hybrid --host HOST --port 8443 --server-name HOST --ca-file /path/to/ca.pem --openssl-path /path/to/openssl --warmup 100 --iterations 1000 --timeout 10 --output-dir results\week2\hybrid-verified

~~~

The analyzer requires observed new-session status for accepted rows. The endpoint-dependent commands above are illustrative and require a verified endpoint; the local paired run is linked in the audit.

For mTLS, provide the approved --client-cert and --client-key values to both
modes. Do not disable certificate validation, and stop if verification does
not report TLS 1.3 plus the expected exact group. See
[the Week 2 benchmarking guide](docs/week2_benchmarking_guide.md) and
[the benchmark report](docs/week2_benchmark_report.md) for the controlled
method, results, limitations, and handover requirements.

Run the Week 2 focused tests:

~~~powershell
python -m pytest tests\test_tls_benchmark.py -v
~~~

## Day 6 — Integration Readiness

Day 6 adds a small, safe application-facing interface in
`src/integration.py`. Call `establish_hybrid_session()` to execute the
already-tested local hybrid workflow and receive public verification metadata:
the protocol version, algorithm names, verified 32-byte session-key length,
elapsed local duration, and completed verification checks.

The result deliberately does **not** contain private keys, X25519 or ML-KEM
shared secrets, the transcript, or the final session key. A failure raises
`HybridIntegrationError` with a safe error code; it never reports success or
falls back to one algorithm when a component fails. The current interface is
an in-memory two-service simulation, not a remote API or a TLS handshake.

Run the integration demonstration:

~~~powershell
.\.venv\Scripts\python.exe scripts\demo_hybrid.py
~~~

Run its focused checks and then the full suite:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -v tests\test_integration.py
.\.venv\Scripts\python.exe -m pytest -v
~~~

The demo prints only non-sensitive verification status. It confirms the
X25519 and ML-KEM-768 components, hybrid derivation, matching session keys,
and the expected key length. See
[the integration guide](docs/integration_guide.md) for the safe result format,
teammate boundaries, reproducibility checklist, and a Week 2 plan for
standardized Envoy/TLS integration.

## Day 7 — Final Verification and Submission Materials

Day 7 verifies the existing environment, all three demonstrations, the full
test suite, and the stored benchmark artifacts without replacing them. It also
adds submission-ready material:

- [architecture](docs/architecture.md) — implemented flows and matching Mermaid diagrams;
- [benchmark report](docs/benchmark_report.md) — recorded local measurements and safe rerun commands;
- [integration guide](docs/integration_guide.md) — interfaces and team boundaries;
- [security limitations](docs/security_limitations.md) — explicit prototype and deployment limitations;
- [reproducibility checklist](docs/reproducibility_checklist.md) — what was actually verified; and
- [presentation notes](docs/presentation_notes.md) — a 5–7 minute outline and viva answers.

## Planned technology stack

- Python 3.13 for this development environment;
- `cryptography` for X25519 and ML-KEM-768 API support;
- HKDF for the implemented classical and hybrid session-key derivations;
- pytest for the Day 2 through Day 7 automated tests;
- Matplotlib for Day 5 charts generated from the measured CSV;
- Kubernetes NetworkPolicies, certificate authentication, OPA, Envoy,
  monitoring, and secrets management in the wider capstone project.

`cryptography` is the selected Day 1 implementation because the installed
50.0.2 release exposes both required primitives through maintained APIs. It is
used here as a library capability check, not as a statement that a secure
production protocol has been designed. If the backend cannot expose ML-KEM-768,
the documented fallback is Open Quantum Safe's `liboqs-python` wrapper. That
fallback requires a native `liboqs` build and is intentionally not added to
the Day 1 requirements by default.

## Prerequisites

- Python 3.11 or newer is recommended; this workspace was verified with
  Python 3.13.12.
- Git.
- Internet access to install Python packages from PyPI.
- On a fallback `liboqs-python` installation: CMake, Git, and a C compiler.
  Windows users normally need the Visual Studio Build Tools C++ workload.

## Project structure

```text
hybrid-key-exchange/
├── src/
│   ├── __init__.py
│   ├── classical_ecdh.py       # Day 2 X25519 and HKDF implementation
│   ├── pqc_mlkem.py            # Day 3 standalone ML-KEM-768 wrapper
│   ├── hybrid_exchange.py      # Day 4 hybrid exchange and HKDF combiner
│   ├── benchmark.py            # Day 5 reusable benchmark utilities
│   └── integration.py          # Day 6 safe integration interface
├── tests/
│   ├── test_ecdh.py
│   ├── test_mlkem.py            # Day 3 ML-KEM-768 tests
│   ├── test_hybrid.py           # Day 4 hybrid exchange tests
│   ├── test_benchmark.py        # Day 5 benchmark checks
│   ├── test_integration.py      # Day 6 integration checks
│   └── test_tls_benchmark.py    # Week 2 TLS benchmarking tests
├── scripts/
│   ├── check_environment.py
│   ├── demo_ecdh.py
│   ├── demo_mlkem.py            # Day 3 ML-KEM-768 demonstration
│   ├── demo_hybrid.py           # Day 4 hybrid demonstration
│   ├── benchmark.py             # Day 5 measurement runner
│   ├── plot_benchmarks.py       # Day 5 CSV chart generator
│   ├── local_tls_server.py      # Week 2 ephemeral local TLS 1.3 server
│   ├── verify_tls_group.py      # Week 2 TLS group verification
│   ├── benchmark_tls.py         # Week 2 process-inclusive TLS benchmark harness
│   └── analyze_tls_results.py   # Week 2 comparative analysis and charts
├── docs/
│   ├── architecture.md
│   ├── benchmark_report.md      # Day 5 local measurements report
│   ├── week2_benchmark_report.md  # Week 2 TLS benchmark report
│   ├── week2_benchmarking_guide.md # Week 2 reproduction guide
│   ├── integration_guide.md     # Day 6 teammate integration boundary
│   ├── presentation_notes.md    # Day 7 capstone outline and viva answers
│   ├── reproducibility_checklist.md
│   └── security_limitations.md
├── results/
│   ├── .gitkeep
│   └── week2/                   # Week 2 TLS measurement results
│       ├── classical-full/      # 1,000-sample classical (X25519) run
│       └── comparison/          # Comparative analysis (when hybrid available)
├── evidence/
│   └── envoy-pqc-build-verification.txt
├── .gitignore
├── requirements.txt
├── README.md
└── .python-version
```

## Setup: Windows PowerShell

From the repository root:

```powershell
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\check_environment.py
```

If the `py` launcher reports that no runtime is installed, use `python` as
shown above. If PowerShell activation is restricted, run the same commands
through the environment interpreter without changing execution-policy
settings:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\check_environment.py
```

If `ensurepip` cannot write to the machine temporary directory, use a local
workspace temporary directory for the bootstrap operation:

```powershell
$taskTemp = Join-Path (Get-Location) ".tmp"
New-Item -ItemType Directory -Force -Path $taskTemp | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
.\.venv\Scripts\python.exe -m ensurepip --upgrade
```

## Setup: Windows Command Prompt

```bat
if not exist .venv python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\check_environment.py
```

## Setup: Linux, Ubuntu, or macOS

```bash
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_environment.py
```

On Ubuntu, if `venv` is missing, install the operating-system package
`python3-venv` using the normal administrator-approved package workflow, then
rerun the commands above.

## Verification

The environment checker performs real, non-secret checks. It verifies the
Python version, confirms that the interpreter is the project `.venv`, imports
`cryptography`, performs an X25519 shared-secret equality check, and performs
an ML-KEM-768 encapsulation/decapsulation equality check. It never prints
private keys, ciphertexts, or shared-secret bytes.

Run it from the repository root with:

```powershell
python scripts\check_environment.py
```

or directly through the environment:

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
```

A successful Day 1 run should resemble:

```text
[PASS] Python version: 3.13.12
[PASS] Virtual environment: ...\\hybrid-key-exchange\\.venv
[PASS] cryptography import: 50.0.2
[PASS] X25519 support: import and exchange check passed
[PASS] ML-KEM-768 support: encapsulation and decapsulation check passed
Summary: 5 passed, 0 failed, 0 blocked
```

The exact package version may differ when the allowed range changes. The
script exits 0 when all checks pass, 1 when a check fails, and 2 when a
required capability is blocked or unavailable.

## Troubleshooting ML-KEM-768

If ML-KEM-768 is blocked, first confirm that the environment installed a
`cryptography` version in the supported range and rerun the checker. Do not
silently substitute an obsolete Kyber draft or a different algorithm.

The fallback `liboqs-python` route is experimental and intended for
prototyping. Its official installation path requires the `liboqs` native
library, Git, CMake, a C compiler, and on Windows a visible `oqs.dll`. The
wrapper itself does not bundle the native library. Record the exact build
version and enabled mechanism list if this route is needed.

## Current progress and future milestones

**Completed milestones: Day 1 — Environment and Repository Setup; Day 2 —
Classical X25519 Key Exchange; Day 3 — Post-Quantum ML-KEM-768; Day 4 — Hybrid
X25519 + ML-KEM-768 Key Establishment; Day 5 — Performance Benchmarking; Day
6 — Integration Readiness; Day 7 — Final Verification and Submission
Preparation.** The repository includes actual 500-iteration local benchmark
artifacts, charts, an analysis report, a safe integration interface,
automated regression checks, and submission documentation for the verified
machine.

Planned next steps:

1. Plan and test certificate-backed, standardized Envoy mTLS with a
   version-pinned hybrid TLS capability where supported.
2. Integrate OPA authorization, Kubernetes microsegmentation, and safe
   monitoring as separate controls.
3. Obtain protocol and deployment review before treating any part of the
   educational prototype as production-ready.

## Limitations

This repository does not implement post-quantum mTLS, certificate
authentication or service-mesh deployment. A separate local AES-GCM demonstration exists. The Day 4
hybrid flow establishes a matching session key in a local simulation, but it
does not authenticate services or provide a complete secure channel.
`cryptography`'s low-level asymmetric APIs require careful protocol design,
validation, key lifecycle handling, and review before production use.
See [security limitations](docs/security_limitations.md) for the full boundary.

## Official references

- [NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final)
- [RFC 7748: Elliptic Curves for Security](https://www.rfc-editor.org/rfc/rfc7748)
- [cryptography X25519 documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/x25519/)
- [cryptography ML-KEM documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/mlkem/)
- [Open Quantum Safe liboqs-python](https://github.com/open-quantum-safe/liboqs-python)
- [Open Quantum Safe liboqs](https://github.com/open-quantum-safe/liboqs)

- ## Week 3 — Dynamic Key Rotation

### Overview

Week 3 implements a Dynamic Key Rotation module to manage encryption keys securely throughout their lifecycle.

The implementation is available in:

- `src/Key_rotation.py`
- `src/Test_key_rotation.py`

### Features Implemented

1. **AES-256-GCM Encryption**
   - Uses 256-bit encryption keys.
   - Supports authenticated encryption and decryption.

2. **Manual Key Rotation**
   - Allows keys to be rotated manually.
   - Generates a new encryption key and updates the active key ID.

3. **Automatic Background Rotation**
   - Supports automatic key rotation using a background thread.
   - Provides start and stop controls.

4. **Grace Period Management**
   - Retains previous keys temporarily.
   - Allows previously encrypted data to be decrypted during the grace period.
   - Retires expired keys.

5. **Rotation History**
   - Maintains a record of key rotation events.
   - Supports configurable maximum history size.

6. **Thread Safety**
   - Uses RLock for synchronized key-management operations.

### Testing

Automated tests cover:

- Encryption and decryption.
- Manual key rotation.
- Automatic background rotation.
- Grace-period decryption.
- Expired key retirement.
- Rotation history.
- Maximum history validation.
- Background thread cleanup.

### Project Outcome

The module demonstrates automated encryption key lifecycle management, controlled key rotation, temporary backward decryption compatibility, and thread-safe operation.

This is an educational implementation and requires further security review before production deployment.

Week 3 — Member 1: Dynamic Key Rotation

Contribution Summary

As Member 1, I developed a Dynamic Key Rotation module for the Post-Quantum Zero-Trust Microsegmentation Mesh project.

The main objective was to implement secure encryption key lifecycle management with automatic and manual rotation capabilities.

Work Completed Over 7 Days

* Day 1: Implemented AES-256-GCM encryption and decryption with secure key generation.
* Day 2: Added key rotation history, thread synchronization, and automatic background rotation.
* Day 3: Implemented and tested manual key rotation and previous-key decryption support.
* Day 4: Verified automatic rotation, key retirement, and grace-period functionality.
* Day 5: Added configurable key history limits and input validation.
* Day 6: Improved automated testing and background thread cleanup.
* Day 7: Completed documentation and final project verification.

Technologies Used

* Python
* AES-256-GCM
* Cryptography library
* Threading and RLock
* Unittest
* GitHub

Final Outcome

Successfully developed a dynamic encryption key management module supporting manual rotation, automatic background rotation, grace-period handling, key retirement, rotation history, and thread-safe operations.

This contribution strengthens the key management component of the wider Zero-Trust architecture.

Role: Member 1 — Dynamic Key Rotation
Project: Post-Quantum Zero-Trust Microsegmentation Mesh
