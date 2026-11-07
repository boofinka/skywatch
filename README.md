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