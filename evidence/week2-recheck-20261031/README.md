# Local TLS group recheck — 31 October 2026

A temporary OpenSSL 4.1.0 `s_server` was started on IPv4 loopback port 19593,
with TLS 1.3 and both X25519 and X25519MLKEM768 enabled. Each verifier run
restricted the client to its expected group, trusted the temporary localhost
certificate, and checked the hostname. Both successful results are preserved
in the adjacent JSON files; each reports a new session, successful certificate
validation and the expected negotiated group. The server was stopped and its
temporary private key removed. These are verification checks, not timing data,
an Envoy measurement, or an mTLS test.

An earlier same-session attempt without local network access failed at TCP.
This successful repeat used an execution context that permits local networking;
the previous failure should not be treated as proof of a broken TLS setup.
