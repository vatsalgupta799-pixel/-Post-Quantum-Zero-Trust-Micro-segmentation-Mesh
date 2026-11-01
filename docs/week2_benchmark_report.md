# Envoy repeat and review handover — 1 November 2026

The classical-first repeat recorded 100/100 successful new handshakes per
mode. p50/p95/p99 were 192.6289/394.6559/618.2272 ms classical and
272.8049/425.5683/590.8987 ms hybrid. The first run began with hybrid; results
are kept separate. The p95 direction changed between runs, and the relay and
network/scheduling effects prevent a pure cryptographic-overhead conclusion.
See the [review handover](week2_review_handover.md) and
[repeat data and chart](../results/week2/envoy-tailscale-reverse-20261101/README.md).

---

# Envoy handshake timing update — 1 November 2026

The team's Envoy endpoint was reached over Tailscale and negotiated TLS 1.3
with the expected X25519 and X25519MLKEM768 groups, validating the explicitly
trusted localhost test certificate. An instrumented client recorded 100 new,
successful handshakes per group. p50/p95/p99 were 195.1531/373.7393/1139.7523
ms classical and 239.5754/327.7337/555.8999 ms hybrid. Tailscale reported a
relay before and after the test, and network and scheduling variability are
included. This one exploratory run does not isolate cryptographic overhead or
establish reliable tail-latency differences. See [full results, method,
limitations, raw data and charts](../results/week2/envoy-tailscale-20261101/README.md).

---

# Local handshake timing update — 1 November 2026

**Envoy preflight:** With the newly supplied public test certificate, both
X25519 and X25519MLKEM768 checks against the documented `192.168.162.128:8444`
timed out before a TLS connection was verified. [Attempt records](../evidence/envoy-attempt-20261101/README.md)
are preserved. No Envoy performance run was performed. Confirm the current
address, listening interface and a network path from Windows before retrying.

An experimental instrumented OpenSSL client measured the interval from the
first `SSL_connect` call until successful TLS handshake completion, after TCP
connection. The local OpenSSL 4.1.0 loopback study recorded 1,000 verified new
sessions per group with no failures. X25519 p50/p95/p99 were 2.9586/6.6341/
8.0773 ms; X25519MLKEM768 values were 5.3504/7.9067/9.0761 ms. This is one
local run and **not an Envoy benchmark**. See [method, controls, raw data,
limits and charts](../results/week2/handshake-loopback-full-20261101/README.md).
It does not supersede the earlier process-duration results, which measured a
different interval. The team endpoint and trusted public certificate are
still needed to run the instrument against Envoy; client-certificate mTLS is
not supported by this experimental probe.

---

# Current environment check — 31 October 2026

**Later recheck:** Both locally hosted OpenSSL groups subsequently passed
certificate- and hostname-validated TLS 1.3 verification when local network
access was permitted. See [the recheck evidence](../evidence/week2-recheck-20261031/README.md).
This supersedes the connectivity failure below for the local OpenSSL test only;
it does not establish availability of Envoy or an isolated handshake timing.
The earlier 10-per-mode beginner smoke data has also been analyzed separately:
[report and charts](../results/week2/beginner-smoke-comparison-20261031/comparison_report.md).
All 20 measured samples were successful, but only 10 per mode and the
process-inclusive timer make the comparison exploratory, not a handshake
performance conclusion. No historical data was overwritten.

**Status: PARTIALLY COMPLETE — MEASUREMENTS OR VERIFICATION BLOCKED.** The
existing harness and the 28 October local results below were preserved. No new
TLS comparison was collected in this session. The historical results are
process-duration measurements, not isolated handshake latencies.

The current Windows 11 environment has Python 3.13.12, Python SSL OpenSSL
3.0.18, cryptography 50.0.2, pytest 9.1.1 and an OpenSSL 4.1.0 executable at
`C:\Program Files\OpenSSL-Win64\bin\openssl.exe`. Its advertised TLS groups
include X25519 and X25519MLKEM768; advertising support alone is not evidence of
negotiation. Envoy and Docker were not found on PATH, no team endpoint was
provided, and no project `.venv` is present. Pytest 9.1.1 is outside the
declared pytest version range, although the local suite passed. This directory
is not a Git working tree, so Git status and commit identity could not be
established.

An isolated OpenSSL test server started on `127.0.0.1:19591` with a temporary
localhost certificate. Both verifier attempts failed before reporting a TLS
version or group. A separate diagnostic on port 19592 showed the server
process running but OpenSSL's TCP `BIO_connect` failed; the underlying cause
was not established. The verifier outcomes are preserved in
`.tmp/person4-live-20261031/`; the temporary private key was removed. These
attempts establish neither a TLS handshake nor a meaningful group or
certificate negative test. The historical positive evidence below remains
separate from this session's failure.

Baseline command: `python -m pytest -q -p no:cacheprovider --basetemp
.tmp/pytest-20261031-person4-a --tb=short`: **140 passed in 2.28 s**. An initial
run with the default temporary directory had 127 passes and 13 setup errors
because pytest could not create its temporary directory. The environment check
passed Python, cryptography, X25519 and ML-KEM checks, and failed its virtual
environment check; `python -m pip check` found no broken installed
requirements.

The next measurement requires a working authorized loopback or team endpoint,
trusted certificate, and a client that reports the actual group and session
state. Re-run positive and negative controls, then use an instrumented client
with a validated handshake-completion timing boundary before drawing a
handshake-performance conclusion. Coordinate Envoy build and group telemetry,
OPA settings, endpoint and certificates, and any capture with the responsible
team members. Do not combine this failed run with the preserved 28 October
measurements.

---

# Local TLS process-duration comparison — 28 October 2026

A local OpenSSL 4.1.0 server and client negotiated TLS 1.3 with a trusted localhost certificate and the exact X25519 or X25519MLKEM768 group. A separate ticket-save/reuse control demonstrated OpenSSL `New` and `Reused` statuses for both groups. The benchmark retained only sanitized status lines and recorded 100 new, verified measured connections per mode, 0 failures; warm-ups and preflights are retained separately.

| Process duration | X25519 | X25519MLKEM768 | Hybrid minus classical |
| --- | ---: | ---: | ---: |
| p50 | 1035.6246 ms | 1035.1042 ms | -0.5204 ms (-0.0502%) |
| p95 | 1050.6977 ms | 1039.8693 ms | -10.8284 ms (-1.0306%) |
| p99 | 1055.2880 ms | 1043.5635 ms | -11.7245 ms (-1.1110%) |
| mean | 1037.4300 ms | 1035.6891 ms | -1.7409 ms (-0.1678%) |
| sample standard deviation | 5.6855 ms | 2.4090 ms | — |

The timer spans OpenSSL process startup, TCP, TLS, certificate verification, output capture, shutdown and parsing. The roughly one-second process delay dominates, so these numbers do not isolate handshake latency or establish which group has lower handshake overhead. Blocks ran hybrid/classical/classical/hybrid, reducing but not eliminating order and drift effects. There were 100 rather than 1,000 attempts per mode because each attempt took about one second; a 1,000-per-mode run would take about 35 minutes. Tail estimates are exploratory. No Envoy, mTLS, authorization or production network measurement is claimed.

Raw data, block metadata, checked summary and accurately labelled plots are in [the paired experiment](../results/week2/local-openssl41-paired-20261028/README.md); the [session controls](../evidence/week2-session-control-20261028/README.md) and [final generated report](../results/week2/local-openssl41-paired-20261028/comparison-final/comparison_report.md) provide supporting evidence.

---

## Earlier report — historical and superseded where inconsistent

> **Week 2 update (28 October 2026):** Local OpenSSL positive and negative TLS checks succeeded; session freshness and a matched comparison remain unverified. Process-inclusive timings are not handshake latency. See the [current audit](project_audit_week2.md).

> **Current rectification update (28 October 2026):** See [the current audit](project_audit_week2.md) for superseding evidence. The OpenSSL timing includes process startup, TCP, TLS, verification, shutdown and parsing; it is not isolated handshake latency. Session reuse is now recorded as unknown and the analyzer rejects it until independent freshness evidence is available. Local TLS positive and negative checks succeeded; a matched comparison remains blocked by session evidence. Older smoke data is historical and cannot establish hostname verification or a defensible tail-latency comparison. Use new output directories and a fresh nonexistent pytest basetemp.

# Week 2 TLS Handshake Benchmark Report

## Status

**PARTIALLY COMPLETE — LOCAL HYBRID TLS VERIFIED; FULL BENCHMARK PENDING**

Review on 28 October 2026: the stored smoke runs verified the certificate
chain but the client did not check the server name. The harness now checks
both the chain and hostname (or IP address), requires an exact group match,
and rejects a nonzero client exit. These changes have passed unit tests but
could not be revalidated against a live server here: the loopback connection
attempt failed before TLS negotiation. No new handshake results were created.
The previous smoke runs are historical capability evidence, not proof that
the strengthened verification works end to end.

The stored 1,000-sample classical data set is a useful configuration-restricted
TLS baseline, but it lacks direct negotiated-group telemetry and is not a
verified comparison input. Python's OpenSSL 3.0.18 backend still cannot
configure the hybrid group, but an installed OpenSSL 4.1.0 CLI can. The
current harness uses that CLI for direct per-sample group and certificate
verification rather than silently falling back to a classical group.

## A. Executive Summary

This report compares TLS 1.3 connection-establishment latency between
classical X25519 and hybrid X25519MLKEM768 key exchange. The historical
classical baseline is retained but not directly verified. A new local
OpenSSL 4.1.0 smoke test verifies that both TLS named groups can be measured.

**Stored classical configuration baseline (X25519):** 1,000 fresh TLS 1.3
connections over localhost, 100% success rate. Median (p50) latency:
15.36 ms. The p95 latency is 22.05 ms and the p99 is 28.32 ms. These values
are not a verified classical-versus-hybrid comparison because the group was
not directly observed.

**Verified local smoke test:** OpenSSL 4.1.0 was used for both a loopback TLS
server and a fresh `openssl s_client` process per connection. All three
classical samples directly reported `X25519`; all three hybrid samples
directly reported `X25519MLKEM768`; TLS 1.3 and certificate verification
succeeded on every attempt. The smoke-only comparison observed p50 values of
1042.3057 ms (classical) and 1066.1231 ms (hybrid), a 23.8174 ms / 2.29%
difference. This is not a performance conclusion: the sample size is three
and timing includes OpenSSL process start-up. Raw data, metadata, verification
outputs, and charts are preserved in `results/week2/openssl41-local-smoke/`.

## B. Experimental Setup

### Hardware and Software

| Item | Value |
| --- | --- |
| OS | Windows 11 |
| CPU | Intel64 Family 6 Model 165 Stepping 2, GenuineIntel |
| Architecture | AMD64 |
| Python | 3.13.12 (MSC v.1944 64 bit) |
| OpenSSL backend | OpenSSL 3.0.18 30 Sep 2025 |
| cryptography | 50.0.2 |
| OpenSSL CLI used for verified smoke test | OpenSSL 4.1.0 (23 Oct 2026) |
| Envoy binary | Not available |
| Docker | Not available |

### Test Configuration

| Parameter | Classical | Hybrid |
| --- | --- | --- |
| TLS version | TLS 1.3 | TLS 1.3 |
| Expected group | X25519 | X25519MLKEM768 |
| Server | Python ssl (localhost:18443) | Blocked |
| Certificate | Self-signed ECDSA P-256 | N/A |
| Certificate validation | Enabled | N/A |
| mTLS | No | N/A |
| Warm-up connections | 100 | N/A |
| Measured connections | 1,000 | N/A |
| Connection reuse | None (fresh TCP+TLS per sample) | N/A |
| Timeout | 10 s | N/A |
| Concurrency | 1 (serial) | N/A |
| Network path | Loopback (127.0.0.1) | N/A |
| Same machine (client/server) | Yes | N/A |

### Timing Boundary

For the historical Python baseline, connection-establishment latency was measured from immediately before
`socket.create_connection()` to immediately after `ctx.wrap_socket()`
completes using `time.perf_counter_ns()`. This includes TCP setup and the
full TLS 1.3 handshake but not application data. The same boundary would be
used for both modes. The later OpenSSL smoke runs instead timed process startup,
TCP, TLS verification, and process exit; the two timing methods cannot be
compared.

## C. Negotiation Verification

### Classical — X25519

The Python ssl context was restricted to X25519 only via
`ctx.set_ecdh_curve('X25519')`; all 1,000 connections completed with
`tls_sock.version()` returning `'TLSv1.3'` and cipher suite
`TLS_AES_256_GCM_SHA384`.

**Limitation:** Python's `ssl.SSLSocket` does not expose a negotiated-group
API. This is configuration evidence, not a direct report of the group selected
by the server. The historical data remains preserved, but it must not be
presented as verified named-group evidence.

### Hybrid — Python Backend Limitation and OpenSSL 4.1 Verification

**Python backend cannot verify hybrid.** `ctx.set_ecdh_curve('X25519MLKEM768')` raises
`ssl.SSLError: unknown elliptic curve name 'X25519MLKEM768'`. The
benchmark harness detects this during prerequisite checks and refuses to
start, exiting with code 1.

Historical evidence in `evidence/envoy-pqc-build-verification.txt` confirms
that an Envoy 1.41.0-dev build with BoringSSL successfully negotiated
X25519MLKEM768 on a different machine. That binary and configuration are not
available here.

The local OpenSSL 4.1.0 smoke test now provides current, direct evidence:
`openssl s_client` reported `Protocol version: TLSv1.3`, `Verification: OK`,
and `Negotiated TLS1.3 group: X25519MLKEM768` for the hybrid server. The
matching classical server reported `Peer Temp Key: X25519, 253 bits`.

## D. Results

### Classical TLS (X25519) — 1,000-Sample Configuration Baseline

| Metric | Value |
| --- | --- |
| Total attempts | 1,000 |
| Successful handshakes | 1,000 |
| Failed handshakes | 0 |
| Success rate | 100.0% |
| p50 latency (ms) | 15.3588 |
| p95 latency (ms) | 22.0534 |
| p99 latency (ms) | 28.3162 |
| Mean latency (ms) | 12.5092 |
| Standard deviation (ms) | 7.3165 |
| Minimum latency (ms) | 1.0869 |
| Maximum latency (ms) | 33.0668 |

### Prior Python-Backend Hybrid Attempt — Blocked

| Metric | Value |
| --- | --- |
| Total attempts | Unavailable |
| Successful handshakes | Unavailable |
| Failed handshakes | Unavailable |
| Success rate | Unavailable |
| All latency percentiles | Unavailable |

### OpenSSL 4.1 Local Smoke Test — Directly Verified, 3 Samples per Mode

| Metric | Classical X25519 | Hybrid X25519MLKEM768 |
| --- | ---: | ---: |
| Successful / attempted | 3 / 3 | 3 / 3 |
| TLS version | TLSv1.3 | TLSv1.3 |
| Certificate verification | 3 / 3 | 3 / 3 |
| p50 connection-establishment (ms) | 1042.3057 | 1066.1231 |
| p95 connection-establishment (ms) | 1054.0361 | 1088.6357 |
| p99 connection-establishment (ms) | 1055.0788 | 1090.6368 |

The client used a new OpenSSL process and `-no_ticket` for every sample. The
values include process start-up, TCP setup, handshake, and verification. They
are capability evidence only; use matched 100+ (preferably 1,000) sample runs
on the team endpoint before reporting any overhead conclusion.

## E. Comparative Analysis

The three-sample smoke comparison is shown above; it is too small and
process-dominated to support a performance conclusion. No controlled full
comparison has been obtained.
The planned comparison metrics are:

- Absolute difference in p50, p95, and p99 latency (ms)
- Relative overhead (%) = ((hybrid − classical) / classical) × 100
- Success-rate difference

The analysis script (`scripts/analyze_tls_results.py`) is ready to process
both CSV files when hybrid data becomes available.

## F. Network and Payload Analysis

No packet capture was performed. No handshake-size measurements are
available. Theoretical key-share sizes from the protocol specifications:

| Component | X25519 | X25519MLKEM768 |
| --- | --- | --- |
| Client key share | 32 bytes | 32 + 1,184 = 1,216 bytes |
| Server key share | 32 bytes | 32 + 1,088 = 1,120 bytes |

These are protocol sizes, **not observed network traffic**. Actual TLS
handshake messages include headers, extensions, certificates, and other
fields that are not captured here.

## G. Limitations

1. **Python SSL remains unsupported.** The interpreter's OpenSSL 3.0.18 does
   not support X25519MLKEM768. The verified smoke run uses an external
   OpenSSL 4.1.0 executable instead.
2. **Loopback network.** All measurements use 127.0.0.1, eliminating real
   network latency, jitter, and packet loss.
3. **Classical group is unverified.** Python did not expose direct named-group
   telemetry and the run predates the strict per-sample OpenSSL verification
   mode.
4. **Strict-run timing scope differs.** New verified runs measure
   connection-establishment through a new `openssl s_client` process, including
   client startup and TCP setup; historical Python timings are not comparable.
5. **Self-signed certificate.** The test certificate has no CA chain
   traversal, reducing TLS processing compared to production.
6. **Serial single-threaded.** No concurrency experiment was run.
7. **No TLS session resumption test.** All connections are full handshakes.
8. **CPU contention.** Client and server share the same machine and CPU.
9. **No Envoy, Kubernetes, or production endpoint.**

## H. Reproduction Instructions

### Run the classical benchmark

```powershell
# Terminal 1: Start the local TLS server
python scripts/local_tls_server.py --port 18443 --group X25519 --max-connections 1200

# Terminal 2: Run the benchmark
$openssl = "C:\path\to\compatible-openssl.exe"
python scripts/benchmark_tls.py --mode classical --host 127.0.0.1 --port 18443 --server-name localhost --ca-file .tmp/tls-test/cert.pem --openssl-path $openssl --warmup 100 --iterations 1000 --timeout 10 --output-dir results/week2/classical-verified
```

### Attempt the hybrid benchmark (will fail on OpenSSL 3.0.x)

```powershell
python scripts/benchmark_tls.py --mode hybrid --host HOST --port 8443 --server-name HOST --ca-file /path/to/ca.pem --openssl-path $openssl --warmup 100 --iterations 1000 --timeout 10 --output-dir results/week2/hybrid-verified
```

### Analyze both results (blocked pending independent session telemetry)

```powershell
python scripts/analyze_tls_results.py --classical-csv results/week2/classical-verified/raw.csv --hybrid-csv results/week2/hybrid-verified/raw.csv --output-dir results/week2/comparison-new
```

### Run the tests

```powershell
python -m pytest tests/test_tls_benchmark.py -v
```

## I. Conclusion

The stored classical TLS 1.3 baseline has 1,000 fresh-connection samples over
loopback, p50 15.36 ms, and a 100% success rate. It is not direct proof of
the negotiated X25519 group and must not be compared with a future verified
hybrid run.

The hybrid experiment can now run through the external OpenSSL 4.1.0 CLI,
which directly verified X25519MLKEM768 in the local smoke test. Python's own
OpenSSL 3.0.18 backend remains unsuitable for the hybrid group.

**What this experiment establishes:**
- A preserved configuration-restricted TLS 1.3 baseline on this hardware and
  software configuration.
- A fail-closed harness that requires OpenSSL-reported TLS 1.3, certificate,
  and named-group evidence for every new sample.
- A local, directly verified X25519MLKEM768 capability smoke test.

**What it does not establish:**
- Any comparison between classical and hybrid TLS performance.
- Network-realistic latency (loopback only).
- The performance of Envoy, BoringSSL, Kubernetes, or production
  infrastructure.

The correct status remains:
**PARTIALLY COMPLETE — LOCAL HYBRID TLS VERIFIED; FULL BENCHMARK PENDING**.
