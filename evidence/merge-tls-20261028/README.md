# Merge verification smoke test

OpenSSL 4.1.0 `s_server -tls1_3 -groups X25519:X25519MLKEM768 -www` on loopback, with an ephemeral localhost self-signed certificate explicitly trusted by the client. Each mode had one warm-up and two measured attempts; all 2/2 per mode passed TLS 1.3, certificate/hostname and exact group checks. The certificate and private key are not included; local CA file paths in metadata are historical. Sessions are unknown, not independently proven fresh. This is a process-inclusive smoke test, not a performance comparison or Envoy evidence.
