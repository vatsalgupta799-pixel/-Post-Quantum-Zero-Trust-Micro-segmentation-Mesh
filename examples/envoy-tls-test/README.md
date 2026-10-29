# Standalone Envoy TLS 1.3 Test

## Purpose

This example runs an Envoy HTTPS endpoint and lets you test classical and hybrid post-quantum TLS 1.3 key exchange.

- Classical group: `X25519`
- Hybrid group: `X25519MLKEM768`
- HTTPS port: `8444`

## Requirements

- Linux
- OpenSSL with support for `X25519MLKEM768`
- An Envoy binary built with support for the hybrid group

## 1. Generate a local test certificate

From the repository root, run:

```bash
bash examples/envoy-tls-test/generate-certs.sh
```

This creates a self-signed certificate and private key in `/tmp`. Do not commit or share the private key.

## 2. Validate the configuration

Replace `/path/to/envoy` with the path to your Envoy executable:

```bash
/path/to/envoy --mode validate \
  -c examples/envoy-tls-test/envoy.yaml
```

## 3. Start Envoy

```bash
/path/to/envoy -c examples/envoy-tls-test/envoy.yaml
```

Keep this terminal open while running tests.

## 4. Test hybrid TLS

In a second terminal:

```bash
openssl s_client \
  -connect 127.0.0.1:8444 \
  -tls1_3 \
  -groups X25519MLKEM768 \
  -servername localhost \
  -brief </dev/null
```

Look for:

`Negotiated TLS1.3 group: X25519MLKEM768`

## 5. Test classical TLS

```bash
openssl s_client \
  -connect 127.0.0.1:8444 \
  -tls1_3 \
  -groups X25519 \
  -servername localhost \
  -brief </dev/null
```

Look for `Peer Temp Key: X25519`.

## 6. Test the HTTPS response

```bash
curl -k https://localhost:8444/
```

Expected response:

`PQC TLS test endpoint`

The `-k` option disables certificate verification and is for this local, self-signed test only.

## Limitations

This is a standalone TLS demonstration. It does not configure mutual TLS (mTLS), Kubernetes integration, production certificate trust, or OPA policy enforcement. Benchmark results should be interpreted in the context of the measurement method and local environment.
