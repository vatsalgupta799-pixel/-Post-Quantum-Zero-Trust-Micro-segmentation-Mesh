# Day 3: Workload Identity and mTLS Preparation

## Objective
Prepare the design for workload identity and mutual TLS (mTLS) in the Post-Quantum Zero-Trust Microsegmentation Mesh project.

## 1. Kubernetes Health Check
- Confirmed Minikube status reports the host, kubelet, and API server as running.
- Confirmed the Kubernetes control plane responds through kubectl.
- Verified the Minikube IP is 192.168.49.2.

## 2. Existing Network Segmentation
Verified these policies exist in the zero-trust namespace:
- default-deny-ingress
- allow-frontend-to-backend
- allow-backend-to-database

## 3. Workload Identity Design
Each workload should have a distinct identity instead of trusting network location alone.
Planned approach:
- Assign separate identities to frontend, backend, and database workloads.
- Use Kubernetes service accounts as an initial identity mechanism.
- Define which workloads are permitted to communicate.
- Avoid granting unnecessary permissions.

## 4. mTLS Design
Mutual TLS allows both communicating services to authenticate each other and encrypt traffic.
Planned approach:
- Evaluate a service mesh such as Istio for workload certificates and mTLS.
- Define service-to-service authentication and authorization rules.
- Test permitted and denied communication after configuration.

## 5. Post-Quantum Cryptography
ML-KEM is a post-quantum key-encapsulation mechanism, not a complete replacement for TLS.
Future work will evaluate how post-quantum key establishment can be integrated into the TLS stack.

## 6. Current Limitations
- mTLS is not implemented yet.
- ML-KEM is not implemented yet.
- The database workload is currently an NGINX placeholder, not a real database.
- Kubernetes NetworkPolicies remain the current network-level control.

## 7. Next Steps
- Choose and configure a workload identity and mTLS solution.
- Implement and test service-to-service mTLS.
- Evaluate ML-KEM support in the chosen cryptographic stack.
- Update test evidence and project documentation.

## Status
Day 3: Initial verification and design documentation completed. Implementation remains pending.
EOF 
