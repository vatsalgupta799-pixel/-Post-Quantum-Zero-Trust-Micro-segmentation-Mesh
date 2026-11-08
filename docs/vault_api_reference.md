# Local Vault integration API reference

Base address: `http://127.0.0.1:8200` on the Vault machine. This is a local-only HTTP listener, not transport-secured production access. Do not put credentials in command arguments, source, logs, chat, or screenshots. The mount and policies below are the Part 2 configuration; live revalidation for Part 3 is recorded in [integration tests](vault_integration_tests.md).

| Operation | Method and path | Input | Identity / permission | Output and errors |
|---|---|---|---|---|
| Health | GET `/v1/sys/health` | None | Unauthenticated | JSON state/version; 200 active, 503 sealed, 501 uninitialized |
| Authenticate | POST `/v1/auth/approle/login` | `role_id`, `secret_id` | Valid AppRole credentials | `auth.client_token`, TTL, policies; invalid credentials rejected |
| Service A read | GET `/v1/secret/data/application/service-a/database` | None | Service A token, `read` | `data.data` and metadata; 403 denied, 404 missing/deleted |
| Service B read | GET `/v1/secret/data/application/service-b/database` | None | Service B token, `read` | `data.data` and metadata; 403 denied, 404 missing/deleted |
| Effective permissions | POST `/v1/sys/capabilities-self` | `paths` array | Application token, `update` | Capabilities per path; `deny` if unauthorized |
| Sign CSR | POST `/v1/pki/sign/service-a-role` | PEM `csr`, `common_name`, optional `ttl` | Certificate-manager token, `update` | Public certificate, issuer/chain and serial; 400 invalid request, 403 denied |
| Generate key and certificate | POST `/v1/pki/issue/service-a-role` | `common_name`, optional TTL | Not permitted to certificate-manager | Can return a private key to an authorized caller; do not log it |
| CA and chain | GET `/v1/pki/cert/ca`, GET `/v1/pki/ca_chain` | None | Public PKI endpoints; policy also allows CA read | Public CA JSON / PEM chain; unavailable while sealed |
| Certificate | GET `/v1/pki/cert/<serial>` | Serial number | Public certificate endpoint | Public certificate JSON, or 404 if missing |
| Revoke | POST `/v1/pki/revoke` | `serial_number` | Separate administrator, not certificate-manager | Revocation status; 403 denied |

The configured role permits only `service-a.mesh.test` and EC P-256; default certificate TTL is one hour, max 24 hours. `sign` receives a CSR, so the caller keeps its private key. `issue` generates and returns a private key and is intentionally denied to the certificate-manager identity. Public PKI read endpoints do not imply access to the CA private key. Capability inspection does not itself guarantee that a request's parameters satisfy the PKI role.

References: [AppRole API](https://developer.hashicorp.com/vault/api-docs/auth/approle), [KV v2 API](https://developer.hashicorp.com/vault/api-docs/secret/kv/kv-v2), [PKI API](https://developer.hashicorp.com/vault/api-docs/secret/pki), and [capabilities-self](https://developer.hashicorp.com/vault/api-docs/system/capabilities-self).
