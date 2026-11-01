# Envoy handshake repeat over Tailscale — 1 November 2026

This is a second independent TLS 1.3 run against the same team Envoy test
endpoint. It starts with the classical group, reversing the balanced group
order of [run 1](../envoy-tailscale-20261101/README.md). Each group recorded
100/100 successful fresh sessions, and each of four blocks had five excluded
successful warm-ups. Every measured row verified the expected TLS group,
server certificate and hostname. Tailscale reported the `blr` relay before and
after the run; continuous path telemetry was not collected.

The [metadata](metadata.json) records the controls and measurement boundary;
[raw.csv](raw.csv) contains every measured observation, and
[summary.json](summary.json) contains statistics. The raw rows and summary
were independently recalculated. The [report](report/report.md) and
[chart](report/handshake_comparison.png) show the distribution. No results were
combined with run 1.

| Metric | Classical | Hybrid | Hybrid minus classical |
| --- | ---: | ---: | ---: |
| p50 | 192.6289 ms | 272.8049 ms | +80.1761 ms (+41.62%) |
| p95 | 394.6559 ms | 425.5683 ms | +30.9124 ms (+7.83%) |
| p99 | 618.2272 ms | 590.8987 ms | -27.3285 ms (-4.42%) |
| Mean | 222.6644 ms | 286.3829 ms | +63.7185 ms (+28.62%) |
| Sample standard deviation | 108.8507 ms | 89.6607 ms | — |
| Minimum / maximum | 116.8403 / 846.3289 ms | 130.6195 / 594.0028 ms | — |

These observations include network round trips and scheduling, so they do not
isolate cryptographic overhead. The live server binary version and exact
configuration were not independently captured. A self-signed localhost test
certificate was explicitly trusted; the run did not use mTLS. Network sizes,
packet counts, retransmissions and CPU were not measured. With 100 samples
per mode and a relay, tail percentiles are exploratory.

With the team test endpoint available, reproduce with a **new** output path:

```powershell
python scripts/benchmark_handshake_probe.py --host 100.71.117.30 --port 8444 `
  --server-name localhost --ca-file examples/envoy-tls-test/envoy-test-cert.pem `
  --dll 'C:\Program Files\OpenSSL-Win64\bin\libssl-4-x64.dll' `
  --per-block 50 --warmup 5 --timeout 15 --order classical-first `
  --output-dir results/week2/NEW_RUN
python scripts/report_handshake_probe.py results/week2/NEW_RUN
```

For a wider review and limitations, see [the Week 2 handover](../../../docs/week2_review_handover.md).
