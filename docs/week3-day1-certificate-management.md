# Week 3 — Day 1: PQC Certificate Management

## Objective
Inspect the existing certificate infrastructure and design a plan for integrating HashiCorp Vault with certificate management, automated rotation, and Kubernetes workload injection.

## 1. Existing Certificate Authority

Inspected `certs/ca-cert.pem` using OpenSSL.

Findings:
- Subject: CN=Zero-Trust-Demo-CA
- Issuer: CN=Zero-Trust-Demo-CA
- Type: Self-signed CA certificate
- Public key algorithm: RSA 4096-bit
- Signature algorithm: SHA256 with RSA
- Validity: 27 October 2026 to 27 October 2027

The CA private key is stored locally and the `certs/` directory is excluded by `.gitignore`.

## 2. Existing Server Certificate

Inspected `certs/server-cert.pem`.

Findings:
- Subject: CN=localhost
- Issuer: CN=Zero-Trust-Demo-CA
- Public key algorithm: RSA 2048-bit
- Signature algorithm: SHA256 with RSA
- Validity: 27 October 2026 to 27 October 2027

Certificate-chain verification was successful:

`openssl verify -CAfile certs/ca-cert.pem certs/server-cert.pem`

Result: `certs/server-cert.pem: OK`

## 3. Existing Client Authentication

Reviewed `evidence/certificate-authentication-demo.txt`.

Previously demonstrated:
- Local CA creation.
- Server and client certificate generation.
- CA-based certificate verification.
- TLS server requiring a client certificate.
- Successful authentication of a trusted client.
- Server identified the client as `CN=trusted-client`.

The no-client-certificate rejection test still needs clear confirmation.

This is conventional RSA-based X.509 authentication, not PQC-signed certificate authentication.

## 4. Existing Envoy Test Certificate

Inspected `examples/envoy-tls-test/generate-certs.sh`.

The script generates:
- A self-signed RSA 2048-bit certificate.
- SHA256-RSA signature.
- Subject CN=localhost.
- SAN entries for localhost and 127.0.0.1.
- Certificate and private key under `/tmp`.

The filename `pqc-cert.pem` does not make the certificate post-quantum. It is a classical test certificate.

## 5. PQC Cryptography Clarification

The project uses X25519 and ML-KEM-768 in its educational hybrid key-establishment prototype.

Important distinction:
- ML-KEM is a post-quantum key-encapsulation mechanism.
- ML-DSA is a post-quantum digital-signature algorithm.
- ML-KEM does not itself provide certificate signatures.
- PQC certificate issuance requires compatible certificate tooling, signature support, and validation across the participating components.

Actual Vault and certificate-toolchain support must be verified before claiming PQC certificate issuance.

## 6. Proposed Certificate Management Architecture

Planned workflow:

1. HashiCorp Vault securely stores and manages certificate-related secrets.
2. A certificate-management component requests or renews certificates using an approved workflow.
3. The updated certificate and private key are delivered to a Kubernetes Secret.
4. The workload receives the updated certificate.
5. Envoy reloads the certificate, where supported.
6. TLS connectivity and certificate validity are tested after rotation.

This is a proposed architecture, not yet an implemented integration.

## 7. Week 3 Implementation Tasks

- Coordinate with the Vault teammate on installation, access, and policies.
- Integrate the certificate workflow with Vault.
- Develop an automated certificate rotation mechanism.
- Update Kubernetes Secrets securely.
- Inject updated certificates into workloads.
- Verify certificate reload and TLS connectivity.
- Record test evidence and document limitations.

## 8. Day 1 Status

Completed:
- Inspected the existing CA and server certificate.
- Verified the server certificate chain.
- Reviewed existing client-authentication evidence.
- Inspected the Envoy certificate-generation script.
- Identified the classical cryptography baseline.
- Established a proposed Vault-to-Kubernetes certificate-management workflow.

Pending:
- Vault integration.
- Automated certificate rotation.
- Kubernetes certificate injection and reload.
- PQC certificate-signature support verification.

No private keys or certificate files are included in this report.
