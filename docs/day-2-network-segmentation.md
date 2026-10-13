# Day 2: Zero-Trust Network Segmentation

## Objective
Implement Kubernetes NetworkPolicies to restrict communication between
frontend, backend, and database workloads in the `zero-trust` namespace.

## Environment
- Kubernetes: Minikube
- CNI: Calico
- Namespace: `zero-trust`
- Workloads: frontend, backend, database
- Note: The database deployment currently uses an NGINX placeholder,
  not a real database server.

## Network Policies

### 1. Default Deny Ingress
File: `kubernetes/network-policies/default-deny-ingress.yaml`

- Selects all pods in the `zero-trust` namespace.
- Denies ingress traffic unless another applicable policy allows it.

### 2. Frontend to Backend
File: `kubernetes/network-policies/allow-frontend-to-backend.yaml`

- Allows pods labelled `app=frontend` to reach backend pods.
- Permits TCP port 80.

### 3. Backend to Database
File: `kubernetes/network-policies/allow-backend-to-database.yaml`

- Allows pods labelled `app=backend` to reach database pods.
- Permits TCP port 80.

## Validation and Test Results

| Test | Observed result |
|---|---|
| Untrusted pod to backend | Connection timed out |
| Frontend pod to backend | NGINX welcome page returned |
| Backend pod to database | NGINX welcome page returned |
| Frontend pod to database | Connection timed out |
| YAML client-side dry run | All three policies recognized |

The successful requests show that the intended allowed paths worked.
The timeouts are consistent with the intended blocked paths, although
a timeout alone does not prove the exact cause.

## Limitations

- The database workload is an NGINX placeholder.
- These policies control ingress traffic; no default-deny egress
  policy has been configured.
- Mutual TLS (mTLS) and post-quantum cryptography (PQC), including
  ML-KEM, have not been implemented by this work.
- Kubernetes NetworkPolicies provide network-level controls; they do
  not independently provide workload identity or encryption.

## Day 2 Status

The three NetworkPolicy manifests have been organized and passed
`kubectl apply --dry-run=client` validation. The allowed and blocked
communication tests produced the expected observations.

## Next Steps

- Verify the final cluster and policy state.
- Plan workload identity and mTLS implementation.
- Investigate a practical ML-KEM integration.
- Add reproducible testing evidence and update the project README.
