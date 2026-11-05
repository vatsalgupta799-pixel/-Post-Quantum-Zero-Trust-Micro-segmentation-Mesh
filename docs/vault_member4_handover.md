# Member 4 handover: local Vault certificate workflow

This is an educational local instance, not a shared production CA. Vault's API is `http://127.0.0.1:8200`; it is reachable only from the same machine and is plaintext HTTP. Before remote integration, deploy validated TLS, use an accessible address, and review network access and identity controls. Vault must be running and unsealed with the existing recovery shares; do not reinitialize it.

The configured authentication mount is `approle/`, and the certificate manager's role is `certificate-manager`. A trusted Vault administrator must provide its Role ID and a fresh, single-use Secret ID through separate secure channels. Prefer a short-lived [response-wrapped Secret ID](https://developer.hashicorp.com/vault/docs/auth/approle/approle-pattern); treat the wrapping token as sensitive too. Role IDs identify roles but should still be distributed carefully. Secret IDs last at most 10 minutes and one login; application service tokens last 10 minutes, up to 15 minutes maximum, and are limited to local IP access. These local CIDR restrictions must be redesigned before use from a different machine or container.

```text
VAULT_ADDR=http://127.0.0.1:8200
VAULT_ROLE_ID=<securely supplied Role ID>
VAULT_SECRET_ID=<securely supplied one-use Secret ID>
```

These are placeholders, not credentials. The application submits the Role ID and Secret ID to `POST /v1/auth/approle/login` and uses the returned token in the `X-Vault-Token` header. Supply credentials through a protected in-memory or secret-delivery channel, not command arguments, Git, ordinary logs, screenshots or chat. The test script performs this exchange in memory, but it does not provision credentials for a teammate.

The PKI mount is `pki/`; the approved role is `service-a-role`. Generate the workload key locally and send its CSR to `POST /v1/pki/sign/service-a-role` with common name `service-a.mesh.test` and a requested TTL no longer than 24 hours (default one hour). The policy does **not** grant access to `pki/issue`, other roles, CA configuration, CA private keys, other services' secrets, or revocation. It permits reading the public CA certificate at `GET /v1/pki/cert/ca`; a PEM CA certificate is also available at `GET /v1/pki/ca`. The issuer is an online ECDSA P-256 demonstration root with a seven-day lifetime. CA and CRL URLs are local-only. The certificate manager can use the public certificate returned by its own signing request; there is no general certificate-list permission.

Actual tests verified approved CSR signing, CA signature, and denied PKI-role modification and secret access. A separate administrator test revoked a demonstration certificate and confirmed its serial in the signed CRL. The client must enforce revocation; this has not been tested. Vault 2.2 documents ML-DSA X.509 support, but this instance has only tested conventional ECDSA P-256. ML-DSA issuance and client compatibility remain unverified. ML-KEM key exchange does not itself create certificate signatures. See [PKI configuration](vault_pki_configuration.md) before choosing an integration. Automated rotation and workload injection remain Member 4's work.
