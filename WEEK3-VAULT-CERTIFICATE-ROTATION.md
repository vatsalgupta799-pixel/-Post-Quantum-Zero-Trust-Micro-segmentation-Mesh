# Week 3 – Vault PKI and Kubernetes TLS Certificate Rotation

## Objective
Integrate HashiCorp Vault PKI with Kubernetes to issue, deploy,
and rotate workload TLS certificates.

## Implementation
1. Configured a Vault PKI secrets engine and certificate role.
2. Issued a TLS certificate for cert-demo.zero-trust.local.
3. Transferred certificate files securely to Kali Linux.
4. Created and updated the Kubernetes TLS Secret.
5. Configured Nginx to serve HTTPS using the mounted certificate.
6. Automated certificate renewal and Kubernetes Secret updates
   using a PowerShell script.
7. Restarted the workload to load the rotated certificate.

## Verification Evidence
- TLS protocol: TLS 1.3
- Cipher suite: TLS_AES_256_GCM_SHA384
- Certificate issuer: Week3 Zero Trust Internal CA
- Certificate public key: RSA-2048
- Nginx HTTP response: 200 OK
- Live certificate serial matched the newly issued Vault certificate.

## Limitations
- The certificate uses classical RSA-2048, not a post-quantum signature.
- Vault was running in development mode.
- Rotation was triggered by running a script; periodic scheduling
  has not yet been configured.
