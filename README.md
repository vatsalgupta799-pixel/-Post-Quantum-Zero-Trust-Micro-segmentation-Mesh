# -Post-Quantum-Zero-Trust-Micro-segmentation-Mesh

A hybrid post-quantum Zero-Trust security framework integrating ML-KEM, mTLS,
and Kubernetes microsegmentation to secure service-to-service communication
while evaluating performance and authentication overhead.

## Day 1 — Environment and Repository Setup

This repository is the Task 4 workspace for a college capstone project on a
Post-Quantum Zero-Trust Microsegmentation Mesh. The planned cryptographic
demonstration combines classical X25519 key exchange with the post-quantum
ML-KEM-768 key-encapsulation mechanism. Day 1 establishes a reproducible
Python environment and verifies library support; it does not implement the
hybrid protocol.

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

The actual key exchange, HKDF combiner, symmetric encryption, benchmarks,
certificates, Kubernetes, Envoy, OPA, Vault, and service-mesh integration are
future work.

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
channel and not a post-quantum implementation. ML-KEM-768, the hybrid
combiner, certificates, and service-mesh integration remain planned for later
milestones.

## Planned technology stack

- Python 3.13 for this development environment;
- `cryptography` for X25519 and ML-KEM-768 API support;
- HKDF for the future hybrid key-derivation step;
- pytest for the Day 2 automated tests;
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
│   ├── pqc_mlkem.py            # Future ML-KEM wrapper placeholder
│   ├── hybrid_exchange.py      # Future hybrid combiner placeholder
│   └── benchmark.py            # Future benchmark placeholder
├── tests/
│   ├── test_ecdh.py
│   ├── test_mlkem.py
│   └── test_hybrid.py
├── scripts/
│   ├── check_environment.py
│   └── demo_ecdh.py
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
Classical X25519 Key Exchange.** The X25519/HKDF baseline, demonstration, and
automated tests are complete on the verified machine.

Planned next steps:

1. Day 3: add ML-KEM-768 encapsulation/decapsulation tests.
2. Later: define the protocol transcript and HKDF-based hybrid combiner.
3. Later: add authenticated symmetric encryption, benchmarks, and integration
   boundaries for the wider zero-trust project.

## Limitations

This repository does not yet implement the X25519-plus-ML-KEM hybrid exchange,
post-quantum mTLS, Kubernetes policy, or service-mesh deployment. Day 2
establishes a classical shared secret and HKDF-derived session key only; it
does not authenticate services or provide post-quantum security.
`cryptography`'s low-level asymmetric APIs require careful protocol design,
validation, key lifecycle handling, and review before production use.

## Official references

- [NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final)
- [RFC 7748: Elliptic Curves for Security](https://www.rfc-editor.org/rfc/rfc7748)
- [cryptography X25519 documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/x25519/)
- [cryptography ML-KEM documentation](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/mlkem/)
- [Open Quantum Safe liboqs-python](https://github.com/open-quantum-safe/liboqs-python)
- [Open Quantum Safe liboqs](https://github.com/open-quantum-safe/liboqs)
