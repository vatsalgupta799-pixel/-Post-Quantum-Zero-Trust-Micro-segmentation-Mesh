# Vault integration architecture

```mermaid
flowchart LR
  A[Service A client] -->|AppRole: service-a| Auth[Vault AppRole authentication]
  B[Service B client] -->|AppRole: service-b| Auth
  M[Certificate-manager client] -->|AppRole: certificate-manager| Auth
  Auth --> ACL[Vault ACL policy evaluation]
  ACL -->|service-specific read| KV[KV v2: secret/]
  ACL -->|sign approved CSR| PKI[PKI: pki/sign/service-a-role]
  PKI -->|public certificate and CA chain| M
  M -. planned integration .-> Downstream[Member 4: renewal, distribution and injection]
```

The diagrams depict the configured local interfaces and planned downstream integration. Member 4's actual application is not present in this workspace, and the downstream flow has not been demonstrated. The certificate manager cannot read Service A's KV secrets under the existing policy; those reads use Service A's separate identity. Vault's listener is localhost-only HTTP and is suitable only for a local demonstration. PKI uses a single online ECDSA P-256 root CA, not a production offline-root hierarchy.
