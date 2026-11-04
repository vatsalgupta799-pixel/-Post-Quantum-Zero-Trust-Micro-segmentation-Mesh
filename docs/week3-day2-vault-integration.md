# Week 3 – Day 2: Vault Integration Preparation

## Objective
Prepare the Kubernetes environment and certificate-management workflow for integration with HashiCorp Vault.

## Work Completed

### 1. Minikube Investigation
- Checked Minikube cluster status.
- Found the Minikube host running, but kubelet and API server stopped.
- Investigated kubelet service logs.
- Identified the missing `/etc/kubernetes/bootstrap-kubelet.conf` file.
- Confirmed that `/etc/kubernetes/manifests/` was empty.

### 2. Certificate Verification
- Verified the existing kubelet client certificate.
- Confirmed its issuer is `minikubeCA`.
- Confirmed the Minikube CA certificate is present and unexpired.
- Inspected the existing Kubernetes certificate and configuration directories.

### 3. etcd Data Protection
- Confirmed that etcd snapshot, database, and WAL files exist.
- Created an etcd backup at `/tmp/etcd-backup.tar.gz` inside Minikube.
- Copied the backup to Kali:
  `/home/vatsal/etcd-backup.tar.gz`
- Verified that the copied backup exists.

### 4. Minikube Profile Investigation
- Confirmed the original Docker-based Minikube profile.
- Recorded Kubernetes version: v1.37.0.
- Recorded container runtime: containerd.
- Recorded CNI: Calico.
- Confirmed the original Minikube Docker container is running.

## Current Status

**Day 2 Status: NOT COMPLETED**

**Vault integration: Blocked / Pending**

The planned Day 2 task was not completed. The Kubernetes API server and kubelet are not operational because required Kubernetes configuration files and control-plane manifests are missing.

The existing etcd data has been backed up. Cluster recovery is still pending.

## Pending Tasks
1. Recover the existing Minikube cluster safely.
2. Coordinate with the Vault setup team member.
3. Confirm Vault server address and authentication method.
4. Review Vault policies and certificate-management permissions.
5. Integrate the certificate workflow with Vault.
6. Plan automated certificate rotation and Kubernetes Secret updates.

## Important Notes
- Existing RSA certificates are classical certificates, not PQC certificates.
- ML-KEM is a post-quantum key-encapsulation mechanism; it does not sign X.509 certificates.
- No successful Vault integration or automated certificate rotation is claimed in this report.

