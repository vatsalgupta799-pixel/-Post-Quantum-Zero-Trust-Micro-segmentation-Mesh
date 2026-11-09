# Classical versus hybrid TLS connection benchmark

- Target: `127.0.0.1:8444`
- Measured iterations per mode: 2
- Warm-ups per mode: 1
- Measurement includes OpenSSL process startup and local connection overhead.
- The temporary self-signed certificate is not a production trust test.

| Mode | Expected group | Successes | Failures | Success rate | Median (ms) | p95 (ms) |
|---|---|---:|---:|---:|---:|---:|
| classical | X25519 | 2 | 0 | 100.0% | 9.575 | 9.618 |
| hybrid | X25519MLKEM768 | 2 | 0 | 100.0% | 9.371 | 9.808 |

- Hybrid-minus-classical median difference: `-0.204 ms`.
- Relative median difference: `-2.13%`.
- This is an observed local connection-time difference, not a universal performance claim.
