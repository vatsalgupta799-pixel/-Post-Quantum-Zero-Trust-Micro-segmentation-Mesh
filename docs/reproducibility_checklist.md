> **Current rectification update (28 October 2026):** See [the current audit](project_audit_week2.md) for superseding evidence. The OpenSSL timing includes process startup, TCP, TLS, verification, shutdown and parsing; it is not isolated handshake latency. Session reuse is now recorded as unknown and the analyzer rejects it until independent freshness evidence is available. A later local TLS smoke test succeeded; a matched comparison remains incomplete. Older smoke data is historical and cannot establish hostname verification or a defensible tail-latency comparison. Use new output directories and a fresh nonexistent pytest basetemp.

# Week 1 reproduction — 28 October 2026

In this Windows `main-checkout`, a new `.venv` was created with Python 3.13.12. The initial `python -m venv .venv` created the environment but failed during pip bootstrapping because the default temporary location was not writable. Without deleting the environment, setting `TEMP` and `TMP` to a workspace directory and running `.\.venv\Scripts\python.exe -m ensurepip --upgrade --default-pip` installed pip 25.3. Then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt --disable-pip-version-check` succeeded. All 40 direct requirements matched their constraints; `pip check` found no broken dependencies. This is a successful installation for this host and date, not a locked cross-platform environment: several direct and transitive dependencies are version ranges.

Verified versions: Python 3.13.12, pip 25.3, cryptography 50.0.2, pytest 8.4.2, Matplotlib 3.11.2, Python SSL OpenSSL 3.0.18. `scripts/check_environment.py` reported 5 passed, 0 failed, 0 blocked.

From the repository root, the following used the new environment:

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/week1-final-20261028-unique --tb=short
.\.venv\Scripts\python.exe scripts\demo_ecdh.py
.\.venv\Scripts\python.exe scripts\demo_mlkem.py
.\.venv\Scripts\python.exe scripts\demo_hybrid.py
.\.venv\Scripts\python.exe src\hybrid_key_exchange.py
```

The last command demonstrates AES-GCM locally. The pytest base directory shown was a new, nonexistent path: always select a fresh path, since pytest may remove an existing `--basetemp`. The final full suite passed **128 tests**, with 0 failures, skips, errors or reported warnings, in 1.08 seconds. All four demos completed successfully without printing secret bytes. The initial pre-change run passed 126 tests in 1.30 seconds. Details are in the current [audit](project_audit_week2.md). The setup and demos were run on Windows; other platforms were not tested. The following Day 7 record is preserved as historical evidence from a different workspace.

---

# Day 7 Reproducibility Checklist

This checklist records what was actually verified in the existing workspace on
2026-10-18. It is evidence for this Windows environment, not a guarantee that
all platforms, future dependency versions, or production deployments behave
the same way.

## Recorded environment

- Workspace: `G:\internship\hybrid-key-exchange`
- Operating system: Windows 11 (`Windows-11-10.0.26300-SP0` in the stored
  benchmark metadata)
- Terminal: PowerShell 7.6.5
- Python: 3.13.12 from the project `.venv`
- pip: 26.2.1
- `cryptography`: 50.0.2
- pytest: 8.4.2
- Matplotlib: 3.11.2

## Completed checks

- [x] Python version recorded: Python 3.13.12.
- [x] Dependency versions recorded: `cryptography` 50.0.2, pytest 8.4.2, and
  Matplotlib 3.11.2.
- [x] Existing virtual environment reused: `.venv` was intact and selected by
  the environment checker.
- [x] Environment check executed: 5 passed, 0 failed, 0 blocked.
- [x] Classical demonstration executed successfully:
  `scripts/demo_ecdh.py` verified matching X25519/HKDF keys with a 32-byte
  session-key length.
- [x] ML-KEM demonstration executed successfully:
  `scripts/demo_mlkem.py` verified ML-KEM-768 encapsulation and decapsulation
  with a 32-byte shared-secret length.
- [x] Hybrid demonstration executed successfully:
  `scripts/demo_hybrid.py` verified X25519, ML-KEM-768, both simulated
  services, matching session keys, and a 32-byte session-key length.
- [x] Automated tests executed: `python -m pytest -v` collected and passed 48
  tests with no failures or skips.
- [x] Benchmark settings recorded: the checked-in run used 20 warm-up and 500
  measured iterations per operation; its metadata is in
  `results/benchmark_environment.json`.
- [x] Raw benchmark results preserved: the checked-in
  `results/benchmark_results.csv` retains 6,000 raw samples across 12
  operations, with 500 samples per operation.
- [x] A fresh benchmark validation was run without overwriting stored results:
  20 warm-up and 500 measured iterations produced 6,000 samples in
  `.tmp/day7-benchmark-run`.
- [x] Charts were regenerated from genuine fresh measurements into
  `.tmp/day7-benchmark-charts`.
- [x] README commands were checked on Windows using the project interpreter;
  the environment check, three demonstrations, test suite, benchmark runner,
  and chart generator all completed successfully.
- [x] The implemented Mermaid diagrams in `docs/architecture.md` were checked
  against the actual local X25519, ML-KEM-768, and hybrid source flow. The
  separate proposed deployment diagram remains explicitly labelled as planned.
- [x] Normal demo output and integration result objects were checked not to
  expose private keys, component shared secrets, transcripts, or final session
  keys; dedicated sanitization tests passed.
- [x] Known limitations are documented in `docs/security_limitations.md`.
- [x] Git status was reviewed before Day 7 edits and again after final
  verification; no pre-existing user changes were overwritten.

## Commands executed

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe scripts\demo_ecdh.py
.\.venv\Scripts\python.exe scripts\demo_mlkem.py
.\.venv\Scripts\python.exe scripts\demo_hybrid.py
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe scripts\benchmark.py --warmup 20 --iterations 500 --output-dir .tmp\day7-benchmark-run --report-path .tmp\day7-benchmark-report.md
.\.venv\Scripts\python.exe scripts\plot_benchmarks.py --summary-path .tmp\day7-benchmark-run\benchmark_summary.csv --output-dir .tmp\day7-benchmark-charts
```

## Not executed in this workspace

- [ ] A brand-new virtual environment was not created for Day 7. The existing
  `.venv` was intentionally preserved; clean-install commands are documented
  in `README.md` but were not executed.
- [ ] Linux, Ubuntu, and macOS commands were documented but not executed on
  this Windows host.
- [ ] No Kubernetes cluster, OPA deployment, Vault deployment, Envoy proxy,
  TLS/mTLS handshake, or networked service integration was run by Task 4.
- [ ] No independent cryptographic audit, formal protocol proof, production
  load test, or side-channel assessment was performed.

## Reproduction path for another developer

1. Clone the repository and open its root.
2. Follow the platform-specific setup section in `README.md` to create or
   reuse `.venv` and install `requirements.txt`.
3. Run the first five commands above through that environment.
4. Read the preserved data under `results/` and `docs/benchmark_report.md`.
5. Use the final two commands with a new ignored output directory to collect a
   fresh benchmark run without replacing the checked-in reference artifacts.

If any of these steps fails, record the exact platform, Python version,
dependency versions, command, and sanitized error message rather than treating
the result as verified.
