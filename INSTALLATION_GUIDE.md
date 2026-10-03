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
+---------------------------------+
|   Application server            |
|   <app-server-ip>:8000          |
|   Django + orchestrator         |
+----------------+----------------+
                 | HTTPS :2376 (mutual TLS)
   +-------------+-------------+
   |                           |
+---------+---------+  +--------+---------+
|  Worker node 1  |  |  Worker node 2   |
|  kali (Docker)  |  |  kali2 (Docker)  |
| <worker-1-ip>   |  | <worker-2-ip>    |
+-----------------+  +------------------+
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
git clone https://github.com/TheGhostSecurity/somacloud.git
cd somacloud
```

The repository is **private**. You need a GitHub token with `repo` scope, or an
SSH key added to the account.

> **Do not clone an empty database.** A fresh clone has no labs. Either restore
> a backup (§12.5) or populate from bundled content:
> `./venv/bin/python manage.py seed_data` then
> `./venv/bin/python manage.py populate_labs`.

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

> **Deploying to a different machine?** Every host-specific value in
> `sandbox/settings.py` is now read from the environment with a placeholder
> default, so you do not edit that file at all — see §3.4. You will still need
> to register your Docker nodes (they are `DockerNode` database rows, not
> settings) and, if you are restoring from a backup, work through §12.6.

### 3.4 Configure Django settings

Do not edit `sandbox/settings.py` for host-specific values. It reads everything
from the environment and contains **no credentials and no real IPs**.

Set these before starting the app:

```bash
export DJANGO_SECRET_KEY="$(./venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
export ALLOWED_HOSTS="somacloud.example.com"    # comma-separated
export DEBUG="false"
export SWARM_MANAGER_IP="10.0.1.10"             # public IP of the app server
export APP_SERVER_URL="http://10.0.1.10:8000"    # reachable FROM the workers
export EMAIL_HOST_USER="you@example.com"
export EMAIL_HOST_PASSWORD="your-app-password"   # Gmail: use an App Password
```

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Signs sessions and password-reset tokens. **Required** — the app refuses to start without it rather than falling back to a known key |
| `ALLOWED_HOSTS` | Comma-separated hostnames/IPs the app answers to |
| `DEBUG` | Defaults to `false`. Never enable on a reachable deployment |
| `SWARM_MANAGER_IP` | Public IP used in Swarm join commands |
| `APP_SERVER_URL` | Base URL workers use for CA signing and setup callbacks |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials. Unset = mail logged, not sent |

Better than `export`, so values do not land in shell history — use an
environment file the service reads:

```ini
# /etc/somacloud/env    (chmod 600, owned by the service user)
DJANGO_SECRET_KEY=<generated value>
ALLOWED_HOSTS=somacloud.example.com
DEBUG=false
SWARM_MANAGER_IP=10.0.1.10
APP_SERVER_URL=http://10.0.1.10:8000
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=<app password>
```

```ini
# /etc/systemd/system/somacloud.service
[Service]
EnvironmentFile=/etc/somacloud/env
```

Then verify:

```bash
./venv/bin/python manage.py check          # fails loudly if SECRET_KEY is unset
./venv/bin/python manage.py check --deploy # security warnings
```

> **Note:** for a real production deployment, also front Django with a
> production WSGI server (e.g. Gunicorn) and terminate TLS at a reverse proxy.
> The reference deployment runs Django's development server via systemd for a
> small institutional install.

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

> **TLS material is never committed to this repository.** `.gitignore` excludes
> `ca/`, `certs/`, `docker-tls/` and all `*.pem` / `*.key` / `*.csr` / `*.srl`
> files. A CA signing key can mint certificates that every Docker node will
> trust, which means anyone holding it can join your Swarm and run arbitrary
> containers on your workers. Treat a leaked CA as a full compromise.
>
> `.gitignore` only prevents *future* commits. Check whether a secret is
> already tracked:
>
> ```bash
> git ls-files | grep -iE '\.pem$|\.key$|\.csr$|^ca/|^certs/'
> ```
>
> Anything listed must be purged from history (§5.4), not merely ignored.

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

### 5.2 Regenerating the CA after a leak

Removing a key from a working tree does not revoke it. To rotate a
compromised CA:

```bash
cd /home/kali/somacloud

# 1. Move the old CA aside (destroy the copy once you have a new one working)
sudo mv ca ca.compromised.$(date +%Y%m%d)

# 2. Generate a fresh CA
./venv/bin/python -c "from core import ca; ca.ensure_ca()"
chmod 600 ca/ca.key

# 3. Delete every issued client certificate
sudo rm -rf certs/*
```

Every node also needs a fresh **server** certificate: the old one was signed by
the retired CA and workers will no longer trust it. Re-run the node Setup flow
(admin UI → Nodes → Setup) per worker, which regenerates the node keypair and
CSR, requests a signature, rewrites `/etc/docker/tls/` and restarts Docker.

Confirm workers no longer accept anything signed by the old CA, then purge it
from git (§5.4).

### 5.3 What ships in the repository

A fresh clone contains **no TLS material**. Only these OpenSSL configuration
templates are tracked, and they hold no keys:

| File | Purpose |
|------|---------|
| `docker-tls/ca-openssl.cnf` | CA signing parameters |
| `docker-tls/client-openssl.cnf` | Client certificate extension profile |
| `docker-tls/signing-openssl.cnf` | CSR signing extensions |

To add another non-secret file to `docker-tls/`, add a negation rule:

```gitignore
docker-tls/*
!docker-tls/*.cnf
```

### 5.4 Purging secrets from git history

Back up first — this rewrites every commit SHA:

```bash
git bundle create ../somacloud-history.bundle --all
./venv/bin/pip install git-filter-repo

git filter-repo --path ca/ca.key --invert-paths
git filter-repo --path docker-tls/server-key.pem --invert-paths
```

Verify before pushing:

```bash
git log --all --full-history -- '*ca.key' '*key.pem'    # expect no commits
git grep -I 'BEGIN RSA PRIVATE KEY' $(git rev-list --all) 2>/dev/null | head
```

Force-push and have collaborators re-clone:

```bash
git push --force-with-lease origin main
```

Deleting a secret in a new commit is **not** sufficient — it stays in history.
Also rotate anything that was exposed: history rewriting hides what was
published, but public secrets should be considered compromised regardless, and
forks or caches may retain copies.

### 5.5 How the certificate flow works

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
   - **Public IP:** `<worker-2-ip>`
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
    --public-ip <worker-2-ip> \
    --docker-host https://<worker-2-ip>:2376 \
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
scp -i somacloud.pem core/views.py kali@<app-server-ip>:/home/kali/somacloud/core/
scp -i somacloud.pem templates/*.html kali@<app-server-ip>:/home/kali/somacloud/templates/

# on the server
cd /home/kali/somacloud && source venv/bin/activate
python manage.py migrate          # if models changed
sudo systemctl restart somacloud
```

If you changed templates or Python modules only, the restart is enough.

### 10.1 Beware of scp destination paths

`scp` does not create directories, and a wrong destination fails silently in
the sense that the file lands in the wrong place and the app keeps running on
stale code. Two mistakes that actually happened:

```bash
# WRONG — files land in core/ instead of core/migrations/
scp core/migrations/0021_x.py host:/home/kali/somacloud/core/

# WRONG — lands in core/ instead of core/management/commands/
scp core/management/commands/seed_data.py host:/home/kali/somacloud/core/
```

Copy to the **full** destination path every time, then verify:

```bash
ssh -i somacloud.pem kali@<app-server-ip> \
  'ls -l /home/kali/somacloud/core/migrations/ /home/kali/somacloud/core/management/commands/'
```

After deploying a model change, confirm Django sees no pending migrations. If
it reports unapplied changes, the migration file did not land:

```bash
./venv/bin/python manage.py makemigrations --check --dry-run
```

### 10.2 Back up before migrating

`manage.py migrate` alters the schema. Take a snapshot first so a failed
migration is recoverable (§12.2):

```bash
./scripts/backup.sh
./venv/bin/python manage.py migrate
```

---

## 11. Post-Installation Checklist

- [ ] App server reachable at `http://<ip>:8000`
- [ ] Admin can log in and sees the Administration page (summary + user management)
- [ ] At least one worker node shows **Active**
- [ ] `python manage.py verify_node --name <node>` passes all steps
- [ ] Ports 2376 and 9000–9100 open on worker security groups
- [ ] At least one terminal container image and one service image registered
- [ ] A lab is published and a student can launch a sandbox from the Lab Library
- [ ] A database backup has been taken and copied **off** the server (see §12)
- [ ] The backup passphrase is stored somewhere other than this server

---

## 12. Backup and Disaster Recovery

> **Read this before shutting down or replacing a server.** The lab content
> (titles, theory, walkthroughs, flags, service definitions) lives in the
> SQLite database, **not** in the `scripts/seed_*.py` files. Those scripts are
> authoring source only — they will not rebuild labs that were created or
> edited through the UI. The database snapshot is the record of record.

### 12.1 What must be backed up

| Item | Location | Why it matters |
|------|----------|----------------|
| Database | `db.sqlite3` | All labs, users, enrollments, sessions, nodes, flags |
| Docker node SSH key | `media/keys/*.pem` | The DB stores only a row pointing at this file |
| Code | Git remote | Already versioned |

Everything else (images, containers) is rebuilt from `scenario-images/` or
re-pulled from Docker Hub.

### 12.2 Taking a backup

```bash
cd /home/kali/somacloud
./scripts/backup.sh
```

This writes three files to `backups/`:

| File | Contents |
|------|----------|
| `db-<stamp>.sqlite3.gz` | Consistent database snapshot |
| `fixture-<stamp>.json.gz` | Readable JSON dump of all models |
| `media-<stamp>.tar.gz` | `media/`, including the Docker node SSH keys |

The snapshot uses SQLite's **online backup API**, so it is safe to run while
the app is serving traffic. Do not substitute a plain `cp db.sqlite3`.

Verify it before trusting it:

```bash
cd /home/kali/somacloud
gunzip -c backups/db-<stamp>.sqlite3.gz > /tmp/check.sqlite3
python3 -c "
import sqlite3; c=sqlite3.connect('/tmp/check.sqlite3')
print('integrity:', c.execute('PRAGMA integrity_check').fetchone()[0])
print('labs:', c.execute('select count(*) from core_lab').fetchone()[0])
print('theory blobs:', c.execute('select count(*) from core_lab where length(theory_content)>0').fetchone()[0])
"
rm /tmp/check.sqlite3
```

### 12.3 Copy the backup OFF the server

**This is the step people forget.** A backup stored only on the instance you
are about to terminate is not a backup.

```bash
# from your workstation
scp -i /path/to/key.pem kali@<server-ip>:/home/kali/somacloud/backups/db-*.gz .
scp -i /path/to/key.pem kali@<server-ip>:/home/kali/somacloud/backups/media-*.tar.gz .
```

Keep at least two copies in different places (laptop + password-manager
attachment or offline USB).

### 12.4 Encrypting for the Git repo

Backups contain password hashes, node setup tokens, and the node SSH private
key. If you commit a backup, commit it **encrypted**:

```bash
# one-time: create a passphrase file outside the repo
umask 077 && openssl rand -base64 24 > ~/somacloud-backup-passphrase.txt

# snapshot + encrypt the newest artifacts
./scripts/backup.sh
./scripts/backup_encrypt.sh

git add -f backups/*.tar.gz.enc
git commit -m "backup: $(date +%Y%m%d-%H%M)"
git push
```

The passphrase is **not** in the repository. Losing it makes the backup
unrecoverable — store it in a password manager and offline.

Confirm encryption actually took effect before pushing:

```bash
grep -ac "sqlite\|BEGIN" backups/*.enc   # must return 0 matches
```

`backups/.gitignore` allows only `*.tar.gz.enc` through, so raw snapshots
cannot be committed by accident.

### 12.5 Restoring on a new server

```bash
git clone https://github.com/TheGhostSecurity/somacloud.git
cd somacloud
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Decrypt and unpack:

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in backups/somacloud-backup-<stamp>.tar.gz.enc \
  -out /tmp/b.tar.gz

tar -xzf /tmp/b.tar.gz -C backups/
```

Restore:

```bash
./scripts/restore.sh backups/db-<stamp>.sqlite3.gz backups/media-<stamp>.tar.gz
```

`restore.sh` stops the service, keeps a timestamped `.bak` of the existing
database, installs the snapshot, runs `migrate`, checks
`PRAGMA integrity_check`, and restarts the service.

### 12.6 Post-restore checklist

The snapshot restores your content, not your infrastructure. These still need
attention:

- [ ] **`ALLOWED_HOSTS`** in `sandbox/settings.py` — add the new server IP or
      every request returns HTTP 400.
- [ ] **Re-register the Docker node.** The restored `DockerNode` row contains
      the *old* IP and SSH host key. Update `public_ip`, `docker_host`,
      `ssh_host`, and clear the stale host key, then re-run
      `python manage.py verify_node --name <node>`.
- [ ] **Rebuild scenario images** from `scenario-images/*/Dockerfile`.
- [ ] **Re-create the systemd unit** (`/etc/systemd/system/somacloud.service`)
      — it is not in the repository.
- [ ] **Re-install TLS certs** for the new host if the hostname/IP changed.
- [ ] **Confirm student-facing ports** (9000–9100) are open in the new
      security group.
- [ ] Log in as an instructor and confirm the lab list shows the expected
      count and all labs are published.

### 12.7 A note on `SECRET_KEY`

`sandbox/settings.py` currently hardcodes a development secret key and runs
with `DEBUG = True`. Before exposing a restored instance to real students,
move both to environment variables:

```python
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

Rotating `SECRET_KEY` invalidates existing sessions, which is expected.

---

## 13. Troubleshooting

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

### Lab content missing after a restore
Labs live in the database, not in the seed scripts. Confirm the snapshot
actually contains them:

```bash
gunzip -c backups/db-<stamp>.sqlite3.gz > /tmp/check.sqlite3
python3 -c "
import sqlite3; c=sqlite3.connect('/tmp/check.sqlite3')
for r in c.execute('select hp.name, count(*) from core_lab l '
                   'left join core_hackphase hp on l.hack_phase_id=hp.id '
                   'group by hp.name order by hp.\"order\"'): print(r)
"
```
If the counts are zero, you restored the wrong file or an empty database.
Do **not** expect `./scripts/seed_*.py` to rebuild them — those are authoring
source, not a data export.

### A sandbox fails to launch with "could not launch sandbox"
Almost always the scheduler refusing to over-commit a node. Check whether the
lab's resource profile can physically fit:

```bash
PYTHONPATH=. DJANGO_SETTINGS_MODULE=sandbox.settings \
  ./venv/bin/python -c "
import django; django.setup()
from core.models import Lab, DockerNode
lab = Lab.objects.get(pk=<lab_id>)
print(lab.resource_profile.name, lab.resource_profile.cpu_count, 'CPU',
      lab.resource_profile.memory_mb, 'MB')
for n in DockerNode.objects.all():
    print(n.name, n.total_cpu, 'CPU', n.total_memory_mb, 'MB', n.status)
"
```

If `memory_mb` exceeds a node's `total_memory_mb`, `select_node()` in
`core/orchestrator.py` returns `None` and the launch fails. Lower the profile
in the instructor UI (or add capacity) — the failure is the oversubscription
guard working as designed.

---

## 14. Useful Management Commands

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
| `./scripts/backup.sh` | Snapshot the database + `media/` (safe while live) |
| `./scripts/backup_encrypt.sh` | Encrypt the newest backup for committing |
| `./scripts/restore.sh <db.gz> <media.tar.gz>` | Restore a snapshot on a server |
