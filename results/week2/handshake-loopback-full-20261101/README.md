# OpenSSL loopback TLS handshake study — 1 November 2026

This is a **local OpenSSL study, not an Envoy benchmark**. It compares
certificate-validated TLS 1.3 handshakes using X25519 and X25519MLKEM768 on
one Windows machine. Both runs used the same server and certificate.

## Method and setup

- Windows 11 build 26300; Python 3.13.12; OpenSSL 4.1.0 client library and
  server executable. CPU and memory details were unavailable through CIM.
- Local server: `openssl s_server -accept 19613 -cert <test-cert> -key
  <test-key> -tls1_3 -groups X25519:X25519MLKEM768 -www`, on IPv4 loopback.
  The same temporary self-signed localhost certificate was explicitly trusted
  by the client. Its public portion is saved as [server-cert.pem](server-cert.pem);
  its private key was removed. No client certificate or OPA was configured.
- Four consecutive blocks in hybrid/classical/classical/hybrid order; 25
  excluded warm-ups and 500 measured attempts per block, one at a time. Each
  connection uses a new TCP socket and TLS context. Both groups recorded
  1,000/1,000 successful new sessions with hostname/certificate, TLS version,
  and exact negotiated-group validation. All 100 warm-ups also succeeded.
- `perf_counter_ns` measures from immediately before the first `SSL_connect`
  call to successful completion, after TCP connects. TLS and certificate
  validation, Python polling and scheduling are included; TCP setup, context
  creation, application processing, process startup and shutdown are excluded.
  No application request was sent. This is handshake duration on this host,
  not pure cryptographic computation time.
- p50/p95/p99 use linear interpolation at `(n-1)*p`; the standard deviation
  is the sample standard deviation. No outlier filtering was applied.

Local validation controls performed separately: both group-restricted clients
completed a trusted handshake; an incorrect hostname, an unrelated trust
certificate, and a hybrid client against an X25519-only server each failed.
These controls do not validate an Envoy server or mTLS.

## Results

| Metric | X25519 | X25519MLKEM768 | Hybrid minus classical |
| --- | ---: | ---: | ---: |
| Attempts / success | 1000 / 1000 | 1000 / 1000 | Both 100% |
| p50 | 2.9586 ms | 5.3504 ms | +2.3918 ms (+80.84%) |
| p95 | 6.6341 ms | 7.9067 ms | +1.2726 ms (+19.18%) |
| p99 | 8.0773 ms | 9.0761 ms | +0.9989 ms (+12.37%) |
| Mean | 3.6198 ms | 5.2794 ms | +1.6596 ms (+45.85%) |
| Sample standard deviation | 1.7801 ms | 2.1833 ms | — |
| Minimum | 1.4838 ms | 1.9441 ms | — |
| Maximum | 8.7727 ms | 10.5479 ms | — |

This single local run observed longer handshake times for the hybrid group; it
does not establish an Envoy or production-network overhead. Client and server
share CPU resources, timing includes scheduling, blocks are not randomized,
and independent repeated runs are needed to assess variability. No handshake
bytes, packet counts, CPU usage, resumed sessions or concurrency were measured.

[Raw CSV](raw.csv), [metadata and warm-ups](metadata.json), [summary](summary.json),
[rechecked report](report/report.md), and [chart](report/handshake_comparison.png)
are preserved. The recheck validated all 2,000 rows and recalculated the
statistics from raw observations. The earlier 50-per-mode study is separately
preserved in `../handshake-loopback-20261101/`.

## Reproduction

Using an authorized compatible server and a public trust certificate that
matches the DNS server name, run from the project root with a **new** output
directory. This experimental client currently requires Windows, OpenSSL 4,
and a DNS server name; it does not support client certificates.

```powershell
python scripts/benchmark_handshake_probe.py --host HOST --port PORT `
  --server-name CERTIFICATE_DNS_NAME --ca-file PATH_TO_PUBLIC_CERT `
  --dll 'C:\Program Files\OpenSSL-Win64\bin\libssl-4-x64.dll' `
  --per-block 500 --warmup 25 --timeout 5 --output-dir results/week2/NEW_RUN
python scripts/report_handshake_probe.py results/week2/NEW_RUN
```

Record the exact server build, configuration, authentication mode, network
path and consent for the target separately. A group or certificate failure
stops the run; no fallback or retries are used. The runner flushes failed
measured attempts to the raw CSV and marks incomplete runs in metadata.
