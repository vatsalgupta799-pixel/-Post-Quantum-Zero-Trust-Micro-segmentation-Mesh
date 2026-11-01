# Envoy connectivity attempt — 1 November 2026

The configured verifier attempted TLS 1.3 against `192.168.162.128:8444`
using the repository's `examples/envoy-tls-test/envoy-test-cert.pem` as its
trust anchor and `localhost` as the expected DNS name. The classical and
hybrid attempts each timed out after five seconds. Neither observed a TLS
version, negotiated group, successful certificate validation, or completed
connection. The adjacent JSON files preserve the sanitized results. This is
not evidence that the certificate or group configuration is invalid, nor does
it show that the server is down; the network path and current address need
checking before TLS can be verified. No benchmark was run against Envoy.

The Windows host reported VMware adapter subnets `192.168.128.0/24` and
`192.168.185.0/24`; the documented endpoint is on `192.168.162.0/24`. This
suggests a possible network mismatch but does not establish the cause. Obtain
the current Kali address and listening interface, and verify connectivity
without changing the server or disabling certificate verification.
