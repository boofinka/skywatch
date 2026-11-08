# SkyWatch - Cloud-Native Weather Application

SkyWatch is a microservices-based weather application demonstrating modern cloud-native architecture, automated infrastructure provisioning with dynamic inventory, container orchestration, and continuous GitOps delivery:

* **Microservices**: Flask Frontend (UI) & Flask Backend (REST API)
* **Containers**: Docker with multi-stage considerations & GHCR publishing
* **Infrastructure**: K3s multi-node Kubernetes running on Ubuntu VMs via Multipass
* **Dynamic Configuration Management**: Ansible dynamic inventory ([`multipass.py`](ansible/inventories/multipass.py)) with zero hardcoded IPs or join secrets
* **Packaging**: Helm 3 chart with templates for Deployments, Services, ConfigMaps, and Ingress
* **GitOps**: ArgoCD automated continuous deployment with self-healing
* **CI/CD**: GitHub Actions automated pipeline (linting, image builds, GHCR push, Helm values updates)
* **Infrastructure as Code**: Terraform bootstrap for GitOps & Kubernetes manifests

---

## Architecture Overview

```text
                           [ End User Browser ]
                                     │
                                     ▼  http://skywatch.local
                       [ Traefik Ingress Controller ]
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼ (port 80)                             ▼ (optional argocd.local)
     [ Frontend Service (ClusterIP) ]            [ ArgoCD Server Service ]
                 │
                 ▼ (port 8080)
      [ Frontend Pods (Flask UI) ]
                 │
                 ▼  http://skywatch-backend:5000/weather?city=...
      [ Backend Service (ClusterIP) ]
                 │
                 ▼ (port 5000)
    [ Backend Pods (Flask REST API) ]
                 │
                 ▼  HTTPS (Geocoding & Forecast)
         [ Open-Meteo Public API ]
```

### Components & Ports

| Component | Technology | Container Port | Service Port | Primary Endpoints |
|-----------|------------|----------------|--------------|-------------------|
| **Frontend** | Flask 3, Gunicorn | `8080` | `80` (ClusterIP) | `/` (Web UI), `/health` |
| **Backend** | Flask 3, Gunicorn | `5000` | `5000` (ClusterIP) | `/weather?city=<name>`, `/health` |
| **Ingress** | Traefik (K3s default)| — | `80` / `443` | Host: `skywatch.local` |
| **GitOps** | ArgoCD | `8080` | `80` / `443` | Host: `argocd.local` |

---

## Repository Structure

```text
.
├── .github/workflows/
│   └── build.yml               # GitHub Actions CI/CD workflow
├── ansible/
│   ├── ansible.cfg             # Configured with dynamic inventory = inventories/multipass.py
│   ├── group_vars/
│   │   └── all.yml             # Global variables (k3s_version only - no hardcoded IPs/secrets)
│   ├── inventories/
│   │   └── multipass.py        # Dynamic inventory querying Multipass instances & IPs
│   ├── playbooks/
│   │   └── site.yml            # Main cluster orchestration playbook
│   └── roles/
│       ├── k3s-server/         # Control plane install & dynamic token export
│       ├── k3s-agent/          # Worker node install & dynamic cluster join
│       └── common/             # Common prerequisites
├── argocd/
│   ├── application.yaml        # ArgoCD Application manifest for skywatch
│   ├── argocd-ingress.yaml     # Traefik ingress for ArgoCD Web UI
│   └── project.yaml            # ArgoCD Project definition
├── backend/
│   ├── app.py                  # Flask REST API connecting to Open-Meteo
│   ├── Dockerfile              # Python 3.12-slim container image
│   └── requirements.txt        # Backend dependencies (Flask, requests, gunicorn)
├── frontend/
│   ├── app.py                  # Flask Web UI proxying to Backend
│   ├── Dockerfile              # Python 3.12-slim container image
│   ├── requirements.txt        # Frontend dependencies (Flask, requests, gunicorn)
│   └── templates/
│       └── index.html          # Responsive weather search interface
├── helm/
│   └── skywatch/
│       ├── Chart.yaml          # Helm chart metadata (v0.1.0)
│       ├── values.yaml         # Configurable parameters (images, replicas, ingress)
│       └── templates/          # Kubernetes manifests (deployments, services, ingress)
├── terraform/
│   ├── versions.tf             # Terraform & provider constraints (helm, kubernetes)
│   ├── provider.tf             # Kubernetes & Helm provider configurations
│   ├── argocd.tf               # ArgoCD namespace & Helm release
│   └── application.tf          # SkyWatch ArgoCD application manifest
└── rendered.yaml               # Static rendered snapshot of Helm chart
```

---

## Prerequisites

Ensure the following tools are installed on your workstation:

* **Multipass** (`multipass version`)
* **Git** (`git --version`)
* **Docker** (`docker --version`)
* **kubectl** (`kubectl version --client`)
* **Helm 3** (`helm version`)
* **Ansible** (`ansible --version`) & **Python 3** (`python3 --version`)
* **Terraform** (`terraform version` >= 1.5)

---

## 1. Local Development (Without Kubernetes)

To test the application locally without deploying a full Kubernetes cluster:

### Run with Python

1. **Start Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
   *Backend runs on `http://localhost:5000`.*

2. **Start Frontend** (in a separate terminal):
   ```bash
   cd frontend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   export BACKEND_URL="http://localhost:5000"  # On Windows: $env:BACKEND_URL="http://localhost:5000"
   python app.py
   ```
   *Frontend UI is available at `http://localhost:8080`.*

### Run with Docker

```bash
docker network create skywatch-net

docker build -t skywatch-backend:local ./backend
docker run -d --name skywatch-backend --network skywatch-net -p 5000:5000 skywatch-backend:local

docker build -t skywatch-frontend:local ./frontend
docker run -d --name skywatch-frontend --network skywatch-net -p 8080:8080 -e BACKEND_URL="http://skywatch-backend:5000" skywatch-frontend:local
```

---

## 2. Infrastructure Setup (Multipass VMs)

SkyWatch runs on a 3-node K3s cluster. Launch the virtual machines using Multipass:

| VM Name | Role | Specification |
|---------|------|---------------|
| `skywatch-cp` | K3s Control Plane | 2 CPU, 2 GB RAM, 10 GB Disk |
| `skywatch-worker1` | K3s Worker 1 | 1 CPU, 1.5 GB RAM, 10 GB Disk |
| `skywatch-worker2` | K3s Worker 2 | 1 CPU, 1.5 GB RAM, 10 GB Disk |

```bash
multipass launch 22.04 --name skywatch-cp --cpus 2 --memory 2G --disk 10G
multipass launch 22.04 --name skywatch-worker1 --cpus 1 --memory 1.5G --disk 10G
multipass launch 22.04 --name skywatch-worker2 --cpus 1 --memory 1.5G --disk 10G
```

Verify that all three instances are running:
```bash
multipass list
```

---

## 3. SSH Key Authorization

To allow Ansible passwordless access into the VMs:

```bash
# Generate key if you do not already have one
test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa

# Authorize your public key across all Multipass instances
PUBKEY=$(cat ~/.ssh/id_rsa.pub)
for vm in skywatch-cp skywatch-worker1 skywatch-worker2; do
  multipass exec "$vm" -- bash -c "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$PUBKEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
done
```

---

## 4. Automated Provisioning with Dynamic Ansible Inventory

SkyWatch uses **dynamic inventory discovery** via [`ansible/inventories/multipass.py`](ansible/inventories/multipass.py).

### How Dynamic Inventory Works
* The script executes `multipass list --format json` directly.
* Resolves VM IPv4 addresses on the fly without any manual `hosts` or `.ini` edits.
* Dynamically assigns `skywatch-cp` to `k3s_server` and `skywatch-worker*` to `k3s_agents`.
* K3s server generates its own random cluster token on install; Ansible reads it dynamically from `/var/lib/rancher/k3s/server/node-token` and passes it to worker nodes at runtime.

### Test the Dynamic Inventory

```bash
cd ansible
python3 inventories/multipass.py
```
*(or via Ansible: `ansible-inventory --list`)*

### Run the Playbook

Because [`ansible/ansible.cfg`](ansible/ansible.cfg) already specifies `inventory = inventories/multipass.py`, simply execute:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

---

## 5. Configure `kubectl` Remote Access

1. Retrieve the kubeconfig directly from `skywatch-cp` via Multipass:
   ```bash
   multipass exec skywatch-cp -- sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config
   chmod 600 ~/.kube/config
   ```

2. Retrieve the dynamically assigned IP of `skywatch-cp`:
   ```bash
   CP_IP=$(multipass info skywatch-cp --format json | grep -oE '172\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
   echo "Control Plane IP: $CP_IP"
   ```

3. Replace `https://127.0.0.1:6443` inside `~/.kube/config` with `https://$CP_IP:6443`:
   ```bash
   sed -i "s|https://127.0.0.1:6443|https://${CP_IP}:6443|g" ~/.kube/config
   ```

4. Verify cluster status:
   ```bash
   kubectl get nodes -o wide
   ```

   **Expected Output**:
   ```text
   NAME               STATUS   ROLES                  AGE   VERSION
   skywatch-cp        Ready    control-plane,master   5m    v1.31.4+k3s1
   skywatch-worker1   Ready    <none>                 4m    v1.31.4+k3s1
   skywatch-worker2   Ready    <none>                 4m    v1.31.4+k3s1
   ```

---

## 6. Deploy SkyWatch via Helm

The Helm chart packages the frontend, backend, services, configmaps, and Traefik ingress.

> [!NOTE]
> The Helm deployment enforces `nodeAffinity` targeting worker nodes (excluding the `control-plane` role). Pods will schedule onto `skywatch-worker1` and `skywatch-worker2`.

```bash
helm upgrade --install skywatch ./helm/skywatch
```

Verify deployment:
```bash
kubectl get pods -l 'app in (skywatch-frontend, skywatch-backend)' -o wide
kubectl get svc -l 'app in (skywatch-frontend, skywatch-backend)'
kubectl get ingress skywatch-ingress
```

---

## 7. Accessing SkyWatch

### Configure Local DNS

Map `skywatch.local` and `argocd.local` to the dynamically assigned IP of `skywatch-cp`:

* **Linux / macOS**: `/etc/hosts`
* **Windows**: `C:\Windows\System32\drivers\etc\hosts`

```text
<CP_IP> skywatch.local
<CP_IP> argocd.local
```

### Open the Application

Open your browser and navigate to:
```text
http://skywatch.local
```

---

## 8. CI/CD Pipeline (GitHub Actions & GHCR)

Workflow file: [`.github/workflows/build.yml`](.github/workflows/build.yml)

### Stages

1. **Trigger**: Pushes to branch `main` (skips if commit contains `[skip ci]`).
2. **Lint**: Runs `flake8 backend` and `flake8 frontend`.
3. **Build & Push**: Builds and publishes container images to GitHub Container Registry:
   * `ghcr.io/boofinka/skywatch-backend:<git-sha>`
   * `ghcr.io/boofinka/skywatch-frontend:<git-sha>`
4. **GitOps Tag Update**: Modifies image tags in `helm/skywatch/values.yaml` using `yq`.
5. **Auto-Commit**: Commits and pushes the updated `values.yaml` back with `[skip ci]`.

---

## 9. Continuous Delivery with ArgoCD

ArgoCD continuously monitors the repository and synchronizes state to the cluster.

### Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait until the ArgoCD pods are ready:
```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
```

### Expose ArgoCD Web UI

Deploy Traefik Ingress for ArgoCD:
```bash
kubectl apply -f argocd/argocd-ingress.yaml
```

Retrieve the initial `admin` password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

Access ArgoCD at:
```text
http://argocd.local
```

### Deploy the SkyWatch ArgoCD Application

Apply the application manifest:
```bash
kubectl apply -f argocd/application.yaml
```

Verify application status:
```bash
kubectl get application -n argocd skywatch
```

---

## 10. Alternative: Bootstrap with Terraform

The `terraform/` directory provides an Infrastructure as Code bootstrap for ArgoCD:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform manages:
* Creation of the `argocd` namespace
* ArgoCD Helm release deployment
* The `skywatch` ArgoCD `Application` resource

---

## 11. Verification & Health Checks

### Backend Health Check
```bash
kubectl port-forward svc/skywatch-backend 5000:5000 &
curl http://localhost:5000/health
```
```json
{"status": "ok"}
```

### Backend Weather API Query
```bash
curl "http://localhost:5000/weather?city=Tel%20Aviv"
```
```json
{
  "city": "Tel Aviv",
  "temperature": 23.4,
  "windspeed": 12.1
}
```

### Frontend Health Check
```bash
kubectl port-forward svc/skywatch-frontend 8080:80 &
curl http://localhost:8080/health
```
```json
{"status": "healthy"}
```

---

## 12. Troubleshooting

### 1. `multipass.py` Fails with Exit Status 2 or Command Not Found
* **Cause**: On Windows WSL, Multipass CLI is called as `multipass.exe` on the host, whereas native Linux calls `multipass`.
* **Resolution**: The updated [`multipass.py`](ansible/inventories/multipass.py) checks both `multipass.exe` and `multipass` via `shutil.which()`. Ensure Multipass is running and accessible from your terminal (`multipass list`).

### 2. Pods Stuck in `Pending`
* **Cause**: Node affinity requires non-control-plane nodes. If worker nodes haven't joined, pods cannot be scheduled.
* **Resolution**: Verify `kubectl get nodes`. Ensure worker nodes are present and `Ready`.

### 3. Kubeconfig `connection refused` on Port 6443
* **Cause**: K3s defaults the cluster address inside `k3s.yaml` to `127.0.0.1:6443`.
* **Resolution**: Run `multipass info skywatch-cp` to get the VM's IP, then update `server: https://<CP_IP>:6443` in `~/.kube/config`.

### 4. Weather Provider Unavailable (503)
* **Cause**: Egress DNS or HTTP connectivity from cluster pods to `https://api.open-meteo.com` blocked.
* **Resolution**: Test pod outbound connectivity:
  ```bash
  kubectl run net-test --rm -it --image=curlimages/curl -- curl -I https://api.open-meteo.com
  ```
