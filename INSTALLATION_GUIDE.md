# SomaCloud — Installation Guide

Complete step-by-step installation and configuration guide for the SomaCloud
Web-Based Cybersecurity Sandbox Environment.

---

## 1. Overview and Architecture

SomaCloud is a Django web application that provisions browser-based terminal
sandboxes (ttyd) on remote Docker worker nodes. Students work inside an
isolated Kali Linux container and complete cybersecurity labs organised by
hacking phase (footprinting, scanning, enumeration, exploitation, etc.).

The system has three logical tiers:

| Tier | Purpose | Technology |
|------|---------|------------|
| **Application server** | Django web app, admin UI, student portal, orchestrator | Django 6.0, Python 3.13 |
| **Worker nodes** | Run student sandbox containers (ttyd terminal + vulnerable services) | Docker Engine 24+ |
| **TLS infrastructure** | Mutual TLS between app server and workers | OpenSSL + a self-hosted CA (`core/ca.py`) |

```
                          +-----------------------------+
                          |   Application server         |
                          |   16.192.120.187:8000        |
                          |   Django + orchestrator      |
                          +--------------+--------------+
                                         | HTTPS :2376 (mutual TLS)
                    +--------------------+---------------------+
                    |                                          |
          +---------+---------+                    +-----------+-----------+
          |  Worker node 1    |                    |  Worker node 2         |
          |  kali (Docker)    |                    |  kali2 (Docker)        |
          |  13.50.225.194    |                    |  13.48.137.218         |
          +-------------------+                    +-----------------------+
```

**Key design decision:** the app server and every worker node share the same
Certificate Authority. The worker presents a server certificate signed by the
CA, and the app server presents a client certificate signed by the same CA.
Both sides trust the shared `ca.pem`, producing mutual TLS.

---

## 2. Prerequisites

### 2.1 Hardware requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Application server CPU | 2 vCPU | 2 vCPU |
| Application server RAM | 2 GB | 4 GB |
| Application server storage | 20 GB SSD | 40 GB SSD |
| Worker node CPU | 2 vCPU | 4 vCPU |
| Worker node RAM | 4 GB | 8 GB (more = more concurrent sandboxes) |
| Worker node storage | 40 GB SSD | 100 GB SSD (Docker images are large) |

Each running sandbox consumes roughly the resource profile assigned to its lab
(256 MB – 2 GB RAM). Plan worker capacity accordingly.

### 2.2 Software requirements

- **Application server:** Linux (Ubuntu 22.04/24.04 or Kali), Python 3.12 or 3.13, pip, OpenSSL, Git
- **Worker nodes:** Linux (Ubuntu/Debian/Kali), Docker Engine CE (installed automatically by the setup script)
- **PostgreSQL** (recommended for production) **or** SQLite (default, zero-config)

### 2.3 Network requirements

Open the following ports in the cloud security groups / firewalls:

| Port | Direction | Protocol | Purpose |
|------|-----------|----------|---------|
| 22 | Inbound to app server & workers | TCP | SSH (administration + automated node setup) |
| 8000 | Inbound to app server | TCP | Django web application |
| 2376 | Inbound to workers | TCP | Docker Engine API (mutual TLS) |
| 9000–9100 | Inbound to workers | TCP | ttyd browser terminals (one port per sandbox) |

---

## 3. Application Server Setup

### 3.1 Update the system and install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git openssl curl
```

### 3.2 Clone the repository

```bash
git clone https://github.com/ghostriley23/somacloud.git
cd somacloud
```

### 3.3 Create a virtual environment and install packages

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` contains:

```
Django==6.0.6
Pillow==12.2.0
requests==2.32.3
matplotlib==3.10.7
psycopg2-binary==2.9.10
paramiko==5.0.0
reportlab==4.4.0
pypdf==5.1.0
```

### 3.4 Configure Django settings

Edit `sandbox/settings.py`:

- **`ALLOWED_HOSTS`** — add the public IP / domain of the app server:
  ```python
  ALLOWED_HOSTS = ["16.192.120.187", "localhost", "127.0.0.1"]
  ```
- **`SECRET_KEY`** — replace the development key with a generated one:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- **`APP_SERVER_URL`** — the base URL workers use to reach the app server for
  certificate signing and setup callbacks:
  ```python
  APP_SERVER_URL = "http://16.192.120.187:8000"
  ```
- **`SWARM_MANAGER_IP`** — public IP of the application server:
  ```python
  SWARM_MANAGER_IP = "16.192.120.187"
  ```

> **Note:** set `DEBUG = False` and use a production WSGI server (e.g. Gunicorn)
> in production. The reference deployment runs Django's development server via
> systemd for a small institutional deployment.

### 3.5 Database setup

**Option A — SQLite (default, zero-config)**

Nothing to do. The database file is created automatically at `db.sqlite3`.

**Option B — PostgreSQL (production)**

```bash
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql
```

```sql
CREATE DATABASE somacloud;
CREATE USER somacloud WITH PASSWORD 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE somacloud TO somacloud;
\q
```

Then configure via environment variables (or directly in `settings.py`):

```bash
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=somacloud
export DB_USER=somacloud
export DB_PASSWORD='choose-a-strong-password'
export DB_HOST=127.0.0.1
export DB_PORT=5432
```

### 3.6 Run database migrations

```bash
python manage.py migrate
```

### 3.7 Create the superuser (administrator)

```bash
python manage.py createsuperuser
```

### 3.8 Seed reference data (optional but recommended)

Populate the default hacking phases, resource profiles, and tools:

```bash
python manage.py seed_data
```

Populate labs from the bundled content files:

```bash
python manage.py populate_labs
```

Synchronise learning-path activities (theory, sandbox, challenge stages):

```bash
python manage.py sync_content
```

---

## 4. Container Images

Sandboxes run Docker images from Docker Hub. Register the images that
instructors may attach to labs. There are two kinds:

- `terminal` — the ttyd browser terminal (e.g. `ghostriley23/kali-ttyd:latest`, exposes port 7681)
- `service` — a vulnerable service container used as the lab target

```bash
python manage.py register_container_image \
    --name "Kali Terminal" \
    --image "ghostriley23/kali-ttyd:latest" \
    --kind terminal \
    --port 7681 \
    --description "Kali Linux browser terminal with common pentest tools"
```

Example vulnerable service:

```bash
python manage.py register_container_image \
    --name "DVWA" \
    --image "vulnerables/web-dvwa:latest" \
    --kind service \
    --port 80
```

---

## 5. Certificate Authority (TLS) Setup

SomaCloud runs a self-hosted Certificate Authority so the app server and all
worker nodes can authenticate each other over HTTPS (mutual TLS).

### 5.1 Generate the CA

The CA keypair, certificate, and signing logic live in `core/ca.py`. The CA is
created **automatically** the first time a node is set up (or when `ensure_ca()`
runs). To create it manually:

```bash
cd /home/kali/somacloud && source venv/bin/activate
python -c "from core import ca; ca.ensure_ca(); print(ca.get_ca_cert_pem().decode())"
```

This creates the CA directory:

```
ca/
├── ca.key          # private key (keep secret, permissions 600)
└── ca.crt          # self-signed CA certificate
```

### 5.2 How the certificate flow works

1. The admin registers a node (IP + SSH key) in the Django UI and clicks **Setup**.
2. The app server generates a one-time **setup token** and builds a bash script.
3. The script is executed on the worker over SSH. On the worker it:
   - installs Docker,
   - generates a private key and a Certificate Signing Request (CSR) for the worker,
   - POSTs the CSR to `APP_SERVER_URL/admin/nodes/<id>/ca/sign/<token>/`,
   - receives a signed server certificate back,
   - writes `ca.pem`, `server.crt`, `server.key` to `/etc/docker/tls/`,
   - configures the Docker daemon to serve TLS on port 2376 and restarts it,
   - calls `setup-complete/<token>/` so the app server marks the node active.
4. Meanwhile the app server generates a **client certificate** for the node in
   `certs/<node_name>/` (`cert.pem`, `key.pem`, `ca.pem`).

Directory layout after setup:

```
somacloud/
├── ca/                     # shared CA keypair
│   ├── ca.key
│   └── ca.crt
└── certs/
    ├── kali/               # client certs used to talk to worker "kali"
    │   ├── ca.pem
    │   ├── cert.pem
    │   └── key.pem
    └── kali2/
        ├── ca.pem
        ├── cert.pem
        └── key.pem
```

---

## 6. Worker Node Setup

Two options are available.

### 6.1 Option A — Automated (recommended)

1. Add the node in the Django UI: **Administration → Docker Nodes → Add Node**.
   - **Name:** `kali2`
   - **Public IP:** `13.48.137.218`
   - **SSH user / port:** `kali`, `22`
   - **SSH key:** select a pre-uploaded key (**Administration → SSH Keys → Upload**)
   - Leave **Docker host** empty; it defaults to `http://<ip>:2376` and is
     automatically switched to `https://<ip>:2376` after successful setup.
2. Click **Setup** on the node.
3. Watch the log output. When it finishes, the node is marked **Active**.
4. Click **Verify** to run an end-to-end smoke test (ping → pull `alpine` →
   create container → verify exit code 0 → clean up).

### 6.2 Option B — Manual (for reference)

If you prefer to configure a worker by hand:

```bash
# 1. Install Docker Engine on the worker
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker

# 2. Request a server certificate from the app server CA
#    (performed automatically by the setup script; requires the node record
#     and a valid setup token). The signed certs go to /etc/docker/tls/.

# 3. Enable TLS on the Docker daemon
sudo tee /etc/docker/daemon.json > /dev/null <<'DAEMON'
{
    "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
    "tls": true,
    "tlsverify": true,
    "tlscacert": "/etc/docker/tls/ca.pem",
    "tlscert": "/etc/docker/tls/server.crt",
    "tlskey": "/etc/docker/tls/server.key"
}
DAEMON

# 4. Restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 7. Registering a Node from the CLI (alternative)

Nodes can also be registered with the management command:

```bash
python manage.py register_node \
    --name kali2 \
    --public-ip 13.48.137.218 \
    --docker-host https://13.48.137.218:2376 \
    --port-start 9000 \
    --port-end 9100 \
    --total-cpu 2 \
    --total-memory 4096 \
    --verify
```

`--verify` runs the full smoke test immediately after registration.

---

## 8. Node Verification

Verify a node end-to-end at any time:

```bash
python manage.py verify_node --name kali2
```

Expected output:

```
  ✓ Daemon ping: Docker daemon responded
  ✓ Pull test image: alpine:latest pulled successfully
  ✓ Create container: Container 7b95526e3428 created
  ✓ Start container: Container started and exited with code 0
  ✓ Cleanup container: Container 7b95526e3428 removed
  ✓ Cleanup image: alpine:latest removed
Verify passed for kali2
```

You can also use the **Verify** button on the node page in the Django UI.

> **Troubleshooting tip:** if the Daemon ping fails with
> `client sent an HTTP request to an HTTPS server`, the node's `docker_host` is
> still `http://`. It must be `https://<ip>:2376`. The setup-complete callback
> flips it automatically for new setups.

---

## 9. Running the Application

### 9.1 Development

```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

Access the app at `http://<app-server-ip>:8000`.

### 9.2 Production-style service (systemd)

Create `/etc/systemd/system/somacloud.service`:

```ini
[Unit]
Description=SomaCloud Django App
After=network.target

[Service]
Type=simple
User=kali
WorkingDirectory=/home/kali/somacloud
ExecStart=/home/kali/somacloud/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable somacloud
sudo systemctl start somacloud
sudo systemctl status somacloud
```

Common service commands:

```bash
sudo systemctl restart somacloud   # after every code deploy
sudo journalctl -u somacloud -f    # live logs
```

---

## 10. Deploying Code Updates

The reference workflow copies updated files to the server and restarts:

```bash
# from your development machine
scp -i somacloud.pem core/views.py kali@16.192.120.187:/home/kali/somacloud/core/
scp -i somacloud.pem templates/*.html kali@16.192.120.187:/home/kali/somacloud/templates/

# on the server
cd /home/kali/somacloud && source venv/bin/activate
python manage.py migrate          # if models changed
sudo systemctl restart somacloud
```

If you changed templates or Python modules only, the restart is enough.

---

## 11. Post-Installation Checklist

- [ ] App server reachable at `http://<ip>:8000`
- [ ] Admin can log in and sees the Administration page (summary + user management)
- [ ] At least one worker node shows **Active**
- [ ] `python manage.py verify_node --name <node>` passes all steps
- [ ] Ports 2376 and 9000–9100 open on worker security groups
- [ ] At least one terminal container image and one service image registered
- [ ] A lab is published and a student can launch a sandbox from the Lab Library

---

## 12. Troubleshooting

### Worker shows "Offline" after setup
Run the verify smoke test and check the node `docker_host` value:

```bash
python manage.py verify_node --name kali2
```
If the ping fails with an HTTP/HTTPS mismatch, update the node's Docker host to
`https://<ip>:2376`.

### `TLS handshake error ... client sent an HTTP request to an HTTPS server`
The orchestrator is sending plain HTTP to a TLS port. Fix the `docker_host`.

### Certificate verification error on the app server
Ensure the client certs exist for the node and match the shared CA:

```bash
ls certs/kali2/     # should contain ca.pem, cert.pem, key.pem
```

### Container cannot pull images
Worker needs outbound internet access to Docker Hub (port 443).

### "Docker unreachable" in the admin summary
The local manager daemon may not be running. Worker nodes are used for sandbox
launches regardless; the summary card reflects the app-server-local daemon.

---

## 13. Useful Management Commands

| Command | Purpose |
|---------|---------|
| `python manage.py createsuperuser` | Create an admin account |
| `python manage.py seed_data` | Seed phases, resource profiles, tools |
| `python manage.py populate_labs` | Populate labs from bundled content |
| `python manage.py sync_content` | Sync learning-path activities/stages |
| `python manage.py register_container_image` | Register a Docker image for labs |
| `python manage.py register_node --verify` | Register + smoke-test a worker |
| `python manage.py verify_node --name <node>` | Run the full node smoke test |
| `python manage.py expire_sessions` | Mark timed-out sandboxes as expired |
