# Week 2 benchmarking — review handover

## Result and scope

Two independent runs measured real TLS 1.3 handshakes against the team's
Envoy test endpoint over a Tailscale private network. In each run, every one
of the 100 measured connections per group succeeded, used a new session,
verified the server certificate and hostname, and reported the intended
negotiated group. The groups were X25519 and X25519MLKEM768. These results are
**server-authenticated TLS**, not mTLS or post-quantum certificates.

The experiment measures the time from immediately before OpenSSL's first
`SSL_connect` call until the TLS handshake completes; TCP connection setup and
application requests are excluded. Certificate validation, network round
trips, client polling and scheduling are included. The measurement is not
pure cryptographic processing time.

| Run | Block order | Classical p50 / p95 / p99 | Hybrid p50 / p95 / p99 |
| --- | --- | --- | --- |
| 1 | hybrid / classical / classical / hybrid | 195.15 / 373.74 / 1139.75 ms | 239.58 / 327.73 / 555.90 ms |
| 2 | classical / hybrid / hybrid / classical | 192.63 / 394.66 / 618.23 ms | 272.80 / 425.57 / 590.90 ms |

Each group had 100 attempts and 100 successes in each run; 20 warm-ups per
run were excluded. Hybrid p50 was 44.42 ms higher in run 1 and 80.18 ms
higher in run 2. p95 changed direction between runs; p99 was particularly
sensitive to slow observations. These are descriptive results, not a reliable
estimate of the algorithms' intrinsic overhead. Tailscale reported its `blr`
relay before and after each run; the route was not continuously monitored.
Network variation, scheduling, and 100 samples per group limit conclusions.

## Evidence and project setup

- [Run 1 method, raw data, statistics and chart](../results/week2/envoy-tailscale-20261101/README.md).
- [Run 2 method, raw data, statistics and chart](../results/week2/envoy-tailscale-reverse-20261101/README.md).
- [Classical verification](../evidence/envoy-tailscale-20261101/classical.json)
  and [hybrid verification](../evidence/envoy-tailscale-20261101/hybrid.json)
  show the exact group, TLS version, certificate and new-session status.
- The [project's Envoy build record](../evidence/envoy-pqc-build-verification.txt)
  reports Envoy 1.41.0-dev with BoringSSL and build identifier
  `85aa7f0fa5525d7b60d3d95e92902522a8a69dfb`. This is a historical record;
  the live binary version was not independently captured during the runs.
- A separate [certificate-validated HTTP check](../evidence/envoy-tailscale-20261101/http-confirmation.txt)
  returned `server: envoy` and the documented test response after the runs.
  The HTTP request was not included in the timing measurements and does not
  establish the binary version or complete configuration.
- The checked-in [standalone Envoy configuration](../examples/envoy-tls-test/envoy.yaml)
  and its [instructions](../examples/envoy-tls-test/README.md) document TLS 1.3
  and no OPA filter or mTLS for that example. The exact live configuration was
  not independently captured, so the example is not proof of live OPA settings.
  The separate OPA-enabled Kubernetes demonstration is a different setup.
- The test uses the project's public self-signed RSA localhost certificate,
  explicitly trusted by the client, not a CA-issued or PQC certificate. The
  new timing client currently supports DNS names and server authentication,
  not client-certificate authentication.
- The project test suite passed **147 tests** after the repeat-run changes.
  Both runs' rows, warm-ups and summary statistics were independently checked.

## Suggested five-minute explanation

1. **Question:** What happens to real TLS 1.3 handshake time when the named
   group changes from X25519 to X25519MLKEM768?
2. **Control:** Same Envoy endpoint, client, certificate validation and network
   path for the two groups within each run. The client restricted and checked
   the actual group on every successful connection.
3. **Method:** New connection each time; the timer covered TLS handshake
   completion after TCP setup. Each mode had 100 measurements per run and
   separate warm-ups. The second run reversed the balanced block order.
4. **Observation:** Hybrid median was higher in both runs; the tail differed
   between runs. Show the two charts and explain the relay and sample limits.
5. **Conclusion:** The prototype can compare verified TLS handshakes, but
   these two network-dependent runs do not establish a universal PQC overhead.

## Reproduce or extend

After coordinating load and endpoint availability with the team, run the
commands in the individual study reports using a new output directory. The
runner supports `--order hybrid-first` and `--order classical-first` for
balanced reversed order. Keep run results separate and record the path, Envoy
version, actual configuration, trust material and authentication settings.

Remaining extensions: repeated larger runs over a stable documented direct
path; scoped packet captures and handshake byte counts; client/server CPU
measurements; and separate resumption, concurrency, mTLS and OPA-overhead
experiments if infrastructure and team coordination permit. Those were not
measured and should not be reported as complete. A direct Tailscale route or
server-side local measurements may reduce relay variation, but still require
their own documented controls and group verification.
