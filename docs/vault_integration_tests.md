# Vault integration test evidence

## Prior evidence

Part 2's sanitized record from 5 November 2026 reports live KV v2 versioning and isolation, an ECDSA P-256 CSR signed by the local CA, and certificate revocation confirmed in a signed CRL. That earlier result does not establish the server's current state.

## Part 3 audit and integration

On 8 November 2026 the existing Vault instance was restarted without changing its data, unsealed by the operator, and checked live: Vault 2.2.1 reported initialized, unsealed, Raft storage and active; health returned HTTP 200. The operator ran `python scripts/vault_integration_audit.py` privately. The audit confirmed administrator authentication, KV v2 at `secret/`, PKI at `pki/`, AppRole, the three role-policy bindings and policy files, 600-second token and Secret ID TTL, one Secret ID use, 900-second token maximum, and loopback restrictions. The PKI role allows only `service-a.mesh.test`, EC P-256, one-hour TTL and 24-hour max; wildcards, arbitrary names, subdomains and IP SANs are disabled. The public CA expires 12 November 2026 at 11:40:42 UTC. The operator then ran `python scripts/vault_integration_demo.py` privately: **49 of 49 recorded checks passed** against the real server. Scripts do not save or print tokens, Secret IDs, secret values, or private keys. Sanitized results are written under ignored `.tmp/`.

| Check | Expected | Part 3 actual |
|---|---|---|
| Connection, initialized and unsealed | Health HTTP 200 | PASS, live status and verifier |
| Service A, B and certificate-manager AppRole login | Valid credentials accepted | PASS, HTTP 200 each |
| Own KV path / other service's path | 200 / 403 | PASS, both services |
| Invalid credentials, missing or invalid token | Rejected | PASS, HTTP 400 / 403 |
| Certificate manager signs approved CSR | 200, valid CA signature and SAN | PASS, HTTP 200 and cryptographic checks |
| Service A signs CSR | 403 | PASS, HTTP 403 |
| Certificate manager reads PKI role administration / uses issue endpoint | 403 | PASS, HTTP 403; Part 3 did not attempt a role modification |
| CA, chain, and test certificate retrieval | 200 and consistency checks | PASS, HTTP 200 and matching fingerprints |
| Disposable certificate revocation | Signed CRL contains serial | PASS, HTTP 200 and signature/serial checks |
| Revoked disposable service token | Protected access denied | PASS, HTTP 403 |

The issued ECDSA P-256 test certificate had validity 2026-11-08 13:27:46 UTC through 14:28:16 UTC. It was revoked by the test and must not be used. The script verified its signature against the retrieved CA and checked that CA appeared in the retrieved chain; this is not independent trust-anchor provisioning or a client-side TLS test. It did not persist the private key. The test used `sys/capabilities-self` for the actual AppRole tokens and verified the certificate-manager could not issue, revoke, administer roles, or access Service A secrets. CA retrieval succeeded, but CA-path effective capabilities were not separately queried; the CA endpoint is public and its success alone does not prove the policy grant. It did not contact Member 4's application.

The operator runs `python scripts/vault_integration_audit.py` and `python scripts/vault_integration_demo.py` from the project root, entering the administrator token at hidden prompts. The administrator token is used only for audit, test credential provisioning, and revoking the disposable certificate/token; application requests use AppRole tokens. Actual token expiration, token renewal, remote TLS, client-side revocation enforcement and PQC certificate signing have not been tested.

Offline unit checks, `python -m pytest -q tests/test_vault_integration.py`, produced **4 passed, 1 skipped** on 8 November 2026. The skipped test is an explicitly opted-in live integration test, not a live pass. To run it in a private PowerShell session, use `$env:VAULT_RUN_LIVE='1'` then `python -m pytest -s -q tests/test_vault_integration.py`; it prompts for an administrator token, creates one-use credentials and issues/revokes a disposable certificate. Remove the environment variable afterward with `Remove-Item Env:VAULT_RUN_LIVE`.

An independent connection-error check called `VaultHTTP().call('sys/health')` with a test base of `http://127.0.0.1:1/v1/`; it returned the sanitized `VaultUnavailable` exception as expected. This is a real local connection-failure check, not an authenticated Vault integration test.
