SkyWatch
A simple distributed weather application demonstrating:

* Flask frontend
* Flask backend
* Docker
* K3s
* Ansible
* Helm
* ArgoCD
* GitHub Actions

# SkyWatch - Installation & Deployment Guide

## Overview

SkyWatch is a cloud-native weather application consisting of:

- Frontend (Flask web UI)
- Backend (Flask REST API)
- K3s Kubernetes cluster
- Helm deployment
- GitHub Actions CI/CD
- GitHub Container Registry (GHCR)
- ArgoCD GitOps
- Terraform (bonus: GitOps bootstrap)

---

# Prerequisites

## Workstation

Install:

- Git
- Docker
- kubectl
- Helm
- Terraform
- Ansible
- Multipass (or equivalent VM solution)

Verify:

```bash
git --version
docker --version
kubectl version --client
helm version
terraform version
ansible --version
```

---

# 1. Clone Repository

```bash
git clone https://github.com/boofinka/skywatch.git

cd skywatch
```

---

# 2. Provision Infrastructure

## Create Virtual Machines

Three Ubuntu VMs are required:

| VM | Purpose |
|----|----------|
| skywatch-cp | K3s Control Plane |
| skywatch-worker1 | Worker |
| skywatch-worker2 | Worker |

Example using Multipass:

```bash
multipass launch 22.04 --name skywatch-cp
multipass launch 22.04 --name skywatch-worker1
multipass launch 22.04 --name skywatch-worker2
```

Retrieve the IP addresses:

```bash
multipass list
```

---

# 3. Configure Ansible Inventory

Edit:

```text
ansible/inventories/hosts.yml
```

Example:

```yaml
all:
  children:
    control:
      hosts:
        skywatch-cp:
          ansible_host: <CONTROL_PLANE_IP>

    workers:
      hosts:
        skywatch-worker1:
          ansible_host: <WORKER1_IP>

        skywatch-worker2:
          ansible_host: <WORKER2_IP>
```

---

# 4. Deploy K3s Cluster

Run:

```bash
cd ansible

ansible-playbook \
  -i inventories/hosts.yml \
  playbooks/site.yml
```

The playbook:

- installs K3s server
- installs K3s agents
- joins workers to cluster
- uses pinned K3s version:

```yaml
k3s_version: v1.31.4+k3s1
```

---

# 5. Configure kubectl

Copy kubeconfig from the control plane:

```bash
scp ubuntu@<CONTROL_PLANE_IP>:/etc/rancher/k3s/k3s.yaml ~/.kube/config
```

Update server address if required.

Verify:

```bash
kubectl get nodes
```

Expected:

```text
skywatch-cp
skywatch-worker1
skywatch-worker2
```

All nodes should show:

```text
Ready
```

---

# 6. Deploy SkyWatch Using Helm

Move to project root:

```bash
cd ~/projects/skywatch
```

Deploy:

```bash
helm upgrade \
  --install skywatch \
  ./helm/skywatch
```

Verify:

```bash
kubectl get pods
```

---

# 7. Access the Application

Verify ingress:

```bash
kubectl get ingress
```

Expected host:

```text
skywatch.local
```

Add DNS mapping:

Windows:

```text
C:\Windows\System32\drivers\etc\hosts
```

Linux:

```bash
/etc/hosts
```

Add:

```text
<CONTROL_PLANE_IP> skywatch.local
```

Open:

```text
http://skywatch.local
```

---

# 8. GitHub Container Registry

Images are published to:

```text
ghcr.io/boofinka/skywatch-frontend
ghcr.io/boofinka/skywatch-backend
```

Tagged using:

```text
<git commit sha>
```

Example:

```text
ghcr.io/boofinka/skywatch-backend:8fd40fd...
```

---

# 9. Continuous Integration

Workflow file:

```text
.github/workflows/build.yml
```

Pipeline executes on every push to:

```text
main
```

Pipeline stages:

1. Checkout repository
2. Lint application code
3. Build frontend image
4. Build backend image
5. Push to GHCR
6. Update Helm image tags
7. Commit updated values.yaml
8. Prevent CI loop using `[skip ci]`

---

# 10. Verify CI/CD

Push:

```bash
git push origin main
```

Verify in GitHub:

```text
Actions
```

Successful pipeline stages:

```text
Lint backend
Lint frontend
Build backend
Push backend
Build frontend
Push frontend
Update Helm image tags
```

---

# 11. Install ArgoCD

Create namespace:

```bash
kubectl create namespace argocd
```

Install ArgoCD:

```bash
kubectl apply -n argocd \
-f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Verify:

```bash
kubectl get pods -n argocd
```

All pods should reach:

```text
Running
```

---

# 12. Create ArgoCD Application

Apply:

```bash
kubectl apply -f argocd/project.yaml

kubectl apply -f argocd/application.yaml
```

Verify:

```bash
kubectl get applications -n argocd
```

Expected:

```text
skywatch
```

---

# 13. Enable Automated GitOps

ArgoCD Application includes:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Behavior:

```text
Git Push
    ↓
GitHub Actions
    ↓
New Images
    ↓
values.yaml Updated
    ↓
ArgoCD Detects Change
    ↓
Automatic Deployment
```

---

# 14. Terraform Bonus

Terraform can bootstrap GitOps resources.

Directory:

```text
terraform/
├── versions.tf
├── provider.tf
├── argocd.tf
└── application.tf
```

Initialize:

```bash
cd terraform

terraform init
```

Validate:

```bash
terraform validate
```

Preview resources:

```bash
terraform plan
```

Terraform manages:

- ArgoCD namespace
- ArgoCD Helm release
- ArgoCD Application

---

# Verification Checklist

## Application

```bash
curl http://skywatch.local
```

Frontend loads successfully.

---

## Backend Health

```bash
kubectl port-forward svc/skywatch-backend 5000:5000
```

```bash
curl http://localhost:5000/health
```

Expected:

```json
{
  "status": "ok"
}
```

---

## Frontend Health

```bash
kubectl port-forward deployment/skywatch-frontend 8080:8080
```

```bash
curl http://localhost:8080/health
```

Expected:

```json
{
  "status": "healthy"
}
```

---

## Kubernetes Pods

```bash
kubectl get pods -A -o wide
```

Verify:

- frontend pods running
- backend pods running
- workloads scheduled on worker nodes

---

# Troubleshooting

## ArgoCD Sync Status = Unknown

Possible symptom:

```text
no route to host
```

Cause:

```text
Cross-node pod networking issue
```

Verify:

```bash
kubectl describe application skywatch -n argocd
```

---

## Images Not Pulling

Check:

```bash
docker pull \
ghcr.io/boofinka/skywatch-backend:<tag>
```

Verify image exists and is publicly accessible.

---

## Pipeline Cannot Push

Ensure:

Repository Settings → Actions → Workflow Permissions

```text
Read and write permissions
```

is enabled.

---

# Architecture

```text
GitHub
   │
   ▼
GitHub Actions
   │
   ▼
GitHub Container Registry
   │
   ▼
Helm values.yaml
   │
   ▼
ArgoCD
   │
   ▼
K3s Cluster
   │
   ├── Frontend
   └── Backend
```
