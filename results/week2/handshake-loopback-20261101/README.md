# Exploratory TLS handshake timing — 1 November 2026

This is a local OpenSSL loopback study, **not an Envoy, mTLS, OPA, or
Kubernetes benchmark**. It uses a new experimental instrumented client; it
does not replace the earlier process-inclusive measurements. The team Envoy
endpoint's current address and trust certificate were not available for this
run.

## Setup and method

- Windows 11 build 26300, Python 3.13.12; OpenSSL client library and server
  executable 4.1.0. CPU and memory information were unavailable through CIM.
- Same local OpenSSL `s_server` for both modes, listening on 127.0.0.1:19612,
  TLS 1.3, group list `X25519:X25519MLKEM768`, `-www`, same temporary
  self-signed localhost certificate trusted explicitly by the client. Neither
  client-certificate authentication nor OPA was configured. No application
  request was sent. The temporary server private key was removed afterward.
- One connection at a time. Four blocks ran hybrid / classical / classical /
  hybrid, each with five excluded warm-ups and 25 measured attempts. Each
  attempt used a fresh TLS context and TCP socket. All 100 measured attempts
  and all 20 warm-ups succeeded; every measurement records the expected group,
  TLS 1.3, successful certificate/hostname validation and no session reuse.
- The timer uses `perf_counter_ns` around the nonblocking `SSL_connect` loop,
  after the TCP connection succeeds and until OpenSSL reports handshake
  completion. It includes TLS certificate validation and Python scheduling and
  select-loop overhead; it excludes TCP setup, context creation, application
  processing, client process startup and shutdown. It is not pure cryptographic
  computation time.
- Percentiles use linear interpolation at `(n - 1) * p`; standard deviation is
  the sample standard deviation. No observations were discarded.

The probe was checked separately against a local server: both groups succeeded;
wrong-hostname, unrelated-CA and hybrid-against-X25519-only cases each failed.
These local controls do not validate the team's Envoy deployment.

## Results

| Handshake duration | X25519 | X25519MLKEM768 | Hybrid minus classical |
| --- | ---: | ---: | ---: |
| Attempts / success | 50 / 50 | 50 / 50 | Both 100% |
| p50 | 2.7861 ms | 5.4833 ms | +2.6973 ms (+96.81%) |
| p95 | 6.5447 ms | 7.5894 ms | +1.0448 ms (+15.96%) |
| p99 | 6.8324 ms | 7.9855 ms | +1.1532 ms (+16.88%) |
| Mean | 3.6724 ms | 4.9627 ms | +1.2903 ms (+35.13%) |
| Sample standard deviation | 1.6127 ms | 1.9922 ms | — |
| Minimum | 1.9642 ms | 2.4030 ms | — |
| Maximum | 6.8446 ms | 8.0558 ms | — |

These are descriptive results from one short local run, not a general estimate
of post-quantum overhead. The two processes share hardware, order effects and
CPU scheduling remain possible, and p95/p99 estimates from 50 observations are
especially unstable. No packet sizes, retransmissions, CPU utilization, remote
networking, resumed sessions or concurrency were measured. Repeat independent
runs with more observations and reversed/randomized blocks before drawing
conclusions. Preserve and report failures, not just successful attempts.

Raw observations are in [raw.csv](raw.csv), statistics in [summary.json](summary.json),
setup and warm-up observations in [metadata.json](metadata.json), and the
exploratory figure in [handshake_comparison.png](handshake_comparison.png).

## Reproduction

Start an authorized test server with a DNS name covered by its certificate.
Use a copy of its public CA or self-signed test certificate for `--ca-file`.
The probe currently requires Windows, OpenSSL 4, a DNS server name and no
client-certificate authentication. Run from the project root with a new output
directory, replacing the placeholders:

```powershell
python scripts/benchmark_handshake_probe.py --host HOST --port PORT `
  --server-name CERTIFICATE_DNS_NAME --ca-file PATH_TO_PUBLIC_CERT `
  --dll 'C:\Program Files\OpenSSL-Win64\bin\libssl-4-x64.dll' `
  --per-block 25 --warmup 5 --timeout 5 --output-dir results/week2/NEW_RUN
```

The script writes individual attempts and a summary; the figure in this
directory was produced separately from the raw CSV. Do not use the older
process-duration analyzer on this different timing schema. Stop if validation
fails; do not disable certificate verification. Coordinate load and test
endpoint access with the service owner.
