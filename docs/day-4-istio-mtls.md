# Day 4: Istio and Mutual TLS (mTLS)

## Objective
Configure Istio in the Kubernetes Zero-Trust environment and enable strict mutual TLS (mTLS) for workloads in the `zero-trust` namespace.

## Environment
- Operating system: Kali Linux
- Kubernetes environment: Minikube
- Service mesh: Istio 1.31.1
- Namespace: `zero-trust`
- Workloads: frontend, backend, database

## Work Completed
1. Installed Istio using the demo profile.
2. Enabled automatic Istio sidecar injection for the `zero-trust` namespace.
3. Restarted application deployments to enable sidecar injection.
4. Applied a `PeerAuthentication` policy named `default` with mTLS mode set to `STRICT`.
5. Checked Istio proxy status and confirmed frontend, backend, and database proxies appeared connected to `istiod`.
6. Inspected proxy certificate secrets. The backend and frontend proxy certificate output showed active, valid certificate material.
7. Checked cluster and workload health after restarting Minikube.

## Verification
- Istio proxy connectivity: observed for frontend, backend, and database.
- Strict mTLS policy: configured and verified as `STRICT`.
- TLS certificate material: inspected for application proxies.
- Service traffic: connectivity commands were prepared for frontend-to-backend and backend-to-database testing. Successful traffic results should only be recorded after observing their actual command output.

## Limitations
- These checks confirm configuration and certificate provisioning, but do not alone prove a successful m
