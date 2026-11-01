# Envoy TLS 1.3 handshake study over Tailscale — 1 November 2026

This is a real, certificate-validated comparison against the team's Envoy test
endpoint. It is a single exploratory run over a relayed private network, not a
controlled estimate of cryptographic cost or production service-mesh behavior.

## Setup and verification

- Windows 11 client, Python 3.13.12, OpenSSL 4.1.0 client library; team-reported
  Kali Envoy endpoint `100.71.117.30:8444`. A historical build record reports
  Envoy 1.41.0-dev with BoringSSL; the version and exact running configuration
  were not independently queried during this measurement.
- The self-signed RSA test certificate from
  `examples/envoy-tls-test/envoy-test-cert.pem` was explicitly trusted; the
  expected DNS identity was `localhost`. Its SHA-256 fingerprint was
  `3E:FD:77:27:A6:F0:23:DE:98:70:AE:FB:18:94:7A:64:D7:12:1D:3B:24:05:C8:7C:22:4B:6F:42:FB:29:31:89`.
  A server-authenticated TLS test was used; the client sent no client
  certificate. This is not a test of mTLS, certificate rotation, or a
  CA-issued/PQC certificate.
- OpenSSL `s_client` preflight verified TLS 1.3, the expected exact group,
  certificate and hostname, and new-session status for both
  [classical](../../../evidence/envoy-tailscale-20261101/classical.json) and
  [hybrid](../../../evidence/envoy-tailscale-20261101/hybrid.json) connections.
  The in-process client independently checked those properties per observation.
- Tailscale ping reported DERP relay `blr` before and after the run; continuous
  path telemetry was not recorded. Client/server locations, link congestion,
  packet retransmissions and CPU usage were not measured. The team's standalone
  example does not configure OPA, but the exact live Envoy configuration was
  not independently captured, so its authorization settings remain unverified.
- Four sequential blocks: hybrid, classical, classical, hybrid. Each block had
  five excluded warm-ups and 50 measured connections, one at a time. The run
  recorded 100 successful observations per group and 20 successful warm-ups;
  each used a fresh TLS context and TCP connection. No failures or retries were
  recorded. 100 per group was chosen to limit traffic and elapsed time over the
  relay. In particular, p99 is exploratory with this sample size.
- `perf_counter_ns` measures from immediately before the first nonblocking
  `SSL_connect` call to successful completion, after TCP connects. It includes
  network round trips, certificate validation and client polling/scheduling;
  TCP establishment, client startup, and application requests are excluded.
  The 15-second timeout applies to the TCP and handshake phases separately.
- Percentiles use linear interpolation at `(n-1)*p`, standard deviation is
  sample standard deviation, and all successful values were retained. Raw rows
  were validated and means, deviations and percentiles independently recalculated.

## Results

| Handshake duration | X25519 | X25519MLKEM768 | Hybrid minus classical |
| --- | ---: | ---: | ---: |
| Attempts / success | 100 / 100 | 100 / 100 | Both 100% |
| p50 | 195.1531 ms | 239.5754 ms | +44.4223 ms (+22.76%) |
| p95 | 373.7393 ms | 327.7337 ms | -46.0056 ms (-12.31%) |
| p99 | 1139.7523 ms | 555.8999 ms | -583.8525 ms (-51.23%) |
| Mean | 226.7296 ms | 245.5834 ms | +18.8538 ms (+8.32%) |
| Sample standard deviation | 170.2911 ms | 68.1060 ms | — |
| Minimum | 116.6397 ms | 128.1917 ms | — |
| Maximum | 1429.3020 ms | 602.1295 ms | — |

The hybrid median was higher in this run, while classical p95 and p99 were
higher. The classical group contained a 1429 ms observation, retained in the
data, and the p99 calculation is sensitive to very few observations. The
differences cannot be attributed solely to the group: relay and network
variation, scheduling, sequential ordering and other uncontrolled conditions
are included. The sample does not establish that either group generally has
better tail latency. Repeat independent, interleaved runs under a stable and
documented path before making a performance claim.

No ClientHello/ServerHello sizes, total handshake bytes, packet counts,
retransmissions, throughput or resource usage were collected. A packet capture
would require an agreed scope and a separate documented collection process.

## Artifacts and reproduction

- [Raw observations](raw.csv), [warm-ups and metadata](metadata.json), and
  [summary](summary.json).
- [Recalculated report](report/report.md) and [distribution and percentile chart](report/handshake_comparison.png).
- [Earlier 10-per-mode smoke data](../envoy-tailscale-smoke-20261101/raw.csv)
  remains separate and was not combined with this run.

With the shared Kali machine reachable and approved for testing, from the
project root use a new output directory:

```powershell
python scripts/benchmark_handshake_probe.py --host 100.71.117.30 --port 8444 `
  --server-name localhost --ca-file examples/envoy-tls-test/envoy-test-cert.pem `
  --dll 'C:\Program Files\OpenSSL-Win64\bin\libssl-4-x64.dll' `
  --per-block 50 --warmup 5 --timeout 15 --output-dir results/week2/NEW_RUN
python scripts/report_handshake_probe.py results/week2/NEW_RUN
```

Confirm the current server version, configuration, identity, network path,
team authorization and load limits first. This experimental Windows client
does not support a client certificate and cannot perform an mTLS experiment.
The runner stops on failure and preserves attempted measured rows; failed or
incomplete runs cannot be plotted as complete comparisons by the report tool.
