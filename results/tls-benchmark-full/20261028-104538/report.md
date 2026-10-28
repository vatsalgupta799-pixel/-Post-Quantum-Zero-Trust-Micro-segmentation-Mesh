# Classical versus hybrid TLS connection benchmark

- Target: `127.0.0.1:8444`
- Measured iterations per mode: 100
- Warm-ups per mode: 5
- Measurement includes OpenSSL process startup and local connection overhead.
- The temporary self-signed certificate is not a production trust test.

| Mode | Expected group | Successes | Failures | Success rate | Median (ms) | p95 (ms) |
|---|---|---:|---:|---:|---:|---:|
| classical | X25519 | 100 | 0 | 100.0% | 9.149 | 10.091 |
| hybrid | X25519MLKEM768 | 100 | 0 | 100.0% | 9.341 | 10.139 |

- Hybrid-minus-classical median difference: `0.192 ms`.
- Relative median difference: `2.10%`.
- This is an observed local connection-time difference, not a universal performance claim.
