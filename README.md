# -Post-Quantum-Zero-Trust-Micro-segmentation-Mesh

A hybrid post-quantum Zero-Trust security framework integrating ML-KEM, mTLS,
and Kubernetes microsegmentation to secure service-to-service communication
while evaluating performance and authentication overhead.

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

Symmetric encryption, benchmarks, certificates, Envoy, OPA, Vault, and
service-mesh integration are future work. The independent and hybrid
key-establishment components are documented below.

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
or claim complete post-quantum security. Day 5 will measure the independently
callable classical, ML-KEM, hybrid, and HKDF operations without adding network
latency to the benchmark.

## Planned technology stack

- Python 3.13 for this development environment;
- `cryptography` for X25519 and ML-KEM-768 API support;
- HKDF for the future hybrid key-derivation step;
- pytest for the Day 2, Day 3, and Day 4 automated tests;
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
│   └── benchmark.py            # Future benchmark placeholder
├── tests/
│   ├── test_ecdh.py
│   ├── test_mlkem.py            # Day 3 ML-KEM-768 tests
│   └── test_hybrid.py           # Day 4 hybrid exchange tests
├── scripts/
│   ├── check_environment.py
│   ├── demo_ecdh.py
│   ├── demo_mlkem.py            # Day 3 ML-KEM-768 demonstration
│   └── demo_hybrid.py           # Day 4 hybrid demonstration
├── docs/
│   └── architecture.md
├── results/
│   └── .gitkeep
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
X25519 + ML-KEM-768 Key Establishment.** The independent and hybrid
demonstrations and automated tests are complete on the verified machine.

Planned next steps:

1. Day 5: benchmark classical, post-quantum, hybrid, and HKDF operations.
2. Later: add authenticated symmetric encryption and integration
   boundaries for the wider zero-trust project.

## Limitations

This repository does not implement post-quantum mTLS, certificate
authentication, symmetric encryption, or service-mesh deployment. The Day 4
hybrid flow establishes a matching session key in a local simulation, but it
does not authenticate services or provide a complete secure channel.
`cryptography`'s low-level asymmetric APIs require careful protocol design,
validation, key lifecycle handling, and review before production use.

## Official references

- [NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final)
- [RFC 7748: Elliptic Curves for Security](https://www.rfc-editor.org/rfc/rfc7748)
- [cryptography X25519 documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/x25519/)
- [cryptography ML-KEM documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/mlkem/)
- [Open Quantum Safe liboqs-python](https://github.com/open-quantum-safe/liboqs-python)
- [Open Quantum Safe liboqs](https://github.com/open-quantum-safe/liboqs)
